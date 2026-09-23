// The govoss site on Cloudflare: static assets from site/, served directly.
//
// This script runs ONLY when no asset matches the request (assets are checked
// first). It exists because of one setting: html_handling is "none", so that
// /sources.html is served as-is - every page, link, canonical and hreflang uses
// the .html URL, and the default mode would 307 it to /sources. "none" also
// switches off directory indexes, so / and /ca/ would 404. This restores them,
// and gives /ca the trailing slash Vercel's copy answered without.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/ca") {
      return Response.redirect(url.origin + "/ca/" + url.search, 308);
    }
    if (url.pathname.endsWith("/")) {
      const idx = new URL(url.pathname + "index.html", url.origin);
      const res = await env.ASSETS.fetch(new Request(idx, request));
      if (res.ok) {
        const out = new Response(res.body, res);
        out.headers.set("Content-Type", "text/html; charset=utf-8");
        out.headers.set("Cache-Control", "public, max-age=300");
        return out;
      }
      return res;
    }
    return env.ASSETS.fetch(request);   // a genuine 404
  },
};
