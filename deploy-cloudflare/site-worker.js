// The govoss site on Cloudflare: static assets from site/, served directly.
//
// This script runs ONLY when no asset matches the request (assets are checked
// first). html_handling is "none", so nothing maps paths to files for us; this
// does, and owns the site's URL scheme since 2026-10-07:
//
//   /software, /catalogs, /docs, /products, /resources (and /ca/...)
//       served from <path>.html - clean paths, no redirect, the .html stays
//       reachable too (its canonical points at the clean path)
//   / and /ca/  served from index.html - the home page
//   /?q=... (any catalog view key)  301 -> /software?q=...  Shared searches were
//       made on / until 2026-10-07; the list lives on /software now
//   /sources.html -> /catalogs, /api.html -> /docs (and /ca/ twins)  301, query
//       kept. Done here, not in _redirects, so the query string provably survives
//       and test_workers.py can pin it. build_site.sh deletes those old files, or
//       an asset would answer before this script ran
//   /ca  308 -> /ca/
const OLD = {
  "/sources.html": "/catalogs",
  "/api.html": "/docs",
  "/ca/sources.html": "/ca/catalogs",
  "/ca/api.html": "/ca/docs",
};
// The catalog's URL keys (build_ui / _ui_template writeURL). A home URL carrying
// any of them is a shared search from before the split.
const VIEW_KEYS = ["q", "fn", "cc", "rp", "src", "lic", "lv", "sort", "alt", "nodesc", "notsoft"];

async function serveHtml(env, request, url, path) {
  const res = await env.ASSETS.fetch(new Request(new URL(path, url.origin), request));
  if (!res.ok) return res;
  const out = new Response(res.body, res);
  out.headers.set("Content-Type", "text/html; charset=utf-8");
  out.headers.set("Cache-Control", "public, max-age=300");
  return out;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const p = url.pathname;
    if (p === "/ca") {
      return Response.redirect(url.origin + "/ca/" + url.search, 308);
    }
    if (OLD[p]) {
      return Response.redirect(url.origin + OLD[p] + url.search, 301);
    }
    if (p === "/" || p === "/ca/") {
      const params = new URLSearchParams(url.search);
      if (VIEW_KEYS.some((k) => params.has(k))) {
        return Response.redirect(url.origin + (p === "/" ? "/software" : "/ca/software") + url.search, 301);
      }
    }
    if (p.endsWith("/")) {
      return serveHtml(env, request, url, p + "index.html");   // a 404 if no index
    }
    if (!p.slice(p.lastIndexOf("/") + 1).includes(".")) {
      // an extensionless path: /software -> /software.html
      const res = await serveHtml(env, request, url, p + ".html");
      if (res.ok) return res;
    }
    return env.ASSETS.fetch(request);   // a genuine 404
  },
};
