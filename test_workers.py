#!/usr/bin/env python3
"""Regression test for the three Cloudflare Workers (JS), run under Node.

    python3 test_workers.py

F8 left "the Workers (JS)" untested. They are small, but each carries a rule
that cost a real incident, and none of it is visible to the Python suites:

  deploy-cloudflare/site-worker.js   runs only when no asset matches: restores
      / and /ca/ (html_handling "none" switches directory indexes off) and 308s
      /ca -> /ca/ keeping the query. Anything else is a genuine 404, untouched.
  deploy-cloudflare/www-redirect.js  www -> apex, 301, path AND query kept, and
      CORS on the redirect itself - a browser checks CORS on each hop, which is
      exactly what the old vercel.app redirect lacks.
  mcp-server/src/index.js            JSON-RPC 2.0 over POST: notifications are
      never answered, tool failures come back INSIDE the result (isError), a
      failed fetch is retried with a CHANGED CACHE KEY (cacheTtl:0 alone was
      served the same cached 404 for an hour), and the index memo is keyed on
      generated_at.

Plus the contract rule from mcp_tools.py: two copies of a tool list are two
contracts, so the Worker's tools must match mcp_tools.TOOLS by name, order and
arguments.

Each Worker is imported as-is by a Node harness with a stubbed env.ASSETS and
a stubbed global fetch; no network, no wrangler. Needs Node 18+ (Request,
Response and fetch are globals); SKIPs, loudly, without it.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

HARNESS = r"""
import { pathToFileURL } from "node:url";
const [site, www, mcp] = await Promise.all(process.argv.slice(2).map(
  (p) => import(pathToFileURL(p).href).then((m) => m.default)));
const out = {};
const hdrs = (r) => Object.fromEntries([...r.headers.entries()]);

// ---------------------------------------------------------------- site-worker
const seen = [];
const ASSETS = { async fetch(req) {
  const u = new URL(req.url); seen.push(u.pathname + u.search);
  if (u.pathname === "/index.html" || u.pathname === "/ca/index.html")
    return new Response("<html>" + u.pathname + "</html>", { status: 200,
      headers: { "Content-Type": "application/octet-stream" } });
  return new Response("not found", { status: 404 });
} };
const S = (path) => site.fetch(new Request("https://govoss.cat" + path), { ASSETS });
let r = await S("/ca?src=IT");
out.ca_redirect = { status: r.status, location: r.headers.get("location") };
seen.length = 0; r = await S("/");
out.root = { status: r.status, body: await r.text(), type: r.headers.get("content-type"),
             cache: r.headers.get("cache-control"), asked: [...seen] };
seen.length = 0; r = await S("/ca/");
out.ca_root = { status: r.status, body: await r.text(), asked: [...seen] };
seen.length = 0; r = await S("/nope/");
out.dir_without_index = { status: r.status, asked: [...seen] };
seen.length = 0; r = await S("/missing.json?x=1");
out.genuine_404 = { status: r.status, asked: [...seen] };

// ---------------------------------------------------------------- www-redirect
r = await www.fetch(new Request("https://www.govoss.cat/entries.json?cc=DE&q=a%20b"));
out.www = { status: r.status, h: hdrs(r) };
r = await www.fetch(new Request("https://www.govoss.cat/"));
out.www_root = { location: r.headers.get("location") };

// ---------------------------------------------------------------- mcp-server
const env = { CATALOG_ORIGIN: "https://govoss.cat" };
let INDEX = { generated_at: "g1", entries: [
  { id: "a", n: "Rocketchat", d: "Instant messaging.", o: "RocketChat", a: ["Rocket.Chat"],
    c: "FR", cs: ["FR"], s: ["FR/sill"], f: ["collaboration"], l: "MIT", cc: 1,
    rp: ["Slack"] },
  { id: "b", n: "QGIS", d: "Desktop GIS.", c: "DE", cs: ["DE", "FR"], s: ["DE/openCode"],
    f: ["geospatial"], l: "GPL-2.0", cc: 3, rp: ["ArcGIS Pro"] },
  { id: "c", n: "Other", d: "Something else.", o: "regione-marche", c: "IT", s: ["IT/developers-italia"],
    f: ["geospatial"], l: "MIT", cc: 2 },
] };
const FILES = { "/by-product.json": { "Microsoft Office": [{ name: "LibreOffice" }],
                                      "Slack": [{ name: "Rocketchat" }] },
                "/entries.json": [{ id: "a", name: "Rocketchat" }],
                "/sources.json": { generated_at: "g1", ingested: [1, 2], survey: [3] },
                "/meta.json": { generated_at: "g1" } };
