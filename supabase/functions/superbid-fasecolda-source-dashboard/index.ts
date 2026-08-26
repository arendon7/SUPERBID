import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const U = Deno.env.get("SUPABASE_URL")!;
const K = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const COOKIE = "sb_fasecolda_source_session";
const GUARDRAIL = "CANDIDATE_SOURCE_TRIAGE_NOT_EVIDENCE_MATCH_OR_VALUATION";

const CLASSES = new Set([
  "ALL",
  "SINGLE_CANDIDATE_LOW_CONFIDENCE",
  "TITLE_DISCRIMINATOR_AVAILABLE",
  "TITLE_PROXY_CONFLICT",
  "STRUCTURED_DIFFERENCE_SOURCE_UNRESOLVED",
  "TRIM_OR_EXTERNAL_SOURCE_REQUIRED",
]);
const ROUTES = new Set([
  "ALL","SOURCE_TRIAGE","EVIDENCE_REVIEW","SOURCE_INSUFFICIENT_ACKNOWLEDGED",
  "SOURCE_RESEARCH_REQUESTED","IDENTITY_REVIEW_REQUESTED","MATCHER_RECHECK_REQUESTED",
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
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--t);font:14px/1.45 Inter,system-ui,sans-serif}a{text-decoration:none;color:inherit}.top{background:var(--g);color:#fff;padding:18px 26px;display:flex;justify-content:space-between;gap:12px;align-items:center}.ey{font-size:10px;letter-spacing:1.3px;font-weight:800;opacity:.72}.top h1{margin:2px 0}main{max-width:1850px;margin:auto;padding:20px 26px 45px}.nav,.filters,.actions,.chips{display:flex;gap:7px;flex-wrap:wrap;align-items:center}.btn,button,input,select,textarea{border:1px solid var(--l);border-radius:8px;padding:8px 10px;background:#fff;font:inherit}.btn,button{cursor:pointer;font-weight:750}.primary{background:var(--g2)!important;color:#fff!important;border-color:var(--g2)!important}.danger{color:var(--r)!important;border-color:#d8aaaa!important;background:#fff7f7!important}.notice{padding:12px 14px;border:1px solid #ead99c;background:#fff3cf;color:#65490d;border-radius:10px;margin-bottom:14px}.ok{background:#e1f2e6;border-color:#b8dbc3;color:#175935}.bad{background:#f4e5e5;border-color:#dfbbbb;color:var(--r)}.panel,.metric{background:#fff;border:1px solid var(--l);border-radius:13px}.metrics{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:14px}.metric{padding:14px}.metric span,.sub,label span{display:block;color:var(--m);font-size:11px}.metric strong{font-size:21px}.head{padding:15px 17px;border-bottom:1px solid var(--l);display:flex;justify-content:space-between;gap:10px;align-items:center}.head h2{margin:0}.section{padding:16px}.tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:1450px}th,td{padding:9px 10px;border-bottom:1px solid #edf0ec;text-align:left;vertical-align:top;white-space:nowrap}th{font-size:10px;text-transform:uppercase;color:var(--m);background:#fafbf9}.wrap{white-space:normal;min-width:300px}.pill{font-size:10px;font-weight:800;border-radius:99px;padding:5px 8px;display:inline-block}.source{background:#fff0c9;color:#72510a}.evidence{background:#daf0e1;color:#175935}.stale{background:#f4dfdf;color:#7f2424}.info{background:#e8eef3;color:#425c70}.none{background:#ecefec;color:#586158}.two{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start}.candidate-grid{display:grid;grid-template-columns:repeat(3,minmax(280px,1fr));gap:10px}.candidate{padding:12px;border:1px solid var(--l);border-radius:10px;background:#fafbf9}.candidate.target{border:2px solid var(--b)}.candidate h3{margin:2px 0}.source-list{display:grid;gap:8px}.source-card{border:1px solid var(--l);padding:10px;border-radius:9px;background:#fafbf9;overflow-wrap:anywhere}.viewer{width:100%;height:720px;border:1px solid var(--l);border-radius:9px;background:#fff}.form textarea{width:100%;min-height:110px}.history{margin-top:14px}.login{width:min(440px,92vw);margin:15vh auto;background:#fff;border:1px solid var(--l);border-radius:16px;padding:28px}.login input,.login button{width:100%}.login button{margin-top:10px}.err{color:var(--r);font-weight:700}
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

function login(error=false,lot=""){
  return html("SUPERBID — Source Sufficiency",`<form class="login" method="post" action="/functions/v1/superbid-fasecolda-source-dashboard/login">${lot?`<input type="hidden" name="lot" value="${esc(lot)}">`:""}<div class="ey">SUPERBID · v0.56</div><h1>Candidate Source Sufficiency</h1><p class="sub">Acceso privado. Este tablero decide solo qué investigación humana sigue; no homologa un código ni produce valoración.</p>${lot?`<p class="sub">Continuar con lote ${esc(lot)} después de autenticar.</p>`:""}${error?'<p class="err">Credencial inválida.</p>':""}<input type="password" name="password" autocomplete="current-password" required placeholder="Clave de acceso"><button class="primary">Entrar</button></form>`,error?401:200);
}
const nav=`<nav class="nav"><a class="btn" href="/functions/v1/superbid-dashboard">Dashboard</a><a class="btn" href="/functions/v1/superbid-readiness-dashboard">Readiness</a><a class="btn" href="/functions/v1/superbid-fasecolda-workbench">Fasecolda</a><a class="btn" href="/functions/v1/superbid-fasecolda-candidate-cockpit">Evidencia candidatos</a><a class="btn" href="/functions/v1/superbid-fasecolda-search-dashboard">Búsqueda</a><form method="post" action="/functions/v1/superbid-fasecolda-source-dashboard/logout"><button>Salir</button></form></nav>`;

function routePill(v:unknown){const x=String(v||"SOURCE_TRIAGE"),c=x==="EVIDENCE_REVIEW"?"evidence":x==="SOURCE_TRIAGE"?"source":x.includes("INSUFFICIENT")?"none":"info";return `<span class="pill ${c}">${esc(x)}</span>`;}
function dispositionPill(v:unknown){const x=String(v||"NONE"),c=x==="CURRENT"?"evidence":x==="STALE"?"stale":"none";return `<span class="pill ${c}">${esc(x)}</span>`;}
function arr(v:unknown){return Array.isArray(v)?v.map(String):[];}

async function board(req:Request){
  const u=new URL(req.url),clsRaw=(u.searchParams.get("class")||"ALL").toUpperCase(),routeRaw=(u.searchParams.get("route")||"ALL").toUpperCase();
  const cls=CLASSES.has(clsRaw)?clsRaw:"ALL",route=ROUTES.has(routeRaw)?routeRaw:"ALL";
  const sel="external_lot_id,title,brand,line,model_year,city,seller,closes_at,automatic_status,automatic_best_code,automatic_best_score,automatic_second_score,current_candidate_count,structured_discriminator_count,structured_discriminators,unique_title_discriminator_count,unique_title_discriminators,title_unique_target_code,duplicate_description_group_count,attachment_count,peritaje_count,source_triage_class,evidence_fingerprint,disposition_status,current_disposition_action,operational_route,source_triage_reason";
  let q=`/rest/v1/dashboard_fasecolda_candidate_source_triage_v56?select=${encodeURIComponent(sel)}&order=closes_at.asc&limit=500`;
  if(cls!=="ALL")q+=`&source_triage_class=eq.${encodeURIComponent(cls)}`;
  if(route!=="ALL")q+=`&operational_route=eq.${encodeURIComponent(route)}`;
  const xs=await rows(q);
  const all=await rows(`/rest/v1/dashboard_fasecolda_candidate_source_triage_v56?select=${encodeURIComponent("external_lot_id,operational_route,peritaje_count,attachment_count,disposition_status,source_triage_class")}&limit=500`);
  const cards=[
    ["Casos",all.length],
    ["Triage fuente",all.filter((x:any)=>x.operational_route==="SOURCE_TRIAGE").length],
    ["A evidencia",all.filter((x:any)=>x.operational_route==="EVIDENCE_REVIEW").length],
    ["Con peritaje",all.filter((x:any)=>Number(x.peritaje_count)>0).length],
    ["Sin anexos",all.filter((x:any)=>Number(x.attachment_count)===0).length],
    ["Disposición vigente",all.filter((x:any)=>x.disposition_status==="CURRENT").length],
  ].map(x=>`<div class="metric"><span>${esc(x[0])}</span><strong>${esc(x[1])}</strong></div>`).join("");
  const classOptions=["ALL",...CLASSES].filter((x,i,a)=>a.indexOf(x)===i).map(x=>`<option value="${esc(x)}" ${x===cls?"selected":""}>${esc(x)}</option>`).join("");
  const routeOptions=["ALL",...ROUTES].filter((x,i,a)=>a.indexOf(x)===i).map(x=>`<option value="${esc(x)}" ${x===route?"selected":""}>${esc(x)}</option>`).join("");
  const filter=`<form class="filters" method="get"><select name="class">${classOptions}</select><select name="route">${routeOptions}</select><button class="primary">Aplicar</button></form>`;
  const trs=xs.map((x:any)=>`<tr><td>${routePill(x.operational_route)}<div class="sub">${esc(x.source_triage_class)}</div></td><td class="wrap"><strong>${esc(x.title)}</strong><div class="sub">Lote ${esc(x.external_lot_id)} · ${esc([x.city,x.seller].filter(Boolean).join(" · "))}</div></td><td>${esc(x.current_candidate_count)}</td><td>${esc(arr(x.structured_discriminators).join(", ")||"—")}<div class="sub">título único: ${esc(arr(x.unique_title_discriminators).join(", ")||"—")} · target ${esc(x.title_unique_target_code||"—")}</div></td><td>${esc(x.attachment_count)}<div class="sub">peritaje ${esc(x.peritaje_count)}</div></td><td>${dispositionPill(x.disposition_status)}<div class="sub">${esc(x.current_disposition_action||"—")}</div></td><td class="wrap">${esc(x.source_triage_reason)}</td><td><a class="btn primary" href="/functions/v1/superbid-fasecolda-source-dashboard/lots/${esc(x.external_lot_id)}">Revisar fuentes</a></td></tr>`).join("");
  return html("SUPERBID — Candidate Source Sufficiency",`<header class="top"><div><div class="ey">SUPERBID · v0.56</div><h1>Fasecolda Candidate Source Sufficiency</h1></div>${nav}</header><main><div class="notice"><strong>${GUARDRAIL}.</strong> Los clasificadores de título/candidatos solo priorizan investigación. No son evidencia, MATCH humano, homologación, recomendación ni señal de compra.</div><section class="metrics">${cards}</section><section class="panel"><div class="head"><div><h2>Cola de suficiencia de fuente</h2><span class="sub">Un fingerprint cambia si cambian identidad, matcher, candidatos o fuentes; cualquier disposición anterior queda STALE automáticamente.</span></div>${filter}</div><div class="tablewrap"><table><thead><tr><th>Ruta</th><th>Lote</th><th>Candidatos</th><th>Diferencias</th><th>Fuentes</th><th>Disposición</th><th>Razón</th><th>Acción</th></tr></thead><tbody>${trs||'<tr><td colspan="8">Sin casos.</td></tr>'}</tbody></table></div></section></main>`);
}

async function detail(req:Request,lot:string){
  const u=new URL(req.url);
  const x=await one(`/rest/v1/dashboard_fasecolda_candidate_source_triage_v56?select=*&external_lot_id=eq.${encodeURIComponent(lot)}&order=lot_id.desc&limit=1`);
  if(!x)return html("No encontrado",`<main><div class="notice bad">No existe caso source-triage vigente para ${esc(lot)}.</div><a class="btn" href="/functions/v1/superbid-fasecolda-source-dashboard">Volver</a></main>`,404);
  const [candidates,attachments,history]=await Promise.all([
    rows(`/rest/v1/lot_fasecolda_candidates?select=${encodeURIComponent("code,model_year,description,score,rank_no,current_value_cop,evaluated_at")}&lot_id=eq.${encodeURIComponent(x.lot_id)}&order=rank_no.asc`),
    rows(`/rest/v1/lot_attachments?select=${encodeURIComponent("id,name,url,kind,source,discovered_at")}&lot_id=eq.${encodeURIComponent(x.lot_id)}&order=kind.asc,id.asc`),
    rows(`/rest/v1/lot_fasecolda_candidate_source_disposition_history?select=${encodeURIComponent("action,source_triage_class,evidence_fingerprint,note,created_at")}&lot_id=eq.${encodeURIComponent(x.lot_id)}&order=created_at.desc&limit=25`),
  ]);
  const sources:{url:string;label:string}[]=[];const seen=new Set<string>();
  const add=(raw:unknown,label:string)=>{const url=safeHttpUrl(raw);if(url&&!seen.has(url)){seen.add(url);sources.push({url,label});}};
  add(x.auction_url,"Página pública del lote");
  for(const a of attachments)add(a.url,`${a.kind||"ANEXO"} · ${a.name||`archivo ${a.id}`}`);
  const requested=safeHttpUrl(u.searchParams.get("source"));
  const selected=requested&&seen.has(requested)?requested:"";
  const sourceCards=sources.map(s=>`<div class="source-card"><strong>${esc(s.label)}</strong><div class="sub">${esc(s.url)}</div><div class="actions"><a class="btn" href="/functions/v1/superbid-fasecolda-source-dashboard/lots/${esc(lot)}?source=${encodeURIComponent(s.url)}">Ver aquí</a><a class="btn" target="_blank" rel="noopener noreferrer" href="${esc(s.url)}">Abrir aparte</a></div></div>`).join("");
  const viewer=selected?(/\.pdf(?:$|\?)/i.test(selected)?`<iframe class="viewer" src="${esc(selected)}" title="Fuente PDF"></iframe>`:`<div class="notice"><strong>Fuente seleccionada.</strong><div class="sub">${esc(selected)}</div><a class="btn" target="_blank" rel="noopener noreferrer" href="${esc(selected)}">Abrir fuente</a></div>`):'<div class="notice">Seleccione una fuente registrada para inspeccionarla. Este tablero no extrae ni diagnostica automáticamente su contenido.</div>';
  const target=String(x.title_unique_target_code||"");
  const candidateCards=candidates.map((c:any)=>`<article class="candidate ${String(c.code)===target?"target":""}"><div class="sub">Rank ${esc(c.rank_no)} · score ${esc(c.score??"—")}</div><h3>${esc(c.code)}</h3><p>${esc(c.description)}</p><strong>${cop(c.current_value_cop)}</strong>${String(c.code)===target?'<p><span class="pill info">TARGET LITERAL DEL TÍTULO · SOLO PROXY READ-ONLY</span></p>':""}</article>`).join("");
  const current=x.disposition_status==="CURRENT";
  const actionOptions=[
    ...(Number(x.current_candidate_count)>=2?["ROUTE_TO_EVIDENCE_REVIEW"]:[]),
    "CONFIRM_CURRENT_SOURCES_INSUFFICIENT","REQUEST_SOURCE_RESEARCH","REFER_IDENTITY_REVIEW","REQUEST_MATCHER_RECHECK",
  ].map(a=>`<option value="${a}">${a}</option>`).join("");
  const dispositionForm=`<form class="form" method="post" action="/functions/v1/superbid-fasecolda-source-dashboard/lots/${esc(lot)}/disposition"><label><span>Disposición operativa</span><select name="action" required>${actionOptions}</select></label><label><span>Fundamento humano (mín. 10; insuficiencia mín. 20)</span><textarea name="note" minlength="10" maxlength="2000" required placeholder="Qué fuente revisó, qué discriminador falta o por qué debe cambiar la ruta."></textarea></label><button class="primary">Registrar disposición</button></form>${current?`<form method="post" action="/functions/v1/superbid-fasecolda-source-dashboard/lots/${esc(lot)}/disposition" style="margin-top:8px"><input type="hidden" name="action" value="CLEAR"><button class="danger">CLEAR disposición vigente</button></form>`:""}`;
  const historyRows=history.map((h:any)=>`<tr><td>${dt(h.created_at)}</td><td>${esc(h.action)}</td><td>${esc(h.source_triage_class)}</td><td>${esc(String(h.evidence_fingerprint||"").slice(0,10))}…</td><td class="wrap">${esc(h.note||"—")}</td></tr>`).join("");
  const flash=u.searchParams.get("saved")?'<div class="notice ok">Disposición registrada. No se modificó match, evidencia v0.52 ni valoración.</div>':u.searchParams.get("cleared")?'<div class="notice ok">Disposición retirada; el caso vuelve a la ruta calculada por su fingerprint actual.</div>':u.searchParams.get("error")?`<div class="notice bad">${esc(u.searchParams.get("error"))}</div>`:"";
  const evidenceCta=x.operational_route==="EVIDENCE_REVIEW"?`<a class="btn primary" href="/functions/v1/superbid-fasecolda-candidate-cockpit/lots/${esc(lot)}">Abrir gate de evidencia v0.52</a>`:"";
  return html(`SUPERBID — Fuentes ${lot}`,`<header class="top"><div><div class="ey">SUPERBID · v0.56</div><h1>Source Sufficiency · ${esc(lot)}</h1></div>${nav}</header><main>${flash}<div class="notice"><strong>${GUARDRAIL}.</strong> ${esc(x.source_triage_reason)} La ruta puede cambiar el trabajo siguiente, pero no la referencia Fasecolda efectiva.</div><section class="metrics"><div class="metric"><span>Clase</span><strong style="font-size:13px">${esc(x.source_triage_class)}</strong></div><div class="metric"><span>Ruta</span><strong style="font-size:13px">${esc(x.operational_route)}</strong></div><div class="metric"><span>Candidatos</span><strong>${esc(x.current_candidate_count)}</strong></div><div class="metric"><span>Discriminadores</span><strong>${esc(x.structured_discriminator_count)}</strong></div><div class="metric"><span>Anexos</span><strong>${esc(x.attachment_count)}</strong></div><div class="metric"><span>Peritajes</span><strong>${esc(x.peritaje_count)}</strong></div></section><section class="panel"><div class="head"><div><h2>${esc(x.title)}</h2><span class="sub">${esc([x.brand,x.line,x.model_year,x.city,x.seller].filter(Boolean).join(" · "))}</span></div><div class="actions">${evidenceCta}<a class="btn" href="/functions/v1/superbid-fasecolda-workbench?lot=${esc(lot)}">Workbench</a></div></div><div class="section"><div class="chips"><span class="pill info">estructurados: ${esc(arr(x.structured_discriminators).join(", ")||"ninguno")}</span><span class="pill info">título único: ${esc(arr(x.unique_title_discriminators).join(", ")||"ninguno")}</span><span class="pill ${Number(x.duplicate_description_group_count)>0?"stale":"none"}">grupos descripción duplicada: ${esc(x.duplicate_description_group_count)}</span><span class="pill none">fingerprint ${esc(String(x.evidence_fingerprint).slice(0,12))}…</span></div><p class="sub">Target literal: ${esc(x.title_unique_target_code||"—")}. Si existe, sigue siendo únicamente una pista determinista y no preselecciona candidato.</p></div></section><section class="panel" style="margin-top:14px"><div class="head"><div><h2>Candidatos actuales</h2><span class="sub">Comparación read-only. El score fuzzy no es evidencia.</span></div></div><div class="section candidate-grid">${candidateCards}</div></section><div class="two" style="margin-top:14px"><section class="panel"><div class="head"><div><h2>Fuentes permitidas</h2><span class="sub">Solo URL pública del lote y anexos ya registrados.</span></div></div><div class="section source-list">${sourceCards||'<p>Sin fuentes registradas.</p>'}</div></section><section class="panel"><div class="head"><div><h2>Inspección de fuente</h2><span class="sub">Sin OCR, extracción ni diagnóstico automático.</span></div></div><div class="section">${viewer}</div></section></div><section class="panel" style="margin-top:14px"><div class="head"><div><h2>Disposición humana</h2><span class="sub">Estado actual: ${esc(x.disposition_status)} · ${esc(x.current_disposition_action||"sin disposición")}</span></div></div><div class="section">${dispositionForm}</div></section><section class="panel history"><div class="head"><div><h2>Histórico de disposiciones</h2><span class="sub">Append-only; el fingerprint evita reutilizar decisiones sobre evidencia cambiada.</span></div></div><div class="tablewrap"><table><thead><tr><th>Fecha</th><th>Acción</th><th>Clase</th><th>Fingerprint</th><th>Nota</th></tr></thead><tbody>${historyRows||'<tr><td colspan="5">Sin histórico.</td></tr>'}</tbody></table></div></section></main>`);
}

async function setDisposition(req:Request,lot:string){
  const f=await req.formData(),action=String(f.get("action")||"").trim().toUpperCase(),note=String(f.get("note")||"").trim();
  const r=await db("/rest/v1/rpc/dashboard_set_fasecolda_candidate_source_disposition_v56",{method:"POST",body:JSON.stringify({p_external_lot_id:lot,p_action:action,p_note:note||null})});
  if(!r.ok){let msg=`No fue posible registrar disposición (${r.status}).`;try{const j=await r.json();msg=String(j.message||j.hint||msg);}catch{}return redirect(`/functions/v1/superbid-fasecolda-source-dashboard/lots/${encodeURIComponent(lot)}?error=${encodeURIComponent(msg)}`);}
  if(action==="ROUTE_TO_EVIDENCE_REVIEW")return redirect(`/functions/v1/superbid-fasecolda-candidate-cockpit/lots/${encodeURIComponent(lot)}`);
  if(action==="CLEAR")return redirect(`/functions/v1/superbid-fasecolda-source-dashboard/lots/${encodeURIComponent(lot)}?cleared=1`);
  return redirect(`/functions/v1/superbid-fasecolda-source-dashboard/lots/${encodeURIComponent(lot)}?saved=1`);
}

Deno.serve(async(req:Request)=>{
  try{
    const p=pathOf(req),u=new URL(req.url),requestedLot=lotFromPath(p)||safeLot(u.searchParams.get("lot"));
    if(p==="/login"&&req.method==="POST"){
      const f=await req.formData(),password=String(f.get("password")||""),lot=safeLot(f.get("lot"));
      if(!await valid(password))return login(true,lot);
      const target=lot?`/functions/v1/superbid-fasecolda-source-dashboard/lots/${encodeURIComponent(lot)}`:"/functions/v1/superbid-fasecolda-source-dashboard";
      return redirect(target,{"set-cookie":`${COOKIE}=${encodeURIComponent(password)}; Path=/functions/v1/superbid-fasecolda-source-dashboard; HttpOnly; Secure; SameSite=Strict; Max-Age=28800`});
    }
    const token=cookie(req);if(!await valid(token))return login(false,requestedLot);
    if(p==="/logout"&&req.method==="POST")return redirect("/functions/v1/superbid-fasecolda-source-dashboard",{"set-cookie":`${COOKIE}=; Path=/functions/v1/superbid-fasecolda-source-dashboard; HttpOnly; Secure; SameSite=Strict; Max-Age=0`});
    const lot=lotFromPath(p);
    if(lot&&p.endsWith("/disposition")&&req.method==="POST")return setDisposition(req,lot);
    if(lot&&req.method==="GET")return detail(req,lot);
    if((p==="/"||p==="")&&req.method==="GET")return board(req);
    return html("No encontrado","<main>Ruta no encontrada.</main>",404);
  }catch(e){return html("Error",`<main><div class="notice bad">Error interno. ${esc(e instanceof Error?e.message:String(e))}</div></main>`,500);}
});
