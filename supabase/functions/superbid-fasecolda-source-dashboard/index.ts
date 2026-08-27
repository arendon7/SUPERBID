import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const U = Deno.env.get("SUPABASE_URL")!;
const K = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const COOKIE = "sb_fasecolda_source_session";
const GUARDRAIL = "CANDIDATE_SOURCE_TRIAGE_NOT_EVIDENCE_MATCH_OR_VALUATION";
const RESEARCH_GUARDRAIL = "SOURCE_RESEARCH_PRIORITY_METADATA_ONLY_NOT_EVIDENCE_MATCH_OR_VALUATION";
const HANDOFF_GUARDRAIL = "SOURCE_CONTEXT_HANDOFF_NOT_EVIDENCE_OR_CANDIDATE_SELECTION";

const CLASSES = new Set([
  "ALL",
  "SINGLE_CANDIDATE_LOW_CONFIDENCE",
  "TITLE_DISCRIMINATOR_AVAILABLE",
  "TITLE_PROXY_CONFLICT",
  "STRUCTURED_DIFFERENCE_SOURCE_UNRESOLVED",
  "TRIM_OR_EXTERNAL_SOURCE_REQUIRED",
]);
const RESEARCH_ROUTES = new Set([
  "ALL",
  "REVIEW_IDENTITY_PRIMARY_SOURCE",
  "REVIEW_IDENTITY_SECONDARY_SOURCE",
  "REVIEW_PERITAJE_FOR_IDENTITY_FACTS",
  "REVIEW_OTHER_REGISTERED_SOURCE",
  "ACQUIRE_EXTERNAL_IDENTITY_SOURCE",
]);

const esc = (v: unknown) => String(v ?? "").replace(/[&<>"']/g, (m) => ({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;",
}[m] || m));
const cop = (v: unknown) => v == null ? "—" : new Intl.NumberFormat("es-CO", {
  style:"currency", currency:"COP", maximumFractionDigits:0,
}).format(Number(v));
const dt = (v: unknown) => v ? new Intl.DateTimeFormat("es-CO", {
  timeZone:"America/Bogota", dateStyle:"short", timeStyle:"short",
}).format(new Date(String(v))) : "—";

