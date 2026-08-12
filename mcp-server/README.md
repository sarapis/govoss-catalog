# govoss-mcp

MCP server over the govoss-catalog union catalogue. Public, keyless, stateless.

    https://govoss-mcp.devin-31f.workers.dev

## Deploying

    cd mcp-server && npm install && npx wrangler deploy

It is **not** part of `run.sh`. The Worker holds no data — it reads the
published JSON at request time — so a weekly catalogue rebuild reaches it with
no redeploy. Deploy only when this code changes.

## Design notes

- **No Durable Object, no KV, no OAuth**, unlike the tasks-mcp Worker. There is
  nothing to authenticate (the data is public) and no session to keep. Every
  binding not declared is one that cannot misconfigure.
- **Reads `mcp-index.json`, not `entries.json`, for search.** A Worker gets 10ms
  of CPU per request; parsing the 5.6 MB export would blow that on a cold
  isolate. The index is the same data reduced to the fields search needs —
  852 KB, ~3ms to parse — and `export_json.py` writes it in the same run that
  writes `entries.json`, so they cannot drift.
- **The parsed index is memoised at module scope**, keyed on `generated_at`.
  Isolates are reused, so the parse is paid on a cold start and amortised away;
  a Monday rebuild changes the key and invalidates it without a purge.
- **`get_entry` does read the full export** — a single lookup is worth the bytes,
  and the edge cache makes it cheap after the first call.
- **It reads the same public URLs as everyone else.** No privileged access, so
  the server can never return something the published data does not contain.

## Tools

`search_entries` · `find_replacements` · `get_entry` · `list_sources` · `get_stats`

Definitions live in `../mcp_tools.py`, which `/api.html` also reads, so the
documented contract and the implemented one come from one file.