const calls = [];
let failIndexOnce = false, failAlways = false;
globalThis.fetch = async (url, init) => {
  calls.push({ url: String(url), cf: init && init.cf });
  const u = new URL(url);
  if (failAlways) return new Response("gone", { status: 404 });
  if (u.pathname === "/mcp-index.json") {
    if (failIndexOnce && !u.searchParams.has("cb"))
      return new Response("cached 404", { status: 404 });
    return Response.json(INDEX);
  }
  if (FILES[u.pathname]) return Response.json(FILES[u.pathname]);
  return new Response("nf", { status: 404 });
};
const rpc = async (body, method = "POST") => {
  const res = await mcp.fetch(new Request("https://mcp.govoss.cat/", {
    method, body: method === "POST" ? (typeof body === "string" ? body : JSON.stringify(body)) : undefined,
    headers: { "content-type": "application/json" } }), env);
  const text = await res.text();
  let json = null; try { json = JSON.parse(text); } catch {}
  return { status: res.status, json, cors: res.headers.get("access-control-allow-origin"), empty: text === "" };
};
const tool = async (name, args) => {
  const r = await rpc({ jsonrpc: "2.0", id: 7, method: "tools/call", params: { name, arguments: args } });
  const res = r.json.result;
  let data = null; try { data = JSON.parse(res.content[0].text); } catch {}
  return { isError: !!res.isError, text: res.content[0].text, data };
};

r = await mcp.fetch(new Request("https://mcp.govoss.cat/", { method: "OPTIONS" }), env);
out.options = { status: r.status, cors: r.headers.get("access-control-allow-origin") };
r = await mcp.fetch(new Request("https://mcp.govoss.cat/"), env);
out.get_root = { status: r.status, json: await r.json() };
out.put = await rpc(null, "PUT");
out.bad_json = await rpc("{not json");
out.initialize = await rpc({ jsonrpc: "2.0", id: 1, method: "initialize" });
out.notification = await rpc({ jsonrpc: "2.0", method: "notifications/initialized" });
out.batch = await rpc([{ jsonrpc: "2.0", method: "notifications/initialized" },
                       { jsonrpc: "2.0", id: 2, method: "ping" }]);
out.unknown = await rpc({ jsonrpc: "2.0", id: 3, method: "no/such" });
out.tools_list = await rpc({ jsonrpc: "2.0", id: 4, method: "tools/list" });

out.search_aka = await tool("search_entries", { query: "rocket.chat" });
out.search_owner = await tool("search_entries", { query: "regione-marche" });
out.search_replaces = await tool("search_entries", { query: "arcgis" });
out.search_country = await tool("search_entries", { country: "FR" });
out.search_facets = await tool("search_entries", { function: "geospatial", licence: "MIT" });
out.search_order = await tool("search_entries", {});
out.search_limit = await tool("search_entries", { limit: 1 });
out.search_limit_huge = await tool("search_entries", { limit: 100000 });

out.repl_exact = await tool("find_replacements", { product: "slack" });
out.repl_near = await tool("find_replacements", { product: "office" });
out.repl_none = await tool("find_replacements", { product: "Nothing Like It" });
out.repl_missing = await tool("find_replacements", {});
out.entry = await tool("get_entry", { id: "a" });
out.entry_miss = await tool("get_entry", { id: "zz" });
out.sources = await tool("list_sources", {});
out.sources_survey = await tool("list_sources", { include_survey: true });
out.unknown_tool = await tool("no_such_tool", {});

// memo keyed on generated_at: a rebuild must be seen without a purge
INDEX = { generated_at: "g2", entries: [{ id: "z", n: "Fresh", d: "", s: [], f: [], cc: 1 }] };
out.after_rebuild = await tool("search_entries", {});