const css = `
:root{--bg:#f4f6f3;--p:#fff;--t:#182018;--m:#687168;--l:#dfe5de;--g:#123d2a;--g2:#1f6a49;--r:#842828;--a:#765400;--b:#425c70}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--t);font:14px/1.45 Inter,system-ui,sans-serif}a{text-decoration:none;color:inherit}.top{background:var(--g);color:#fff;padding:18px 26px;display:flex;justify-content:space-between;gap:12px;align-items:center}.ey{font-size:10px;letter-spacing:1.3px;font-weight:800;opacity:.72}.top h1{margin:2px 0}main{max-width:1850px;margin:auto;padding:20px 26px 45px}.nav,.filters,.actions,.chips{display:flex;gap:7px;flex-wrap:wrap;align-items:center}.btn,button,input,select,textarea{border:1px solid var(--l);border-radius:8px;padding:8px 10px;background:#fff;font:inherit}.btn,button{cursor:pointer;font-weight:750}.primary{background:var(--g2)!important;color:#fff!important;border-color:var(--g2)!important}.danger{color:var(--r)!important;border-color:#d8aaaa!important;background:#fff7f7!important}.notice{padding:12px 14px;border:1px solid #ead99c;background:#fff3cf;color:#65490d;border-radius:10px;margin-bottom:14px}.ok{background:#e1f2e6;border-color:#b8dbc3;color:#175935}.bad{background:#f4e5e5;border-color:#dfbbbb;color:var(--r)}.panel,.metric{background:#fff;border:1px solid var(--l);border-radius:13px}.metrics{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:14px}.metric{padding:14px}.metric span,.sub,label span{display:block;color:var(--m);font-size:11px}.metric strong{font-size:21px}.head{padding:15px 17px;border-bottom:1px solid var(--l);display:flex;justify-content:space-between;gap:10px;align-items:center}.head h2{margin:0}.section{padding:16px}.tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:1550px}th,td{padding:9px 10px;border-bottom:1px solid #edf0ec;text-align:left;vertical-align:top;white-space:nowrap}th{font-size:10px;text-transform:uppercase;color:var(--m);background:#fafbf9}.wrap{white-space:normal;min-width:300px}.pill{font-size:10px;font-weight:800;border-radius:99px;padding:5px 8px;display:inline-block}.source{background:#fff0c9;color:#72510a}.evidence{background:#daf0e1;color:#175935}.stale{background:#f4dfdf;color:#7f2424}.info{background:#e8eef3;color:#425c70}.none{background:#ecefec;color:#586158}.primary-source{background:#daf0e1;color:#175935}.secondary-source{background:#e1edf4;color:#36566a}.condition-source{background:#fff0c9;color:#72510a}.other-source{background:#eee7f4;color:#68457a}.acquire-source{background:#f4e5e5;color:#7f2424}.admin-source{background:#ecefec;color:#586158}.two{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start}.candidate-grid{display:grid;grid-template-columns:repeat(3,minmax(280px,1fr));gap:10px}.candidate{padding:12px;border:1px solid var(--l);border-radius:10px;background:#fafbf9}.candidate.target{border:2px solid var(--b)}.candidate h3{margin:2px 0}.source-list{display:grid;gap:8px}.source-card{border:1px solid var(--l);padding:10px;border-radius:9px;background:#fafbf9;overflow-wrap:anywhere}.source-card.first{border:2px solid var(--b)}.viewer{width:100%;height:720px;border:1px solid var(--l);border-radius:9px;background:#fff}.form textarea{width:100%;min-height:110px}.history{margin-top:14px}.login{width:min(440px,92vw);margin:15vh auto;background:#fff;border:1px solid var(--l);border-radius:16px;padding:28px}.login input,.login button{width:100%}.login button{margin-top:10px}.err{color:var(--r);font-weight:700}
@media(max-width:1100px){.metrics{grid-template-columns:repeat(3,1fr)}.two{grid-template-columns:1fr}.candidate-grid{grid-template-columns:1fr 1fr}}@media(max-width:720px){main{padding:13px}.top{align-items:flex-start}.metrics,.candidate-grid{grid-template-columns:1fr}.viewer{height:520px}}
`;

function html(title:string, body:string, status=200, headers:Record<string,string>={}) {
  return new Response(`<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title><style>${css}</style></head><body>${body}</body></html>`, {
    status, headers:{"content-type":"text/html; charset=utf-8","cache-control":"no-store",...headers},
  });
}
async function db(path:string, init:RequestInit={}) {
  return fetch(`${U}${path}`, {...init,headers:{apikey:K,authorization:`Bearer ${K}`,"content-type":"application/json",...(init.headers||{})}});
}
async function rows(path:string) { const r=await db(path); if(!r.ok) throw new Error(`GET ${r.status}`); return r.json(); }
async function one(path:string) { const xs=await rows(path); return xs[0]||null; }
function cookie(req:Request) { for(const p of (req.headers.get("cookie")||"").split(";")){const [k,...v]=p.trim().split("=");if(k===COOKIE)return decodeURIComponent(v.join("="));} return ""; }
async function valid(t:string) { if(!t||t.length<32||t.length>256)return false;const r=await db("/rest/v1/rpc/dashboard_token_valid",{method:"POST",body:JSON.stringify({p_token:t})});return r.ok&&(await r.json())===true; }
function pathOf(req:Request){const p=new URL(req.url).pathname,m="/superbid-fasecolda-source-dashboard",i=p.indexOf(m);return i>=0?(p.slice(i+m.length)||"/"):p;}
function safeLot(v:unknown){const x=String(v??"").trim();return /^\d{5,12}$/.test(x)?x:"";}
function lotFromPath(p:string){const m=p.match(/^\/lots\/(\d{5,12})(?:\/|$)/);return m?safeLot(m[1]):"";}
function safeHttpUrl(v:unknown){try{const u=new URL(String(v??""));return u.protocol==="https:"||u.protocol==="http:"?u.toString():"";}catch{return "";}}
function redirect(location:string,headers:Record<string,string>={}){return new Response(null,{status:303,headers:{location,"cache-control":"no-store",...headers}});}
function arr(v:unknown){return Array.isArray(v)?v.map(String):[];}
function objArr(v:unknown){return Array.isArray(v)?v.filter(x=>x&&typeof x==="object") as Record<string,unknown>[]:[];}

