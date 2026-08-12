/**
 * govoss-catalog MCP server.
 *
 * Model Context Protocol over Streamable HTTP: one POST endpoint speaking
 * JSON-RPC 2.0. No SDK, no Durable Object, no OAuth, no state - this server
 * answers from static JSON that anyone can already fetch, so there is nothing
 * to authenticate and no session to keep.
 *
 * WHY IT EXISTS
 * The catalogue's whole public argument is "take the data, don't scrape the
 * page". entries.json is 5.6 MB; an agent that wants three entries should not
 * download all of it. These five tools do the filtering at the edge.
 *
 * WHY IT READS mcp-index.json AND NOT entries.json
 * A Worker gets 10ms of CPU per request on the free plan. JSON.parse runs at a
 * few hundred MB/s, so parsing the 5.6 MB export would blow the budget on a
 * cold isolate. mcp-index.json is the same data reduced to the fields search
 * needs - 852 KB raw, ~3ms to parse - and it is written by the SAME pipeline
 * run that writes entries.json, so the two cannot drift.
 *
 * WHY THE PARSED INDEX IS MEMOISED AT MODULE SCOPE
 * Workers reuse isolates between requests. Parsing once per isolate and holding
 * it means the cost is paid on a cold start and amortised to nothing after. The
 * memo is keyed on generated_at, so a Monday rebuild invalidates it naturally
 * rather than needing a purge.
 */

const PROTOCOL_VERSION = "2024-11-05";
const SERVER_INFO = { name: "govoss-catalog", version: "1.0.0" };

// ---------------------------------------------------------------- data access

let MEMO = null; // { generatedAt, entries }

async function loadIndex(env) {
  const origin = env.CATALOG_ORIGIN;
  // cacheTtl lets Cloudflare's edge hold the upstream file, so a cold isolate
  // usually pays a cache hit rather than a trip to Vercel.
  const res = await fetch(`${origin}/mcp-index.json`, {
    cf: { cacheTtl: 3600, cacheEverything: true },
  });
  if (!res.ok) throw new Error(`catalogue index unavailable (${res.status})`);
  const data = await res.json();
  if (MEMO && MEMO.generatedAt === data.generated_at) return MEMO;
  MEMO = { generatedAt: data.generated_at, entries: data.entries };
  return MEMO;
}

async function loadJson(env, path) {
  const res = await fetch(`${env.CATALOG_ORIGIN}${path}`, {
    cf: { cacheTtl: 3600, cacheEverything: true },
  });
  if (!res.ok) throw new Error(`${path} unavailable (${res.status})`);
  return res.json();
}

// ---------------------------------------------------------------- tools

const TOOLS = [
  {
    name: "search_entries",
    description:
      "Full-text search over government open source entries: name, description, " +
      "owner and also-known-as, with optional facet filters. All filters are AND-ed. " +
      "Returns compact records; use get_entry for the full record.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "free text; omit to browse by facet alone" },
        country: { type: "string", description: "ISO-ish country code as published, e.g. DE" },
        function: { type: "string", description: "functional category, see get_stats" },
        source: { type: "string", description: "source catalogue key, see list_sources" },
        licence: { type: "string", description: "licence string as published" },
        limit: { type: "number", description: "default 20, max 100" },
      },
    },
  },
  {
    name: "find_replacements",
    description:
      "The procurement question, answered from an invoice line. Give it a proprietary " +
      "product name ('Qualtrics', 'Microsoft Office') and get the government open source " +
      "alternatives, each with confidence (strong/partial/adjacent) and kind (software / " +
      "service / paid-tier). kind matters: 'service' means the paid item is hosting or " +
      "content, which open source software does not replace by itself.",
    inputSchema: {
      type: "object",
      properties: { product: { type: "string" } },
      required: ["product"],
    },
  },
  {
    name: "get_entry",
    description:
      "One entry by its stable id, every field, including deep links back to each " +
      "government catalogue that lists it so a claim can be verified upstream.",
    inputSchema: {
      type: "object",
      properties: { id: { type: "string" } },
      required: ["id"],
    },
  },
  {
    name: "list_sources",
    description:
      "The government catalogues harvested first-hand, with access route and entry " +
      "count. With include_survey, also the catalogues checked and REJECTED and why - " +
      "which saves repeating a dead end someone already investigated.",
    inputSchema: {
      type: "object",
      properties: { include_survey: { type: "boolean" } },
    },
  },
  {
    name: "get_stats",
    description:
      "Counts, freshness (generated_at), and the controlled vocabulary for functions " +
      "and countries. Poll this rather than the pages to detect a rebuild.",
    inputSchema: { type: "object", properties: {} },
  },
];

