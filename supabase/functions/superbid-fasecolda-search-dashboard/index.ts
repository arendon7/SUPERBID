import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import {
  SEARCH_EXPLORATION_GUARDRAIL,
  buildSearchExplorationVariants,
  type SearchExplorationDisposition,
  type SearchVariant,
} from "./search_exploration.ts";

const U = Deno.env.get("SUPABASE_URL")!;
const K = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const COOKIE = "sb_fasecolda_search_session";
const BASE = "/functions/v1/superbid-fasecolda-search-dashboard";

const esc = (v: unknown) => String(v ?? "").replace(/[&<>"']/g, (m) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[m] || m));

const dt = (v: unknown) => v ? new Intl.DateTimeFormat("es-CO", {
  timeZone: "America/Bogota", dateStyle: "short", timeStyle: "short",
}).format(new Date(String(v))) : "—";

const css = `
:root{--bg:#f4f6f3;--p:#fff;--t:#182018;--m:#687168;--l:#dfe5de;--g:#123d2a;--g2:#1f6a49;--r:#842828;--a:#765400;--b:#425c70}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--t);font:14px/1.45 Inter,system-ui,sans-serif}a{text-decoration:none;color:inherit}.top{background:var(--g);color:#fff;padding:18px 26px;display:flex;justify-content:space-between;gap:14px;align-items:center}.top h1{margin:2px 0}.ey{font-size:10px;letter-spacing:1.4px;font-weight:800;opacity:.72}main{padding:20px 26px 45px;max-width:1700px;margin:auto}.nav,.filters,.actions,.badges{display:flex;gap:7px;flex-wrap:wrap;align-items:center}.btn,button,select,input,textarea{border:1px solid var(--l);border-radius:8px;padding:8px 10px;background:#fff;font:inherit}.btn,button{font-weight:750;cursor:pointer}.primary{background:var(--g2)!important;border-color:var(--g2)!important;color:#fff!important}.danger{border-color:#d4adad!important;color:var(--r)!important}.notice{padding:12px 14px;border:1px solid #ead99c;background:#fff3cf;color:#65490d;border-radius:10px;margin-bottom:14px}.notice.ok{background:#e1f2e6;border-color:#b8dbc3;color:#175935}.notice.bad{background:#f4e5e5;border-color:#dfbbbb;color:var(--r)}.panel,.lot,.metric{background:var(--p);border:1px solid var(--l);border-radius:13px}.panel{margin-bottom:14px}.head{padding:15px 17px;border-bottom:1px solid var(--l);display:flex;justify-content:space-between;gap:10px;align-items:center}.head h2,.lot h2{margin:0}.sub,label span{display:block;color:var(--m);font-size:11px}.stack{display:grid;gap:14px}.lot{padding:17px}.meta{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:12px 0}.kv,.metric{background:#f8faf7;padding:10px;border-radius:8px}.kv span,.metric span{display:block;color:var(--m);font-size:10px;text-transform:uppercase}.metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:9px;margin-bottom:14px}.metric strong{font-size:20px}.pill{font-size:10px;font-weight:800;border-radius:99px;padding:5px 8px;display:inline-block}.expand,.explorable,.hascodes{background:#daf0e1;color:#175935}.nomatch,.missing,.nocodes{background:#fff0c9;color:var(--a)}.identity,.error{background:#f4dfdf;color:#7f2424}.source{background:#e8eef3;color:#425c70}.neutral{background:#ecefec;color:#586158}.form{margin-top:13px;padding-top:13px;border-top:1px solid var(--l)}.form input,.form textarea{width:100%}.form textarea{min-height:72px}.confirm{display:flex;gap:8px;align-items:flex-start;margin:10px 0}.confirm input{width:auto;margin-top:3px}.matrix{display:grid;grid-template-columns:repeat(2,minmax(320px,1fr));gap:10px}.result{border:1px solid var(--l);border-radius:11px;padding:13px;background:#fafbf9}.result h3{margin:3px 0}.codes{display:flex;gap:5px;flex-wrap:wrap;margin:10px 0}.code{font-family:ui-monospace,monospace;background:#eef1ed;border-radius:6px;padding:5px 7px}.login{width:min(430px,92vw);margin:15vh auto;background:#fff;border:1px solid var(--l);border-radius:16px;padding:28px}.login input{width:100%}.login button{width:100%;margin-top:10px}.err{color:var(--r);font-weight:700}@media(max-width:1000px){.meta,.metrics{grid-template-columns:repeat(2,1fr)}.matrix{grid-template-columns:1fr}main{padding:13px}.top{align-items:flex-start}}`;

function html(title: string, body: string, status = 200, headers: Record<string, string> = {}) {
  return new Response(`<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title><style>${css}</style></head><body>${body}</body></html>`, {
    status,
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", ...headers },
  });
}

async function db(path: string, init: RequestInit = {}) {
  return fetch(`${U}${path}`, {
    ...init,
    headers: { apikey: K, authorization: `Bearer ${K}`, "content-type": "application/json", ...(init.headers || {}) },
  });
}

async function rows(path: string) {
  const r = await db(path);
  if (!r.ok) throw new Error(`GET ${r.status}`);
  return r.json();
}

async function one(path: string) {
  const xs = await rows(path);
  return xs[0] || null;
}

function cookie(req: Request) {
  for (const p of (req.headers.get("cookie") || "").split(";")) {
    const [k, ...v] = p.trim().split("=");
    if (k === COOKIE) return decodeURIComponent(v.join("="));
  }
  return "";
}

async function valid(token: string) {
  if (!token || token.length < 32 || token.length > 256) return false;
  const r = await db("/rest/v1/rpc/dashboard_token_valid", { method: "POST", body: JSON.stringify({ p_token: token }) });
  return r.ok && (await r.json()) === true;
}

function pathOf(req: Request) {
  const p = new URL(req.url).pathname;
  const marker = "/superbid-fasecolda-search-dashboard";
  const i = p.indexOf(marker);
  return i >= 0 ? (p.slice(i + marker.length) || "/") : p;
}

function safeLot(v: unknown) {
  const lot = String(v || "").trim();
  return /^\d{5,12}$/.test(lot) ? lot : "";
}

function lotFromPath(p: string) {
  const m = p.match(/^\/lots\/(\d{5,12})(?:\/|$)/);
  return m ? safeLot(m[1]) : "";
}

function redirect(location: string, headers: Record<string, string> = {}) {
  return new Response(null, { status: 303, headers: { location, "cache-control": "no-store", ...headers } });
}

function login(error = false, lot = "") {
  return html("SUPERBID — Fasecolda Search", `<form class="login" method="post" action="${BASE}/login">
    ${lot ? `<input type="hidden" name="lot" value="${esc(lot)}">` : ""}
    <div class="ey">SUPERBID · v0.54</div><h1>Search Exploration Matrix</h1>
    <p class="sub">Acceso privado. Explorar términos consulta la búsqueda pública de Fasecolda, pero no crea candidatos, overrides, homologaciones ni señal de compra.</p>
    ${lot ? `<p class="sub">Continuar con lote ${esc(lot)} después de autenticar.</p>` : ""}
    ${error ? '<p class="err">Credencial inválida.</p>' : ""}
    <input type="password" name="password" autocomplete="current-password" required placeholder="Clave de acceso"><button class="primary">Entrar</button>
  </form>`, error ? 401 : 200);
}

const nav = `<nav class="nav"><a class="btn" href="/functions/v1/superbid-dashboard">Dashboard</a><a class="btn" href="/functions/v1/superbid-readiness-dashboard">Readiness</a><a class="btn" href="/functions/v1/superbid-fasecolda-workbench">Workbench</a><a class="btn" href="/functions/v1/superbid-fasecolda-candidate-cockpit">Candidatos</a><a class="btn" href="${BASE}">Búsqueda</a><a class="btn" href="${BASE}/overrides">Overrides</a><form method="post" action="${BASE}/logout"><button>Salir</button></form></nav>`;

function dispositionPill(v: SearchExplorationDisposition) {
  if (v === "EXPLORABLE") return '<span class="pill explorable">EXPLORABLE</span>';
  if (v === "MISSING_YEAR") return '<span class="pill missing">MISSING_YEAR</span>';
  return '<span class="pill identity">IDENTITY_INPUT_REVIEW</span>';
}

function reasonPill(v: string) {
  const c = v === "SEARCH_TERM_CAN_BE_EXPANDED" ? "expand" : v === "NO_MATCH_ROW" ? "nomatch" : "source";
  return `<span class="pill ${c}">${esc(v)}</span>`;
}

const DIAG_SELECT = "external_lot_id,lot_id,title,brand,line,model_year,city,seller,review_state,review_score,effective_status,current_search_term,suggested_search_term,suggestion_differs,candidate_count,matcher_note,diagnostic_reason,diagnostic_rank,interpretation";

async function loadCase(lot: string) {
  return one(`/rest/v1/dashboard_fasecolda_unmatched_diagnostics?select=${encodeURIComponent(DIAG_SELECT)}&external_lot_id=eq.${encodeURIComponent(lot)}&limit=1`);
}

function explorationFor(x: any) {
  return buildSearchExplorationVariants({
    title: x?.title,
    brand: x?.brand,
    modelYear: x?.model_year,
    currentTerm: x?.current_search_term,
    suggestedTerm: x?.suggested_search_term,
  });
}

async function board(req: Request) {
  const u = new URL(req.url);
  const lot = safeLot(u.searchParams.get("lot"));
  const reason = (u.searchParams.get("reason") || "ALL").toUpperCase();
  const allowed = new Set(["SEARCH_TERM_CAN_BE_EXPANDED", "NO_YEAR_COMPATIBLE_REFERENCE", "PUBLIC_SEARCH_RETURNED_NO_CODES", "NO_MATCH_ROW", "UNMATCHED_OTHER", "ALL"]);
  const rr = allowed.has(reason) ? reason : "ALL";
  let q = `/rest/v1/dashboard_fasecolda_unmatched_diagnostics?select=${encodeURIComponent(DIAG_SELECT)}&order=diagnostic_rank.asc,review_score.desc&limit=200`;
  if (lot) q += `&external_lot_id=eq.${encodeURIComponent(lot)}`;
  if (rr !== "ALL") q += `&diagnostic_reason=eq.${encodeURIComponent(rr)}`;
  const xs = await rows(q);
  const enriched = xs.map((x: any) => ({ ...x, exploration: explorationFor(x) }));
  const counts = {
    total: enriched.length,
    explorable: enriched.filter((x: any) => x.exploration.disposition === "EXPLORABLE").length,
    identity: enriched.filter((x: any) => x.exploration.disposition === "IDENTITY_INPUT_REVIEW").length,
    missing: enriched.filter((x: any) => x.exploration.disposition === "MISSING_YEAR").length,
    noMatch: enriched.filter((x: any) => x.diagnostic_reason === "NO_MATCH_ROW").length,
  };
  const metrics = [["Casos", counts.total], ["Explorables", counts.explorable], ["Identidad entrada", counts.identity], ["Sin año", counts.missing], ["Sin fila match", counts.noMatch]]
    .map(([k, v]) => `<div class="metric"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join("");
  const filter = `<form class="filters" method="get">${lot ? `<input type="hidden" name="lot" value="${esc(lot)}">` : ""}<select name="reason"><option value="ALL" ${rr === "ALL" ? "selected" : ""}>Todos</option><option value="SEARCH_TERM_CAN_BE_EXPANDED" ${rr === "SEARCH_TERM_CAN_BE_EXPANDED" ? "selected" : ""}>Término expandible</option><option value="NO_MATCH_ROW" ${rr === "NO_MATCH_ROW" ? "selected" : ""}>Sin fila de match</option><option value="NO_YEAR_COMPATIBLE_REFERENCE" ${rr === "NO_YEAR_COMPATIBLE_REFERENCE" ? "selected" : ""}>Sin referencia para año</option><option value="PUBLIC_SEARCH_RETURNED_NO_CODES" ${rr === "PUBLIC_SEARCH_RETURNED_NO_CODES" ? "selected" : ""}>Búsqueda sin códigos</option><option value="UNMATCHED_OTHER" ${rr === "UNMATCHED_OTHER" ? "selected" : ""}>Otros</option></select><button class="primary">Aplicar</button>${lot ? `<a class="btn" href="${BASE}">Salir de modo lote</a>` : ""}</form>`;
  const cards = enriched.map((x: any) => {
    const ex = x.exploration;
    const terms = ex.variants.map((v: SearchVariant) => `<span class="code">${esc(v.term)}</span>`).join("");
    const action = ex.disposition === "EXPLORABLE"
      ? `<form method="post" action="${BASE}/lots/${esc(x.external_lot_id)}/explore"><button class="primary">Explorar ${esc(ex.variants.length)} variante(s)</button></form>`
      : `<div class="notice ${ex.disposition === "IDENTITY_INPUT_REVIEW" ? "bad" : ""}">${ex.disposition === "IDENTITY_INPUT_REVIEW" ? "La marca/identidad canónica del lote no permite probes seguros. Corregir identidad antes de buscar." : "Falta año de modelo; resolver año antes de explorar Fasecolda."}</div>`;
    const manualProbe = ex.disposition === "EXPLORABLE"
      ? `<form class="form" method="post" action="${BASE}/lots/${esc(x.external_lot_id)}/probe"><label><span>Probe manual avanzado</span><input name="term" maxlength="80" required placeholder="Término exacto que desea probar"></label><p class="sub">El backend revalida que el caso siga siendo EXPLORABLE y exige preservar la marca canónica. El probe manual tampoco persiste nada.</p><button>Probar un término manual</button></form>`
      : "";
    return `<article class="lot"><div class="head" style="padding:0 0 10px;border:0"><div><h2>${esc(x.title)}</h2><div class="sub">Lote ${esc(x.external_lot_id)} · ${esc([x.city, x.seller].filter(Boolean).join(" · "))}</div></div><div class="badges">${reasonPill(x.diagnostic_reason)}${dispositionPill(ex.disposition)}</div></div><div class="meta"><div class="kv"><span>Brand canónico</span><strong>${esc(x.brand || "—")}</strong></div><div class="kv"><span>Año</span><strong>${esc(x.model_year ?? "—")}</strong></div><div class="kv"><span>Estado</span><strong>${esc(x.effective_status)}</strong></div><div class="kv"><span>Término actual</span><strong>${esc(x.current_search_term || "—")}</strong></div><div class="kv"><span>Sugerido</span><strong>${esc(x.suggested_search_term || "—")}</strong></div><div class="kv"><span>Candidatos actuales</span><strong>${esc(x.candidate_count ?? 0)}</strong></div></div><div class="codes">${terms || '<span class="sub">Sin variantes seguras.</span>'}</div>${action}${manualProbe}<p><a class="btn" href="/functions/v1/superbid-fasecolda-workbench?lot=${esc(x.external_lot_id)}">Volver al caso</a> <a class="btn" href="/functions/v1/superbid-dashboard/lots/${esc(x.external_lot_id)}">Detalle del lote</a></p></article>`;
  }).join("");
  return html("SUPERBID — Search Exploration", `<header class="top"><div><div class="ey">SUPERBID · v0.54</div><h1>Fasecolda Search Exploration Matrix</h1></div>${nav}</header><main>${lot ? `<div class="notice ok"><strong>Modo lote ${esc(lot)}.</strong> El diagnóstico está restringido al caso seleccionado.</div>` : ""}<div class="notice"><strong>${esc(SEARCH_EXPLORATION_GUARDRAIL)} · FASECOLDA_SEARCH_PROBE_NOT_MATCH · CASE_CONTEXT_ROUTING_NOT_BUY_SIGNAL.</strong> Las variantes son hipótesis de búsqueda. Explorar ejecuta probes read-only y nunca selecciona un término ganador. Un override solo puede confirmarse individualmente después de revisar un resultado con códigos públicos.</div><section class="metrics">${metrics}</section><section class="panel"><div class="head"><div><h2>${esc(enriched.length)} diagnósticos</h2><span class="sub">Los casos de identidad de entrada y año se separan del problema de búsqueda.</span></div>${filter}</div></section><div class="stack">${cards || '<section class="lot">Sin casos para este filtro.</section>'}</div></main>`);
}

type ProbeResult = {
  term: string;
  origin: string;
  ok: boolean;
  httpStatus?: number;
  codeCount: number;
  codes: unknown[];
  error?: string;
};

async function runProbe(lot: string, variant: SearchVariant): Promise<ProbeResult> {
  try {
    const r = await db("/rest/v1/rpc/dashboard_probe_fasecolda_search_term", { method: "POST", body: JSON.stringify({ p_external_lot_id: lot, p_term: variant.term }) });
    if (!r.ok) return { term: variant.term, origin: variant.origin, ok: false, codeCount: 0, codes: [], error: (await r.text()).slice(0, 220) };
    const j = await r.json();
    return { term: variant.term, origin: variant.origin, ok: true, httpStatus: Number(j.http_status), codeCount: Number(j.code_count || 0), codes: Array.isArray(j.codes) ? j.codes : [] };
  } catch (e) {
    return { term: variant.term, origin: variant.origin, ok: false, codeCount: 0, codes: [], error: e instanceof Error ? e.message : String(e) };
  }
}

function overrideForm(lot: string, term: string) {
  return `<form class="form" method="post" action="${BASE}/lots/${esc(lot)}/override"><input type="hidden" name="term" value="${esc(term)}"><label><span>Fundamento humano obligatorio</span><textarea name="note" minlength="10" maxlength="2000" required placeholder="Por qué este término representa mejor la línea pública del vehículo y por qué decide usarlo."></textarea></label><label class="confirm"><input type="checkbox" name="confirm_override" value="YES" required><span>Confirmo que revisé este resultado concreto y quiero reejecutar el matcher normal con este término. Esto NO fuerza HIGH ni selecciona un código Fasecolda.</span></label><button class="primary">Confirmar solo este término</button></form>`;
}

async function explore(lot: string) {
  const x = await loadCase(lot);
  if (!x) return html("Caso no disponible", `<main><div class="notice bad">El lote ${esc(lot)} no está actualmente en el workflow de búsqueda Fasecolda.</div><a class="btn" href="${BASE}">Volver</a></main>`, 404);
  const ex = explorationFor(x);
  if (ex.disposition !== "EXPLORABLE" || ex.variants.length === 0) {
    return html("Exploración bloqueada", `<header class="top"><div><div class="ey">SUPERBID · v0.54</div><h1>Exploración bloqueada · ${esc(lot)}</h1></div>${nav}</header><main><div class="notice bad"><strong>${esc(ex.disposition)}.</strong> Este caso no admite exploración automática segura de términos. No se ejecutó ningún probe.</div><a class="btn" href="${BASE}?lot=${esc(lot)}&reason=ALL">Volver</a></main>`, 409);
  }
  const results: ProbeResult[] = [];
  for (const variant of ex.variants) results.push(await runProbe(lot, variant));
  const successful = results.filter((r) => r.ok && r.codeCount > 0).length;
  const matrix = results.map((r) => {
    const cls = !r.ok ? "error" : r.codeCount > 0 ? "hascodes" : "nocodes";
    const label = !r.ok ? "ERROR PROBE" : r.codeCount > 0 ? "DEVOLVIÓ CÓDIGOS" : "SIN CÓDIGOS";
    const codes = r.codes.slice(0, 22).map((c) => `<span class="code">${esc(typeof c === "string" ? c : JSON.stringify(c))}</span>`).join("");
    return `<article class="result"><span class="pill ${cls}">${label}</span><div class="sub">${esc(r.origin)}</div><h3>${esc(r.term)}</h3><div class="meta"><div class="kv"><span>HTTP</span><strong>${esc(r.httpStatus ?? "—")}</strong></div><div class="kv"><span>Códigos</span><strong>${esc(r.codeCount)}</strong></div></div>${r.error ? `<div class="notice bad">${esc(r.error)}</div>` : `<div class="codes">${codes || '<span class="sub">Sin códigos públicos.</span>'}</div>`}${r.ok && r.codeCount > 0 ? overrideForm(lot, r.term) : ""}</article>`;
  }).join("");
  return html("SUPERBID — Search Matrix", `<header class="top"><div><div class="ey">SUPERBID · v0.54</div><h1>Search Exploration · lote ${esc(lot)}</h1></div>${nav}</header><main><div class="notice"><strong>${esc(SEARCH_EXPLORATION_GUARDRAIL)}.</strong> Se ejecutaron ${esc(results.length)} probes secuenciales read-only. La cantidad de códigos no es un score de calidad y el sistema no elige ningún término ganador.</div><section class="panel"><div class="head"><div><h2>${esc(x.title)}</h2><span class="sub">Actual: ${esc(x.current_search_term || "—")} · sugerido: ${esc(x.suggested_search_term || "—")}</span></div><span class="pill ${successful ? "hascodes" : "nocodes"}">${esc(successful)} variante(s) con códigos</span></div></section><div class="matrix">${matrix}</div><p style="margin-top:14px"><a class="btn" href="${BASE}?lot=${esc(lot)}&reason=ALL">Volver al diagnóstico</a> <a class="btn" href="/functions/v1/superbid-fasecolda-workbench?lot=${esc(lot)}">Volver al caso</a></p></main>`);
}

async function singleProbe(lot: string, req: Request) {
  try {
    const x = await loadCase(lot);
    if (!x) return html("Caso no disponible", `<main><div class="notice bad">El lote ${esc(lot)} no está actualmente en el workflow de búsqueda Fasecolda.</div><a class="btn" href="${BASE}">Volver</a></main>`, 404);
    const ex = explorationFor(x);
    if (ex.disposition !== "EXPLORABLE") {
      return html("Probe bloqueado", `<main><div class="notice bad"><strong>${esc(ex.disposition)}.</strong> El probe manual también está bloqueado hasta corregir la identidad/año de entrada. No se llamó a Fasecolda.</div><a class="btn" href="${BASE}?lot=${esc(lot)}&reason=ALL">Volver</a></main>`, 409);
    }
    const f = await req.formData();
    const term = String(f.get("term") || "").trim();
    const r = await db("/rest/v1/rpc/dashboard_probe_fasecolda_search_term", { method: "POST", body: JSON.stringify({ p_external_lot_id: lot, p_term: term }) });
    if (!r.ok) throw new Error((await r.text()).slice(0, 300));
    const pr = await r.json();
    const codes = Array.isArray(pr.codes) ? pr.codes : [];
    const codeHtml = codes.map((c: unknown) => `<span class="code">${esc(typeof c === "string" ? c : JSON.stringify(c))}</span>`).join("");
    const confirm = pr.has_codes ? overrideForm(lot, pr.term) : `<div class="notice">El probe no devolvió códigos públicos. No se habilita confirmación de override.</div>`;
    return html("SUPERBID — Probe Fasecolda", `<header class="top"><div><div class="ey">SUPERBID · v0.54</div><h1>Resultado de probe manual</h1></div>${nav}</header><main><div class="notice"><strong>FASECOLDA_SEARCH_PROBE_NOT_MATCH · ${esc(SEARCH_EXPLORATION_GUARDRAIL)}.</strong> Resultado de búsqueda, no homologación.</div><section class="lot"><h2>Lote ${esc(lot)}</h2><div class="meta"><div class="kv"><span>Término</span><strong>${esc(pr.term)}</strong></div><div class="kv"><span>HTTP</span><strong>${esc(pr.http_status)}</strong></div><div class="kv"><span>Códigos</span><strong>${esc(pr.code_count)}</strong></div><div class="kv"><span>Actual</span><strong>${esc(pr.current_search_term || "—")}</strong></div><div class="kv"><span>Sugerido</span><strong>${esc(pr.suggested_search_term || "—")}</strong></div></div><div class="codes">${codeHtml || '<span class="sub">Sin códigos.</span>'}</div>${confirm}<p><a class="btn" href="${BASE}?lot=${esc(lot)}&reason=ALL">Volver</a></p></section></main>`);
  } catch (e) {
    return html("Error", `<main><div class="notice bad">${esc(e instanceof Error ? e.message : "Probe inválido")}</div><a class="btn" href="${BASE}?lot=${esc(lot)}&reason=ALL">Volver</a></main>`, 400);
  }
}

async function overrideTerm(lot: string, req: Request) {
  try {
    const x = await loadCase(lot);
    if (!x) throw new Error("El lote ya no está en el workflow de búsqueda Fasecolda.");
    const ex = explorationFor(x);
    if (ex.disposition !== "EXPLORABLE") throw new Error(`Override bloqueado por ${ex.disposition}; corrija primero la identidad/año de entrada.`);
    const f = await req.formData();
    const term = String(f.get("term") || "").trim();
    const note = String(f.get("note") || "").trim();
    if (String(f.get("confirm_override") || "") !== "YES") throw new Error("Debe confirmar explícitamente el override del término.");
    if (note.length < 10) throw new Error("El fundamento humano debe tener al menos 10 caracteres.");
    if (note.length > 2000) throw new Error("El fundamento supera 2000 caracteres.");
    const r = await db("/rest/v1/rpc/dashboard_set_fasecolda_search_term_override", { method: "POST", body: JSON.stringify({ p_external_lot_id: lot, p_action: "CONFIRM", p_term: term, p_note: note }) });
    if (!r.ok) throw new Error((await r.text()).slice(0, 350));
    return redirect(`/functions/v1/superbid-fasecolda-workbench?lot=${encodeURIComponent(lot)}`);
  } catch (e) {
    return html("Error", `<main><div class="notice bad">${esc(e instanceof Error ? e.message : "Override inválido")}</div><a class="btn" href="${BASE}?lot=${esc(lot)}&reason=ALL">Volver</a></main>`, 400);
  }
}

async function overridesPage(req: Request) {
  const xs = await rows("/rest/v1/lot_fasecolda_search_term_overrides?select=external_lot_id,search_term,note,confirmed_at,updated_at&order=updated_at.desc&limit=200");
  const cleared = new URL(req.url).searchParams.get("cleared") === "1";
  const cards = xs.map((x: any) => `<article class="lot"><h2>Lote ${esc(x.external_lot_id)}</h2><div class="meta"><div class="kv"><span>Término</span><strong>${esc(x.search_term)}</strong></div><div class="kv"><span>Confirmado</span><strong>${dt(x.confirmed_at)}</strong></div><div class="kv"><span>Actualizado</span><strong>${dt(x.updated_at)}</strong></div></div><p>${esc(x.note || "")}</p><form class="form" method="post" action="${BASE}/lots/${esc(x.external_lot_id)}/clear"><label><span>Motivo para retirar</span><textarea name="note" minlength="10" maxlength="2000" required></textarea></label><label class="confirm"><input type="checkbox" name="confirm_clear" value="YES" required><span>Confirmo que quiero retirar el término manual y reejecutar el matcher con el término derivado del título.</span></label><button class="danger">Retirar override</button></form><p><a class="btn" href="/functions/v1/superbid-fasecolda-workbench?lot=${esc(x.external_lot_id)}">Abrir caso</a></p></article>`).join("");
  return html("SUPERBID — Overrides Fasecolda", `<header class="top"><div><div class="ey">SUPERBID · v0.54</div><h1>Overrides activos de búsqueda</h1></div>${nav}</header><main>${cleared ? '<div class="notice ok">Override retirado; el matcher volvió al término derivado del título.</div>' : ""}<div class="notice">MANUAL_FASECOLDA_SEARCH_TERM_NOT_MATCH: un override cambia únicamente el término de búsqueda; el matcher conserva su autoridad y puede seguir devolviendo UNMATCHED/MEDIUM/AMBIGUOUS/HIGH según sus reglas.</div><div class="stack">${cards || '<section class="lot">No hay overrides activos.</section>'}</div></main>`);
}

async function clearOverride(lot: string, req: Request) {
  try {
    const f = await req.formData();
    const note = String(f.get("note") || "").trim();
    if (String(f.get("confirm_clear") || "") !== "YES") throw new Error("Debe confirmar explícitamente el retiro.");
    if (note.length < 10) throw new Error("El motivo debe tener al menos 10 caracteres.");
    const r = await db("/rest/v1/rpc/dashboard_set_fasecolda_search_term_override", { method: "POST", body: JSON.stringify({ p_external_lot_id: lot, p_action: "CLEAR", p_term: null, p_note: note }) });
    if (!r.ok) throw new Error((await r.text()).slice(0, 350));
    return redirect(`${BASE}/overrides?cleared=1`);
  } catch (e) {
    return html("Error", `<main><div class="notice bad">${esc(e instanceof Error ? e.message : "Retiro inválido")}</div><a class="btn" href="${BASE}/overrides">Volver</a></main>`, 400);
  }
}

Deno.serve(async (req: Request) => {
  try {
    const p = pathOf(req);
    const u = new URL(req.url);
    const requestedLot = lotFromPath(p) || safeLot(u.searchParams.get("lot"));
    if (p === "/login" && req.method === "POST") {
      const f = await req.formData();
      const password = String(f.get("password") || "");
      const lot = safeLot(f.get("lot"));
      if (!await valid(password)) return login(true, lot);
      const target = lot ? `${BASE}?lot=${encodeURIComponent(lot)}&reason=ALL` : BASE;
      return redirect(target, { "set-cookie": `${COOKIE}=${encodeURIComponent(password)}; Path=${BASE}; HttpOnly; Secure; SameSite=Strict; Max-Age=28800` });
    }
    const token = cookie(req);
    if (!await valid(token)) return login(false, requestedLot);
    if (p === "/logout" && req.method === "POST") return redirect(BASE, { "set-cookie": `${COOKIE}=; Path=${BASE}; HttpOnly; Secure; SameSite=Strict; Max-Age=0` });
    const lot = lotFromPath(p);
    if (lot && p.endsWith("/explore") && req.method === "POST") return explore(lot);
    if (lot && p.endsWith("/probe") && req.method === "POST") return singleProbe(lot, req);
    if (lot && p.endsWith("/override") && req.method === "POST") return overrideTerm(lot, req);
    if (lot && p.endsWith("/clear") && req.method === "POST") return clearOverride(lot, req);
    if (p === "/overrides" && req.method === "GET") return overridesPage(req);
    if ((p === "/" || p === "") && req.method === "GET") return board(req);
    return html("No encontrado", "<main>Ruta no encontrada.</main>", 404);
  } catch (e) {
    return html("Error", `<main><div class="notice bad">Error interno del dashboard. ${esc(e instanceof Error ? e.message : String(e))}</div></main>`, 500);
  }
});