async function allowedSourceForLot(lot:string,raw:unknown){
  const requested=safeHttpUrl(raw);if(!requested)return "";
  const x=await one(`/rest/v1/dashboard_fasecolda_source_research_priority_v57?select=${encodeURIComponent("auction_url,source_inventory")}&external_lot_id=eq.${encodeURIComponent(lot)}&order=lot_id.desc&limit=1`);
  if(!x)return "";
  const allowed=new Set<string>();
  const publicUrl=safeHttpUrl(x.auction_url);if(publicUrl)allowed.add(publicUrl);
  for(const s of objArr(x.source_inventory)){const url=safeHttpUrl(s.url);if(url)allowed.add(url);}
  return allowed.has(requested)?requested:"";
}

function login(error=false,lot="",source=""){
  const safeSource=safeHttpUrl(source);
  return html("SUPERBID — Source Research",`<form class="login" method="post" action="/functions/v1/superbid-fasecolda-source-dashboard/login">${lot?`<input type="hidden" name="lot" value="${esc(lot)}">`:""}${safeSource?`<input type="hidden" name="source" value="${esc(safeSource)}">`:""}<div class="ey">SUPERBID · v0.58</div><h1>Fasecolda Source Research</h1><p class="sub">Acceso privado. La prioridad usa únicamente metadata de fuentes registradas; no inspecciona el contenido ni homologa vehículos.</p>${lot?`<p class="sub">Continuar con lote ${esc(lot)} después de autenticar.</p>`:""}${error?'<p class="err">Credencial inválida.</p>':""}<input type="password" name="password" autocomplete="current-password" required placeholder="Clave de acceso"><button class="primary">Entrar</button></form>`,error?401:200);
}
const nav=`<nav class="nav"><a class="btn" href="/functions/v1/superbid-dashboard">Dashboard</a><a class="btn" href="/functions/v1/superbid-readiness-dashboard">Readiness</a><a class="btn" href="/functions/v1/superbid-fasecolda-workbench">Fasecolda</a><a class="btn" href="/functions/v1/superbid-fasecolda-candidate-cockpit">Evidencia candidatos</a><a class="btn" href="/functions/v1/superbid-fasecolda-search-dashboard">Búsqueda</a><form method="post" action="/functions/v1/superbid-fasecolda-source-dashboard/logout"><button>Salir</button></form></nav>`;

function routePill(v:unknown){const x=String(v||"SOURCE_TRIAGE"),c=x==="EVIDENCE_REVIEW"?"evidence":x==="SOURCE_TRIAGE"?"source":x.includes("INSUFFICIENT")?"none":"info";return `<span class="pill ${c}">${esc(x)}</span>`;}
function dispositionPill(v:unknown){const x=String(v||"NONE"),c=x==="CURRENT"?"evidence":x==="STALE"?"stale":"none";return `<span class="pill ${c}">${esc(x)}</span>`;}
function researchRoutePill(v:unknown){const x=String(v||"ACQUIRE_EXTERNAL_IDENTITY_SOURCE"),c=x==="REVIEW_IDENTITY_PRIMARY_SOURCE"?"primary-source":x==="REVIEW_IDENTITY_SECONDARY_SOURCE"?"secondary-source":x==="REVIEW_PERITAJE_FOR_IDENTITY_FACTS"?"condition-source":x==="REVIEW_OTHER_REGISTERED_SOURCE"?"other-source":"acquire-source";return `<span class="pill ${c}">${esc(x)}</span>`;}
function sourceRolePill(v:unknown){const x=String(v||"OTHER_REGISTERED"),c=x==="IDENTITY_PRIMARY"?"primary-source":x==="IDENTITY_SECONDARY"?"secondary-source":x==="CONDITION_IDENTITY_POTENTIAL"?"condition-source":x==="ADMINISTRATIVE_GENERIC"?"admin-source":"other-source";return `<span class="pill ${c}">${esc(x)}</span>`;}

