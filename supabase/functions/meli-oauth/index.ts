import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

function clean(s: string) { return s.replace(/[<>&\"']/g, ""); }
function html(title: string, body: string, status = 200) {
  return new Response(`<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${clean(title)}</title><style>body{font-family:system-ui,-apple-system,sans-serif;background:#f4f6f3;color:#182018;margin:0;padding:48px}.card{max-width:620px;margin:auto;background:#fff;border:1px solid #dfe5de;border-radius:16px;padding:28px;box-shadow:0 10px 32px rgba(0,0,0,.06)}h1{font-size:24px;margin-top:0}p{line-height:1.6;color:#526052}.ok{color:#17633c}.bad{color:#8b2d2d}</style></head><body><div class="card"><h1>${clean(title)}</h1>${body}</div></body></html>`, { status, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
}

Deno.serve(async (req) => {
  if (req.method !== "GET") return new Response("Method not allowed", { status: 405, headers: { allow: "GET" } });
  const url = new URL(req.url);
  const code = url.searchParams.get("code") ?? "";
  const state = url.searchParams.get("state") ?? "";
  const error = url.searchParams.get("error");

  if (error) return html("Autorización no completada", `<p class="bad">Mercado Libre devolvió: <strong>${clean(error)}</strong>.</p><p>La conexión sigue deshabilitada y no se almacenó ningún token.</p>`, 400);
  if (!code || !state || code.length > 4096 || state.length > 512) return html("Callback inválido", '<p class="bad">Faltan parámetros válidos de autorización.</p>', 400);
  if (!SUPABASE_URL || !SERVICE_ROLE) return html("Configuración incompleta", '<p class="bad">El callback no tiene credenciales internas del proyecto.</p>', 503);

  const r = await fetch(`${SUPABASE_URL}/rest/v1/rpc/meli_exchange_authorization_code`, {
    method: "POST",
    headers: { apikey: SERVICE_ROLE, authorization: `Bearer ${SERVICE_ROLE}`, "content-type": "application/json", "cache-control": "no-store" },
    body: JSON.stringify({ p_code: code, p_state: state })
  });
  let payload: any = null;
  try { payload = await r.json(); } catch { payload = null; }
  if (!r.ok || !payload?.ok) {
    const status = clean(String(payload?.status ?? `HTTP_${r.status}`));
    return html("No se pudo completar la conexión", `<p class="bad">Estado: <strong>${status}</strong>.</p><p>El código OAuth no se reutilizará. Puede iniciar una autorización nueva desde SUPERBID.</p>`, 400);
  }
  return html("Mercado Libre conectado", '<p class="ok"><strong>Conexión autorizada correctamente.</strong></p><p>Los tokens quedaron almacenados cifrados en Supabase Vault. Puede cerrar esta ventana y volver a SUPERBID.</p>');
});