function matches(e, q) {
  if (!q) return true;
  const hay = (
    e.n + " " + (e.d || "") + " " + (e.rp || []).join(" ")
  ).toLowerCase();
  return hay.indexOf(q) >= 0;
}

async function callTool(env, name, args) {
  args = args || {};

  if (name === "search_entries") {
    const { entries, generatedAt } = await loadIndex(env);
    const q = (args.query || "").trim().toLowerCase();
    const limit = Math.min(Math.max(parseInt(args.limit, 10) || 20, 1), 100);
    let out = entries.filter((e) => {
      if (!matches(e, q)) return false;
      if (args.country && !(e.cs || [e.c]).includes(args.country)) return false;
      if (args.function && !(e.f || []).includes(args.function)) return false;
      if (args.source && !(e.s || []).includes(args.source)) return false;
      if (args.licence && e.l !== args.licence) return false;
      return true;
    });
    const total = out.length;
    out = out.sort((a, b) => (b.cc || 1) - (a.cc || 1) || a.n.localeCompare(b.n))
             .slice(0, limit);
    return {
      total_matching: total,
      returned: out.length,
      generated_at: generatedAt,
      entries: out.map((e) => ({
        id: e.id, name: e.n, description: e.d, country: e.c, countries: e.cs,
        sources: e.s, functions: e.f, licence: e.l, repo_url: e.u,
        catalogue_count: e.cc, replaces: e.rp, link_dead: !!e.x,
      })),
      note: total > out.length
        ? `${total - out.length} more match; raise limit or narrow the filters.`
        : undefined,
    };
  }

  if (name === "find_replacements") {
    const product = (args.product || "").trim();
    if (!product) throw new Error("product is required");
    const byProduct = await loadJson(env, "/by-product.json");
    // by-product.json is keyed by the product name as curated. Match
    // case-insensitively, then fall back to a contains match so "Office" finds
    // "Microsoft Office" - but report which key actually answered, so the
    // caller is never guessing what was matched.
    const keys = Object.keys(byProduct);
    const exact = keys.find((k) => k.toLowerCase() === product.toLowerCase());
    const near = exact ? [exact]
      : keys.filter((k) => k.toLowerCase().includes(product.toLowerCase()));
    if (!near.length) {
      return {
        product, matched_key: null, alternatives: [],
        note: "No mapping for that product. The replaces index is hand-curated and " +
              "covers the products most often seen on public-sector invoices, not " +
              "every product - absence here is not evidence no alternative exists.",
      };
    }
    return {
      product,
      matched_key: near.length === 1 ? near[0] : undefined,
      matched_keys: near.length > 1 ? near : undefined,
      alternatives: near.flatMap((k) => byProduct[k]),
    };
  }

  if (name === "get_entry") {
    const id = (args.id || "").trim();
    if (!id) throw new Error("id is required");
    // Full record, so this one does read the large export - a single lookup is
    // worth the bytes, and the edge cache makes it cheap after the first call.
    const all = await loadJson(env, "/entries.json");
    const hit = all.find((e) => e.id === id);
    if (!hit) {
      const { entries } = await loadIndex(env);
      const near = entries.filter((e) => e.id.includes(id)).slice(0, 5).map((e) => e.id);
      return { id, found: false, did_you_mean: near,
               note: "Ids come from search_entries; they are stable but not guessable." };
    }
    return hit;
  }

  if (name === "list_sources") {
    const s = await loadJson(env, "/sources.json");
    return args.include_survey
      ? s
      : { generated_at: s.generated_at, ingested: s.ingested,
          note: "Pass include_survey:true for the catalogues checked and rejected, with reasons." };
  }

  if (name === "get_stats") {
    const m = await loadJson(env, "/meta.json");
    return m;
  }

  throw new Error(`unknown tool: ${name}`);
}