async function board(req:Request){
  const u=new URL(req.url),clsRaw=(u.searchParams.get("class")||"ALL").toUpperCase(),researchRaw=(u.searchParams.get("research")||"ALL").toUpperCase();
  const cls=CLASSES.has(clsRaw)?clsRaw:"ALL",research=RESEARCH_ROUTES.has(researchRaw)?researchRaw:"ALL";
  const sel="external_lot_id,title,brand,line,model_year,city,seller,closes_at,automatic_status,current_candidate_count,structured_discriminator_count,structured_discriminators,duplicate_description_group_count,attachment_count,peritaje_count,source_triage_class,disposition_status,current_disposition_action,operational_route,source_triage_reason,identity_primary_count,identity_secondary_count,condition_identity_potential_count,administrative_generic_count,other_registered_count,first_review_source_name,first_review_source_role,research_route,research_rank,research_reason,source_research_actionable";
  let q=`/rest/v1/dashboard_fasecolda_source_research_queue_v571?select=${encodeURIComponent(sel)}&source_research_actionable=eq.true&order=research_rank.asc,closes_at.asc&limit=500`;
  if(cls!=="ALL")q+=`&source_triage_class=eq.${encodeURIComponent(cls)}`;
  if(research!=="ALL")q+=`&research_route=eq.${encodeURIComponent(research)}`;
  const xs=await rows(q);
  const all=await rows(`/rest/v1/dashboard_fasecolda_source_research_queue_v571?select=${encodeURIComponent("external_lot_id,research_route,disposition_status")}&source_research_actionable=eq.true&limit=500`);
  const cards=[["Casos accionables",all.length],["Identidad primaria",all.filter((x:any)=>x.research_route==="REVIEW_IDENTITY_PRIMARY_SOURCE").length],["Identidad secundaria",all.filter((x:any)=>x.research_route==="REVIEW_IDENTITY_SECONDARY_SOURCE").length],["Peritaje potencial",all.filter((x:any)=>x.research_route==="REVIEW_PERITAJE_FOR_IDENTITY_FACTS").length],["Adquirir fuente",all.filter((x:any)=>x.research_route==="ACQUIRE_EXTERNAL_IDENTITY_SOURCE").length],["Disposición vigente",all.filter((x:any)=>x.disposition_status==="CURRENT").length]].map(x=>`<div class="metric"><span>${esc(x[0])}</span><strong>${esc(x[1])}</strong></div>`).join("");
  const classOptions=["ALL",...CLASSES].filter((x,i,a)=>a.indexOf(x)===i).map(x=>`<option value="${esc(x)}" ${x===cls?"selected":""}>${esc(x)}</option>`).join("");
  const researchOptions=["ALL",...RESEARCH_ROUTES].filter((x,i,a)=>a.indexOf(x)===i).map(x=>`<option value="${esc(x)}" ${x===research?"selected":""}>${esc(x)}</option>`).join("");
  const filter=`<form class="filters" method="get"><select name="class">${classOptions}</select><select name="research">${researchOptions}</select><button class="primary">Aplicar</button></form>`;
  const trs=xs.map((x:any)=>`<tr><td>${researchRoutePill(x.research_route)}<div class="sub">rank ${esc(x.research_rank)}</div></td><td>${routePill(x.operational_route)}<div class="sub">${esc(x.source_triage_class)}</div></td><td class="wrap"><strong>${esc(x.title)}</strong><div class="sub">Lote ${esc(x.external_lot_id)} · ${esc([x.city,x.seller].filter(Boolean).join(" · "))}</div></td><td>${esc(x.current_candidate_count)}<div class="sub">estructurados ${esc(x.structured_discriminator_count)}</div></td><td><strong>P ${esc(x.identity_primary_count)} · S ${esc(x.identity_secondary_count)} · C ${esc(x.condition_identity_potential_count)}</strong><div class="sub">admin ${esc(x.administrative_generic_count)} · otros ${esc(x.other_registered_count)} · total ${esc(x.attachment_count)}</div><div class="sub">primera: ${esc(x.first_review_source_name||"—")} · ${esc(x.first_review_source_role||"—")}</div></td><td>${dispositionPill(x.disposition_status)}<div class="sub">${esc(x.current_disposition_action||"—")}</div></td><td class="wrap">${esc(x.research_reason)}</td><td><a class="btn primary" href="/functions/v1/superbid-fasecolda-source-dashboard/lots/${esc(x.external_lot_id)}">Inspeccionar fuentes</a></td></tr>`).join("");
  return html("SUPERBID — Source Research Priority",`<header class="top"><div><div class="ey">SUPERBID · v0.58</div><h1>Fasecolda Source Research Priority</h1></div>${nav}</header><main><div class="notice"><strong>${GUARDRAIL} · ${RESEARCH_GUARDRAIL} · ${HANDOFF_GUARDRAIL}.</strong> La cola muestra solo trabajo source-research accionable y ordena anexos por metadata. La fuente que una persona abra puede acompañarla al gate v0.52 como contexto visual, pero nunca se convierte automáticamente en evidencia, MATCH o candidato.</div><section class="metrics">${cards}</section><section class="panel"><div class="head"><div><h2>${xs.length} casos visibles</h2><span class="sub">Rank 10–40: existe una fuente registrada para inspección humana; rank 80: se necesita adquirir o registrar una fuente externa de identidad.</span></div>${filter}</div><div class="tablewrap"><table><thead><tr><th>Prioridad research</th><th>Ruta operativa</th><th>Lote</th><th>Candidatos</th><th>Inventario metadata</th><th>Disposición</th><th>Razón</th><th>Acción</th></tr></thead><tbody>${trs||'<tr><td colspan="8">Sin casos accionables para estos filtros.</td></tr>'}</tbody></table></div></section></main>`);
}

