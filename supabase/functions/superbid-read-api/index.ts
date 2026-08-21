import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
});

async function db(path: string, init: RequestInit = {}) {
  return fetch(`${SUPABASE_URL}${path}`, {
    ...init,
    headers: {
      apikey: SERVICE_ROLE,
      authorization: `Bearer ${SERVICE_ROLE}`,
      "content-type": "application/json",
      ...(init.headers || {})
    }
  });
}

async function authorized(req: Request) {
  const auth = req.headers.get("authorization") || "";
  const token = auth.toLowerCase().startsWith("bearer ") ? auth.slice(7).trim() : (req.headers.get("x-superbid-read-key") || "").trim();
  if (!token || token.length > 256) return false;
  const r = await db("/rest/v1/rpc/dashboard_token_valid", { method: "POST", body: JSON.stringify({ p_token: token }) });
  if (!r.ok) return false;
  return (await r.json()) === true;
}

function safeInt(value: string | null, fallback: number, max: number) {
  const n = Number.parseInt(value || "", 10);
  return Number.isFinite(n) ? Math.max(1, Math.min(max, n)) : fallback;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: { allow: "GET,OPTIONS" } });
  if (req.method !== "GET") return json({ error: "method_not_allowed" }, 405);
  if (!await authorized(req)) return json({ error: "unauthorized" }, 401);

  const u = new URL(req.url);
  const marker = "/superbid-read-api";
  const i = u.pathname.indexOf(marker);
  const path = i >= 0 ? u.pathname.slice(i + marker.length) || "/" : u.pathname;

  if (path === "/health") return json({ ok: true, service: "superbid-read-api" });

  if (path === "/summary") {
    const r = await db("/rest/v1/rpc/dashboard_summary", { method: "POST", body: "{}" });
    return new Response(await r.text(), { status: r.status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
  }

  if (path === "/review-queue") {
    const limit = safeInt(u.searchParams.get("limit"), 100, 500);
    const state = (u.searchParams.get("state") || "").toUpperCase();
    const allowed = new Set(["REVIEW_NOW","REVIEW_SOON","WATCH","NO_HEADROOM","BLOCKED_VALUATION","CLOSED_OR_PAST"]);
    const select = "external_lot_id,title,brand,line,model_year,city,seller,url,current_bid_cop,bid_count,closes_at,outcome,commission_percent_public,fasecolda_status,fasecolda_current_cop,fasecolda_12m_ago_cop,fasecolda_change_12m_pct,preliminary_headroom_before_fixed_costs_cop,peritaje_count,peritajes,review_score,review_state,review_reasons,market_status,market_comparable_count_live,market_quick_sale_cop,max_bid_market_validated_cop,expected_profit_current_cop,expected_roi_current_pct,market_final_buy_recommendation_available,final_decision";
    let q = `/rest/v1/dashboard_lot_current?select=${encodeURIComponent(select)}&order=review_score.desc,closes_at.asc&limit=${limit}`;
    if (allowed.has(state)) q += `&review_state=eq.${encodeURIComponent(state)}`;
    const r = await db(q);
    return new Response(await r.text(), { status: r.status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
  }

  if (path.startsWith("/lots/")) {
    const id = path.slice("/lots/".length).trim();
    if (!/^\d{5,12}$/.test(id)) return json({ error: "invalid_lot_id" }, 400);
    const r = await db(`/rest/v1/dashboard_lot_current?select=*&external_lot_id=eq.${encodeURIComponent(id)}&limit=1`);
    if (!r.ok) return new Response(await r.text(), { status: r.status, headers: { "content-type": "application/json" } });
    const rows = await r.json();
    return rows.length ? json(rows[0]) : json({ error: "not_found" }, 404);
  }

  if (path === "/history") {
    const limit = safeInt(u.searchParams.get("limit"), 200, 1000);
    const select = "external_lot_id,title,brand,line,model_year,city,seller,url,initial_bid_cop,current_bid_cop,bid_count,bid_observed_at,closes_at,outcome,fasecolda_status,fasecolda_current_cop,peritaje_count";
    const r = await db(`/rest/v1/dashboard_lot_current?select=${encodeURIComponent(select)}&order=bid_observed_at.desc&limit=${limit}`);
    return new Response(await r.text(), { status: r.status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
  }

  return json({ error: "not_found" }, 404);
});