// ---------------------------------------------------------------- JSON-RPC

function rpcResult(id, result) {
  return { jsonrpc: "2.0", id, result };
}
function rpcError(id, code, message) {
  return { jsonrpc: "2.0", id, error: { code, message } };
}

async function handleRpc(env, msg) {
  const { id, method, params } = msg;

  if (method === "initialize") {
    return rpcResult(id, {
      protocolVersion: PROTOCOL_VERSION,
      capabilities: { tools: {} },
      serverInfo: SERVER_INFO,
      instructions:
        "A union catalogue of government open source software, harvested first-hand " +
        "from 17 national, municipal and international government catalogues. Use " +
        "find_replacements to answer 'what can we stop paying for?'. A null field means " +
        "the upstream government catalogue did not state that value - it is never " +
        "guessed - so read null as 'not stated', not 'unknown'.",
    });
  }
  // Notifications carry no id and MUST NOT be answered.
  if (method === "notifications/initialized" || method === "initialized") return null;
  if (method === "ping") return rpcResult(id, {});
  if (method === "tools/list") return rpcResult(id, { tools: TOOLS });

  if (method === "tools/call") {
    const name = params && params.name;
    try {
      const data = await callTool(env, name, (params && params.arguments) || {});
      return rpcResult(id, {
        content: [{ type: "text", text: JSON.stringify(data, null, 1) }],
      });
    } catch (err) {
      // Tool failures are reported INSIDE the result with isError, per MCP, so
      // the model can see and recover from them rather than the transport
      // swallowing the reason.
      return rpcResult(id, {
        content: [{ type: "text", text: `${name} failed: ${err.message}` }],
        isError: true,
      });
    }
  }
  if (id === undefined || id === null) return null;
  return rpcError(id, -32601, `method not found: ${method}`);
}

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "content-type, mcp-protocol-version, mcp-session-id",
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS });
    }

    // A human or a probe landing on the root should be told what this is and
    // where the data lives, not given a 404. That is the same reason the
    // catalogue answers /api/entries and /data.json.
    if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/mcp")) {
      return Response.json({
        name: SERVER_INFO.name,
        description: "MCP server over the govoss-catalog union catalogue of government " +
                     "open source software.",
        transport: "POST JSON-RPC 2.0 to this URL (MCP Streamable HTTP)",
        protocol_version: PROTOCOL_VERSION,
        tools: TOOLS.map((t) => t.name),
        the_data_itself: `${env.CATALOG_ORIGIN}/entries.json`,
        docs: `${env.CATALOG_ORIGIN}/api.html`,
      }, { headers: CORS });
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed. POST JSON-RPC to this URL.",
                          { status: 405, headers: CORS });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return Response.json(rpcError(null, -32700, "parse error"),
                           { status: 400, headers: CORS });
    }

    // A client may batch. Answer in kind, and drop nulls (notifications).
    if (Array.isArray(body)) {
      const out = (await Promise.all(body.map((m) => handleRpc(env, m)))).filter(Boolean);
      return out.length
        ? Response.json(out, { headers: CORS })
        : new Response(null, { status: 202, headers: CORS });
    }

    const res = await handleRpc(env, body);
    return res
      ? Response.json(res, { headers: CORS })
      : new Response(null, { status: 202, headers: CORS });
  },
};