async function detail(req:Request,lot:string){
  const u=new URL(req.url);
  const x=await one(`/rest/v1/dashboard_fasecolda_source_research_priority_v57?select=*&external_lot_id=eq.${encodeURIComponent(lot)}&order=lot_id.desc&limit=1`);
  if(!x)return html("No encontrado",`<main><div class="notice bad">No existe caso source-research para ${esc(lot)}.</div><a class="btn" href="/functions/v1/superbid-fasecolda-source-dashboard">Volver</a></main>`,404);
  const [candidates,history]=await Promise.all([
    rows(`/rest/v1/lot_fasecolda_candidates?select=${encodeURIComponent("code,model_year,description,score,rank_no,current_value_cop,evaluated_at")}&lot_id=eq.${encodeURIComponent(x.lot_id)}&order=rank_no.asc`),
    rows(`/rest/v1/lot_fasecolda_candidate_source_disposition_history?select=${encodeURIComponent("action,source_triage_class,evidence_fingerprint,note,created_at")}&lot_id=eq.${encodeURIComponent(x.lot_id)}&order=created_at.desc&limit=25`),
  ]);
  const inventory=objArr(x.source_inventory),seen=new Set<string>();
  const publicUrl=safeHttpUrl(x.auction_url);if(publicUrl)seen.add(publicUrl);
  for(const s of inventory){const url=safeHttpUrl(s.url);if(url)seen.add(url);}
  const requested=safeHttpUrl(u.searchParams.get("source")),firstReview=safeHttpUrl(x.first_review_source_url),selected=requested&&seen.has(requested)?requested:firstReview&&seen.has(firstReview)?firstReview:"";
  const publicCard=publicUrl?`<div class="source-card"><div class="actions"><span class="pill info">PUBLIC_LOT_CONTEXT</span></div><strong>Página pública del lote</strong><div class="sub">${esc(publicUrl)}</div><div class="actions"><a class="btn" href="/functions/v1/superbid-fasecolda-source-dashboard/lots/${esc(lot)}?source=${encodeURIComponent(publicUrl)}">Ver aquí</a><a class="btn" target="_blank" rel="noopener noreferrer" href="${esc(publicUrl)}">Abrir aparte</a></div></div>`:"";
  const sourceCards=inventory.map((s:any)=>{const url=safeHttpUrl(s.url);if(!url)return"";const first=url===firstReview;return `<div class="source-card ${first?"first":""}"><div class="actions">${sourceRolePill(s.metadata_role)}${first?'<span class="pill info">PRIMERA POR METADATA</span>':""}</div><strong>${esc(s.name||`${s.kind||"ANEXO"} ${s.id||""}`)}</strong><div class="sub">${esc(s.kind||"—")} · ${esc(s.source||"—")} · rank ${esc(s.metadata_rank||"—")}</div><div class="sub">${esc(url)}</div><div class="actions"><a class="btn" href="/functions/v1/superbid-fasecolda-source-dashboard/lots/${esc(lot)}?source=${encodeURIComponent(url)}">Ver aquí</a><a class="btn" target="_blank" rel="noopener noreferrer" href="${esc(url)}">Abrir aparte</a></div></div>`;}).join("");
  const viewer=selected?(/\.pdf(?:$|\?)/i.test(selected)?`<iframe class="viewer" src="${esc(selected)}" title="Fuente registrada"></iframe>`:`<div class="notice"><strong>Fuente seleccionada para inspección humana.</strong><div class="sub">${esc(selected)}</div><a class="btn" target="_blank" rel="noopener noreferrer" href="${esc(selected)}">Abrir fuente</a></div>`):'<div class="notice">No hay un anexo priorizado para mostrar. La página pública puede revisarse como contexto, pero el caso puede requerir adquirir una fuente externa de identidad.</div>';
  const target=String(x.title_unique_target_code||"");
  const candidateCards=candidates.map((c:any)=>`<article class="candidate ${String(c.code)===target?"target":""}"><div class="sub">Rank ${esc(c.rank_no)} · score ${esc(c.score??"—")}</div><h3>${esc(c.code)}</h3><p>${esc(c.description)}</p><strong>${cop(c.current_value_cop)}</strong>${String(c.code)===target?'<p><span class="pill info">TARGET LITERAL DEL TÍTULO · SOLO PROXY READ-ONLY</span></p>':""}</article>`).join("");
  const current=x.disposition_status==="CURRENT";
  const actionOptions=[...(Number(x.current_candidate_count)>=2?["ROUTE_TO_EVIDENCE_REVIEW"]:[]),"CONFIRM_CURRENT_SOURCES_INSUFFICIENT","REQUEST_SOURCE_RESEARCH","REFER_IDENTITY_REVIEW","REQUEST_MATCHER_RECHECK"].map(a=>`<option value="${a}">${a}</option>`).join("");
  const dispositionForm=`<form class="form" method="post" action="/functions/v1/superbid-fasecolda-source-dashboard/lots/${esc(lot)}/disposition">${selected?`<input type="hidden" name="source" value="${esc(selected)}">`:""}<label><span>Disposición operativa</span><select name="action" required>${actionOptions}</select></label><label><span>Fundamento humano (mín. 10; insuficiencia mín. 20)</span><textarea name="note" minlength="10" maxlength="2000" required placeholder="Qué fuente revisó, qué discriminador falta o por qué debe cambiar la ruta."></textarea></label><button class="primary">Registrar disposición</button></form>${current?`<form method="post" action="/functions/v1/superbid-fasecolda-source-dashboard/lots/${esc(lot)}/disposition" style="margin-top:8px"><input type="hidden" name="action" value="CLEAR"><button class="danger">CLEAR disposición vigente</button></form>`:""}`;
  const historyRows=history.map((h:any)=>`<tr><td>${dt(h.created_at)}</td><td>${esc(h.action)}</td><td>${esc(h.source_triage_class)}</td><td>${esc(String(h.evidence_fingerprint||"").slice(0,10))}…</td><td class="wrap">${esc(h.note||"—")}</td></tr>`).join("");
  const flash=u.searchParams.get("saved")?'<div class="notice ok">Disposición registrada. No se modificó match, evidencia v0.52 ni valoración.</div>':u.searchParams.get("cleared")?'<div class="notice ok">Disposición retirada; el caso vuelve a la ruta calculada por su fingerprint actual.</div>':u.searchParams.get("error")?`<div class="notice bad">${esc(u.searchParams.get("error"))}</div>`:"";
  const evidenceCta=x.operational_route==="EVIDENCE_REVIEW"?`<a class="btn primary" href="/functions/v1/superbid-fasecolda-candidate-cockpit/lots/${esc(lot)}${selected?`?source=${encodeURIComponent(selected)}`:""}">Abrir gate de evidencia v0.52</a>`:"";
  return html(`SUPERBID — Source Research ${lot}`,`<header class="top"><div><div class="ey">SUPERBID · v0.58</div><h1>Source Research · ${esc(lot)}</h1></div>${nav}</header><main>${flash}<div class="notice"><strong>${GUARDRAIL} · ${RESEARCH_GUARDRAIL} · ${HANDOFF_GUARDRAIL}.</strong> ${esc(x.research_reason)} La fuente seleccionada puede acompañar la navegación al cockpit, pero su metadata y su apertura no crean evidencia ni preseleccionan candidato.</div><section class="metrics"><div class="metric"><span>Prioridad research</span><strong style="font-size:12px">${esc(x.research_route)}</strong></div><div class="metric"><span>Ruta operativa</span><strong style="font-size:12px">${esc(x.operational_route)}</strong></div><div class="metric"><span>Identidad P/S</span><strong>${esc(x.identity_primary_count)}/${esc(x.identity_secondary_count)}</strong></div><div class="metric"><span>Peritaje potencial</span><strong>${esc(x.condition_identity_potential_count)}</strong></div><div class="metric"><span>Admin / otros</span><strong>${esc(x.administrative_generic_count)}/${esc(x.other_registered_count)}</strong></div><div class="metric"><span>Accionable</span><strong style="font-size:13px">${x.source_research_actionable?"SÍ":"NO"}</strong></div></section><section class="panel"><div class="head"><div><h2>${esc(x.title)}</h2><span class="sub">${esc([x.brand,x.line,x.model_year,x.city,x.seller].filter(Boolean).join(" · "))}</span></div><div class="actions">${evidenceCta}<a class="btn" href="/functions/v1/superbid-fasecolda-workbench?lot=${esc(lot)}">Workbench</a></div></div><div class="section"><div class="chips">${researchRoutePill(x.research_route)}<span class="pill info">estructurados: ${esc(arr(x.structured_discriminators).join(", ")||"ninguno")}</span><span class="pill info">título único: ${esc(arr(x.unique_title_discriminators).join(", ")||"ninguno")}</span><span class="pill ${Number(x.duplicate_description_group_count)>0?"stale":"none"}">grupos descripción duplicada: ${esc(x.duplicate_description_group_count)}</span><span class="pill none">fingerprint ${esc(String(x.evidence_fingerprint).slice(0,12))}…</span></div><p class="sub">Primera fuente por metadata: ${esc(x.first_review_source_name||"—")} · ${esc(x.first_review_source_role||"—")}. Target literal: ${esc(x.title_unique_target_code||"—")}; sigue siendo solo proxy read-only.</p></div></section><section class="panel" style="margin-top:14px"><div class="head"><div><h2>Candidatos actuales</h2><span class="sub">Comparación read-only. El score fuzzy y la prioridad de fuentes no son evidencia.</span></div></div><div class="section candidate-grid">${candidateCards}</div></section><div class="two" style="margin-top:14px"><section class="panel"><div class="head"><div><h2>Inventario priorizado</h2><span class="sub">Ordenado solo por kind/nombre registrado. No se ha leído el contenido.</span></div></div><div class="section source-list">${publicCard}${sourceCards||'<p>Sin anexos registrados.</p>'}</div></section><section class="panel"><div class="head"><div><h2>Inspección humana</h2><span class="sub">Sin OCR, extracción ni diagnóstico automático. La selección inicial es navegación, no conclusión.</span></div></div><div class="section">${viewer}</div></section></div><section class="panel" style="margin-top:14px"><div class="head"><div><h2>Disposición humana</h2><span class="sub">Estado actual: ${esc(x.disposition_status)} · ${esc(x.current_disposition_action||"sin disposición")}</span></div></div><div class="section">${dispositionForm}</div></section><section class="panel history"><div class="head"><div><h2>Histórico de disposiciones</h2><span class="sub">Append-only; el fingerprint evita reutilizar decisiones sobre evidencia cambiada.</span></div></div><div class="tablewrap"><table><thead><tr><th>Fecha</th><th>Acción</th><th>Clase</th><th>Fingerprint</th><th>Nota</th></tr></thead><tbody>${historyRows||'<tr><td colspan="5">Sin histórico.</td></tr>'}</tbody></table></div></section></main>`);
}

