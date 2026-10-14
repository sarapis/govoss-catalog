// POST /api/subscribe - "Get project updates" (owner, 2026-10-14).
//
// The form is in every page's footer and on the home page (theme.signup_form).
// A signup goes to the Sarapis CRM (Airtable, base "Sarapis CRM", table People),
// whose rule is ONE ROW PER EMAIL ADDRESS:
//   - an address already there gains Brand "govoss", list "govoss updates" and
//     source "govoss.cat signup" ALONGSIDE what it has (read, union, write back -
//     never an upsert, which would replace the select fields wholesale)
//   - a new address is created with those, First Seen and a note of where and when
// `typecast` lets Airtable create those three select options on first use.
//
// Guards: same-origin POST only; a filled honeypot (`website`) is answered "ok"
// and dropped; the address is checked against a strict pattern that admits no
// quote, so it can never break out of the filterByFormula string.
// The Airtable token is a Worker SECRET (wrangler secret put AIRTABLE_TOKEN
// --config wrangler.site.jsonc); without it the endpoint answers 503 and stores
// nothing. Single opt-in: the form says what the address is used for.
//
// A fetch() from the page asks for JSON; a plain form post (no JavaScript) gets a
// short HTML page.

export const CRM = { base: "app6KkPPGq9NVEAsM", table: "tblcx9dun5fAyGRCn" };
export const BRAND = "govoss", LIST = "govoss updates", SOURCE = "govoss.cat signup";
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
  if (f.website) return reply(request, lang, 200, "ok");          // the honeypot: say yes, store nothing
  const email = String(f.email || "").trim().toLowerCase();
  if (email.length > 254 || !EMAIL.test(email)) return reply(request, lang, 400, "bad");
  if (!env.AIRTABLE_TOKEN) return reply(request, lang, 503, "fail");
  const page = /^\/[A-Za-z0-9/_.-]{0,120}$/.test(String(f.page || "")) ? f.page : "/";
  const api = `https://api.airtable.com/v0/${CRM.base}/${CRM.table}`;
  const auth = { Authorization: `Bearer ${env.AIRTABLE_TOKEN}`, "Content-Type": "application/json" };
  const today = new Date().toISOString().slice(0, 10);
  try {
    const q = new URLSearchParams({ filterByFormula: `LOWER({Email})='${email}'`, maxRecords: "1" });
    ["Brands", "Tags", "Sources"].forEach((k) => q.append("fields[]", k));
    const found = await fetch(`${api}?${q}`, { headers: auth });
    if (!found.ok) throw new Error("search " + found.status);
    const rec = ((await found.json()).records || [])[0];
    const add = (have, v) => [...new Set([...(have || []), v])];
    let res;
    if (rec) {
      const fl = rec.fields || {};
      res = await fetch(api, { method: "PATCH", headers: auth, body: JSON.stringify({ typecast: true, records: [{
        id: rec.id, fields: { Brands: add(fl.Brands, BRAND), Tags: add(fl.Tags, LIST),
                              Sources: add(fl.Sources, SOURCE), "Last Interaction": today } }] }) });
    } else {
      res = await fetch(api, { method: "POST", headers: auth, body: JSON.stringify({ typecast: true, records: [{
        fields: { Name: email, Email: email, Brands: [BRAND], Tags: [LIST], Sources: [SOURCE],
                  "First Seen": today, "Last Interaction": today,
                  Notes: `Signed up for govoss.cat updates on ${new Date().toISOString()} from ${page} (${lang}).` } }] }) });
    }
    if (!res.ok) throw new Error("write " + res.status);
  } catch (e) {
    console.error("subscribe failed: " + e.message);             // never the address
    return reply(request, lang, 502, "fail");
  }
  return reply(request, lang, 200, "ok");
}
