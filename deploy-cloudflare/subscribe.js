// POST /api/subscribe - "Get project updates" (owner, 2026-10-14).
//
// The form is in every page's footer and on the home page (theme.signup_form).
// A signup is FORWARDED to the Sarapis Payload CMS's shared multi-brand list,
// `campaign-signups` at next.sarapis.org - the same list un.opensource.nyc writes
// to (owner, 2026-10-14: align with the sister sites, not a separate store).
//   { email, campaign: "govoss", source: <page path> }
// `site` is left empty: the CMS reads that as Sarapis, govoss.cat's publisher.
// Anonymous create needs no credential; Payload validates the address again and
// refuses anonymous reads, so nothing here can list the subscribers.
//
// Server to server, so the CMS needs no CORS entry for govoss.cat, and the form
// still works without JavaScript. Guards here: same-origin POST only; a filled
// honeypot (`website`) is answered "ok" and NOT forwarded; a strict address
// pattern; the address is never logged.
// Single opt-in, no unsubscribe link and no automated sending - as on the sister
// sites - so the form promises neither (see theme.signup_form).
//
// A fetch() from the page asks for JSON; a plain form post gets a short HTML page.

export const CMS = "https://next.sarapis.org/api/campaign-signups";
export const CAMPAIGN = "govoss";
const EMAIL = /^[A-Za-z0-9.!#$%&*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}$/;

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const TEXT = {
  en: { ok: "Thanks - you're on the list for govoss.cat updates.", bad: "Please enter a valid email address.",
        fail: "Something went wrong and you were not added. Please try again later.", back: "Back to govoss.cat" },
  ca: { ok: "Gràcies: ja sou a la llista de novetats de govoss.cat.", bad: "Introduïu una adreça electrònica vàlida.",
        fail: "Alguna cosa ha fallat i no us hem afegit. Torneu-ho a provar més tard.", back: "Torna a govoss.cat" },
};

function reply(request, lang, status, key) {
  const t = TEXT[lang] || TEXT.en;
  if ((request.headers.get("accept") || "").includes("application/json")) {
    return Response.json({ ok: key === "ok", message: t[key] }, { status, headers: { "Cache-Control": "no-store" } });
  }
  const home = lang === "ca" ? "/ca/" : "/";
  return new Response(
    `<!doctype html><html lang="${lang}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">` +
    `<meta name="robots" content="noindex"><title>govoss.cat</title>` +
    `<body style="font:16px/1.5 system-ui,sans-serif;max-width:560px;margin:15vh auto;padding:0 20px">` +
    `<p>${esc(t[key])}</p><p><a href="${home}">${esc(t.back)}</a></p></body></html>`,
    { status, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } });
}

function sameOrigin(request, url) {
  const o = request.headers.get("origin");
  if (o) return o === url.origin;
  const r = request.headers.get("referer");
  try { return !!r && new URL(r).origin === url.origin; } catch { return false; }
}

async function readForm(request) {
  const type = request.headers.get("content-type") || "";
  if (type.includes("application/json")) {
    try { return await request.json(); } catch { return {}; }
  }
  try { return Object.fromEntries(await request.formData()); } catch { return {}; }
}

export async function subscribe(request, env, url) {
  if (request.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405, headers: { Allow: "POST" } });
  }
  if (!sameOrigin(request, url)) return new Response("Forbidden", { status: 403 });
  const f = await readForm(request);
  const lang = f.lang === "ca" ? "ca" : "en";
  if (f.website) return reply(request, lang, 200, "ok");          // the honeypot: say yes, send nothing
  const email = String(f.email || "").trim().toLowerCase();
  if (email.length > 254 || !EMAIL.test(email)) return reply(request, lang, 400, "bad");
  const page = /^\/[A-Za-z0-9/_.-]{0,120}$/.test(String(f.page || "")) ? f.page : "/";
  try {
    const res = await fetch(CMS, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ email, campaign: CAMPAIGN, source: page }) });
    if (res.status === 400) return reply(request, lang, 400, "bad");   // Payload refused the address
    if (!res.ok) throw new Error("cms " + res.status);
  } catch (e) {
    console.error("subscribe failed: " + e.message);             // never the address
    return reply(request, lang, 502, "fail");
  }
  return reply(request, lang, 200, "ok");
}