// cache-key retry: a failure is retried ONCE with a changed URL
calls.length = 0; failIndexOnce = true;
out.cache_retry = await tool("search_entries", {});
out.cache_retry_calls = calls.map((c) => ({ url: c.url, cf: c.cf }));
failIndexOnce = false;

// a persistent failure is reported inside the result, naming URL and status
failAlways = true;
out.index_down = await tool("search_entries", {});
failAlways = false;

console.log(JSON.stringify(out));
"""


def main():
    node = shutil.which("node")
    if not node:
        print("SKIP  node not found - the Workers are untested on this machine")
        return 0
    paths = [os.path.join(HERE, p) for p in
             ("deploy-cloudflare/site-worker.js", "deploy-cloudflare/www-redirect.js",
              "mcp-server/src/index.js")]
    with tempfile.TemporaryDirectory() as tmp:
        h = os.path.join(tmp, "harness.mjs")
        open(h, "w").write(HARNESS)
        p = subprocess.run([node, "--no-warnings", h, *paths], capture_output=True, text=True,
                           timeout=60)
    if p.returncode != 0:
        print("FAIL  the harness itself failed:\n" + p.stderr[-2000:])
        return 1
    o = json.loads(p.stdout)

    failed, ran = [], []

    def check(label, got, want):
        ran.append(label)
        if got != want:
            failed.append(f"{label}: expected {want!r}, got {got!r}")

    # ---- site-worker.js
    check("/ca 308s to /ca/ with the query kept", o["ca_redirect"],
          {"status": 308, "location": "https://govoss.cat/ca/?src=IT"})
    check("/ serves /index.html", (o["root"]["status"], o["root"]["body"], o["root"]["asked"]),
          (200, "<html>/index.html</html>", ["/index.html"]))
    check("/ is served as HTML whatever the asset's type", o["root"]["type"], "text/html; charset=utf-8")
    check("/ gets a short cache", o["root"]["cache"], "public, max-age=300")
    check("/ca/ serves /ca/index.html", (o["ca_root"]["status"], o["ca_root"]["asked"]),
          (200, ["/ca/index.html"]))
    check("a directory with no index stays a 404", o["dir_without_index"],
          {"status": 404, "asked": ["/nope/index.html"]})
    check("any other path is passed through untouched", o["genuine_404"],
          {"status": 404, "asked": ["/missing.json?x=1"]})

    # ---- www-redirect.js
    w = o["www"]["h"]
    check("www 301s, path and query kept", (o["www"]["status"], w.get("location")),
          (301, "https://govoss.cat/entries.json?cc=DE&q=a%20b"))
    check("www redirect carries CORS (the vercel.app gap)", w.get("access-control-allow-origin"), "*")
    check("www root lands on the apex root", o["www_root"]["location"], "https://govoss.cat/")

    # ---- mcp: transport
    check("OPTIONS preflight: 204 with CORS", o["options"], {"status": 204, "cors": "*"})
    check("GET / describes the server", (o["get_root"]["status"], o["get_root"]["json"]["the_data_itself"]),
          (200, "https://govoss.cat/entries.json"))
    check("non-POST is 405", o["put"]["status"], 405)
    check("bad JSON is a -32700 parse error, status 400",
          (o["bad_json"]["status"], o["bad_json"]["json"]["error"]["code"]), (400, -32700))
    init = o["initialize"]["json"]["result"]
    check("initialize answers the protocol version", init["protocolVersion"], "2024-11-05")
    check("initialize states no catalogue COUNT (it went stale at 17)",
          re.search(r"\b\d+\s+(national|government|catalogue)", init["instructions"]), None)
    check("a notification is never answered: 202, empty",
          (o["notification"]["status"], o["notification"]["empty"]), (202, True))
    check("a batch answers only the request, not the notification",
          [m.get("id") for m in o["batch"]["json"]], [2])
    check("unknown method with an id: -32601", o["unknown"]["json"]["error"]["code"], -32601)
    check("every response carries CORS", o["initialize"]["cors"], "*")

    # ---- mcp: the contract matches mcp_tools.py (two copies are two contracts)
    sys.path.insert(0, HERE)
    import mcp_tools
    js = o["tools_list"]["json"]["result"]["tools"]
    check("tool names and order match mcp_tools.TOOLS",
          [t["name"] for t in js], [t["name"] for t in mcp_tools.TOOLS])
    for t_py in mcp_tools.TOOLS:
        t_js = next((t for t in js if t["name"] == t_py["name"]), None) or {}
        spec = [] if t_py["args"] == "(none)" else [a.strip() for a in t_py["args"].split(",")]
        names = sorted(re.match(r"(\w+)", a).group(1) for a in spec)
        required = sorted(re.match(r"(\w+)", a).group(1) for a in spec if "?" not in a.split(":")[0])
        schema = t_js.get("inputSchema") or {}
        check(f"{t_py['name']}: arguments match", sorted((schema.get("properties") or {}).keys()), names)
        check(f"{t_py['name']}: required arguments match", sorted(schema.get("required") or []), required)

    # ---- mcp: search_entries
    ids = lambda k: [e["id"] for e in o[k]["data"]["entries"]]
    check("also-known-as is searched (Rocket.Chat)", ids("search_aka"), ["a"])
    check("owner is searched (and nothing else says 'regione-marche')", ids("search_owner"), ["c"])
    check("the proprietary products replaced are searched", ids("search_replaces"), ["b"])
    check("country filter reads countries[], not just country", sorted(ids("search_country")), ["a", "b"])
    check("facet filters are AND-ed", ids("search_facets"), ["c"])
    check("most-catalogued first", ids("search_order"), ["b", "c", "a"])
    check("limit is honoured, and the rest counted",
          (ids("search_limit"), o["search_limit"]["data"]["total_matching"]), (["b"], 3))
    check("limit is capped, not trusted", o["search_limit_huge"]["data"]["returned"], 3)

    # ---- mcp: the other tools
    check("find_replacements: exact match is case-insensitive",
          (o["repl_exact"]["data"]["matched_key"], o["repl_exact"]["data"]["alternatives"]),
          ("Slack", [{"name": "Rocketchat"}]))
    check("find_replacements: a contains-match says which key answered",
          o["repl_near"]["data"]["matched_key"], "Microsoft Office")
    check("find_replacements: no mapping is not evidence of none",
          ("not evidence" in o["repl_none"]["data"]["note"], o["repl_none"]["data"]["alternatives"]),
          (True, []))
    check("find_replacements: a missing product is a tool error, inside the result",
          o["repl_missing"]["isError"], True)
    check("get_entry returns the full record", o["entry"]["data"], {"id": "a", "name": "Rocketchat"})
    check("get_entry miss says not found, never guesses",
          (o["entry_miss"]["data"]["found"], o["entry_miss"]["isError"]), (False, False))
    check("list_sources omits the survey unless asked",
          ("survey" in o["sources"]["data"], "survey" in o["sources_survey"]["data"]), (False, True))
    check("an unknown tool is a tool error, not a transport error",
          (o["unknown_tool"]["isError"], "unknown tool" in o["unknown_tool"]["text"]), (True, True))

    # ---- mcp: freshness and failure
    check("a rebuild (new generated_at) is seen without a purge", ids("after_rebuild"), ["z"])
    urls = [c["url"] for c in o["cache_retry_calls"]]
    check("a failed fetch is retried once", len(urls), 2)
    check("...with a CHANGED cache key, not just cacheTtl:0",
          (urls[0] != urls[1], "cb=" in urls[1] and "cb=" not in urls[0]), (True, True))
    check("...and the retry succeeds", o["cache_retry"]["isError"], False)
    check("errors are never cached: non-2xx TTLs are 0",
          (o["cache_retry_calls"][0]["cf"] or {}).get("cacheTtlByStatus", {}).get("400-499"), 0)
    check("a persistent failure is reported inside the result with URL and status",
          (o["index_down"]["isError"],
           "https://govoss.cat/mcp-index.json -> 404" in o["index_down"]["text"]), (True, True))

    for f in failed:
        print(f"FAIL  {f}")
    n = len(ran)
    print(f"\n{n - len(failed)}/{n} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