async function setDisposition(req:Request,lot:string){
  const f=await req.formData(),action=String(f.get("action")||"").trim().toUpperCase(),note=String(f.get("note")||"").trim();
  const source=action==="ROUTE_TO_EVIDENCE_REVIEW"?await allowedSourceForLot(lot,f.get("source")):"";
  const sourceQuery=source?`?source=${encodeURIComponent(source)}`:"";
  const r=await db("/rest/v1/rpc/dashboard_set_fasecolda_candidate_source_disposition_v56",{method:"POST",body:JSON.stringify({p_external_lot_id:lot,p_action:action,p_note:note||null})});
  if(!r.ok){let msg=`No fue posible registrar disposición (${r.status}).`;try{const j=await r.json();msg=String(j.message||j.hint||msg);}catch{}return redirect(`/functions/v1/superbid-fasecolda-source-dashboard/lots/${encodeURIComponent(lot)}${sourceQuery?`${sourceQuery}&`:'?'}error=${encodeURIComponent(msg)}`);}
  if(action==="ROUTE_TO_EVIDENCE_REVIEW")return redirect(`/functions/v1/superbid-fasecolda-candidate-cockpit/lots/${encodeURIComponent(lot)}${sourceQuery}`);
  if(action==="CLEAR")return redirect(`/functions/v1/superbid-fasecolda-source-dashboard/lots/${encodeURIComponent(lot)}?cleared=1`);
  return redirect(`/functions/v1/superbid-fasecolda-source-dashboard/lots/${encodeURIComponent(lot)}?saved=1`);
}

