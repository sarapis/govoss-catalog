// www.govoss.cat -> govoss.cat, permanently, path and query kept.
//
// A Worker rather than a Cloudflare redirect rule because the deploy login has
// no zone-edit rights. Separate from the site Worker on purpose: the site stays
// assets-first (no script on every request) and only www pays for this.
//
// CORS on the redirect itself: a browser following a cross-origin redirect
// checks CORS on the redirect response too, so without this header a page
// fetching https://www.govoss.cat/entries.json from another site would fail -
// exactly the gap the old vercel.app redirect has.
export default {
  fetch(request) {
    const url = new URL(request.url);
    return new Response(null, {
      status: 301,
      headers: {
        Location: "https://govoss.cat" + url.pathname + url.search,
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=86400",
      },
    });
  },
};