Deno.serve(async(req:Request)=>{
  try{
    const p=pathOf(req),u=new URL(req.url),requestedLot=lotFromPath(p)||safeLot(u.searchParams.get("lot")),requestedSource=safeHttpUrl(u.searchParams.get("source"));
    if(p==="/login"&&req.method==="POST"){
      const f=await req.formData(),password=String(f.get("password")||""),lot=safeLot(f.get("lot")),source=safeHttpUrl(f.get("source"));
      if(!await valid(password))return login(true,lot,source);
      const target=lot?`/functions/v1/superbid-fasecolda-source-dashboard/lots/${encodeURIComponent(lot)}${source?`?source=${encodeURIComponent(source)}`:""}`:"/functions/v1/superbid-fasecolda-source-dashboard";
      return redirect(target,{"set-cookie":`${COOKIE}=${encodeURIComponent(password)}; Path=/functions/v1/superbid-fasecolda-source-dashboard; HttpOnly; Secure; SameSite=Strict; Max-Age=28800`});
    }
    const token=cookie(req);if(!await valid(token))return login(false,requestedLot,requestedSource);
    if(p==="/logout"&&req.method==="POST")return redirect("/functions/v1/superbid-fasecolda-source-dashboard",{"set-cookie":`${COOKIE}=; Path=/functions/v1/superbid-fasecolda-source-dashboard; HttpOnly; Secure; SameSite=Strict; Max-Age=0`});
    const lot=lotFromPath(p);
    if(lot&&p.endsWith("/disposition")&&req.method==="POST")return setDisposition(req,lot);
    if(lot&&req.method==="GET")return detail(req,lot);
    if((p==="/"||p==="")&&req.method==="GET")return board(req);
    return html("No encontrado","<main>Ruta no encontrada.</main>",404);
  }catch(e){return html("Error",`<main><div class="notice bad">Error interno. ${esc(e instanceof Error?e.message:String(e))}</div></main>`,500);}
});
