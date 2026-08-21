from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OAUTH = (ROOT / "supabase/migrations/20260820224253_mercadolibre_oauth_v18.sql").read_text(encoding="utf-8")
PIPE = (ROOT / "supabase/migrations/20260821042638_market_comparable_pipeline_v18.sql").read_text(encoding="utf-8")
FINAL = (ROOT / "supabase/migrations/20260821042913_market_validated_opportunity_v18.sql").read_text(encoding="utf-8")
GUARD = (ROOT / "supabase/migrations/20260821043520_market_queue_trigger_guard_v18.sql").read_text(encoding="utf-8")
EDGE = (ROOT / "supabase/functions/meli-oauth/index.ts").read_text(encoding="utf-8")


def test_oauth_uses_vault_pkce_and_one_time_state():
    low = OAUTH.lower()
    assert "vault.create_secret" in low
    assert "code_challenge_method=s256" in low
    assert "state_hash" in low
    assert "used_at is not null" in low
    assert "expires_at<clock_timestamp()" in low
    assert "meli_refresh_token" in low


def test_oauth_privileged_functions_are_not_public_rpc():
    low = OAUTH.lower()
    assert "revoke all on function" in low
    assert "from public,anon,authenticated" in low
    assert "grant execute" in low and "to service_role" in low


def test_market_pipeline_stops_before_search_when_auth_missing():
    low = PIPE.lower()
    auth_pos = low.index("if not found or c.status<>'ready'")
    request_pos = low.index("https://api.mercadolibre.com/sites/mco/search")
    assert auth_pos < request_pos
    assert "auth_required" in low


def test_market_comparables_require_year_and_line_identity():
    low = PIPE.lower()
    assert "v_year is distinct from l.model_year" in low
    assert "fasecolda_line_compatible" in low
    assert "v_score<0.30" in low


def test_market_pipeline_does_not_persist_sensitive_seller_identity():
    low = PIPE.lower()
    assert "seller,car_dealer" in low
    assert "seller,id" not in low
    assert "phone" not in low
    assert "email" not in low
    assert "reservedprice" not in low
    assert "winnerbid" not in low


def test_market_queue_only_requeues_on_real_identity_change():
    low = GUARD.lower()
    assert "new.title is not distinct from old.title" in low
    assert "new.model_year is not distinct from old.model_year" in low
    assert "v_status:=case when v_conn='ready' then 'pending' else 'auth_required' end" in low


def test_final_decision_requires_market_and_cost_review():
    low = FINAL.lower()
    assert "market_validation_available" in low
    assert "costs_complete" in low
    assert "cost_reviewed_at is not null" in low
    assert "market_final_buy_recommendation_available" in low
    assert "when not market_validation_available then 'market_validation_pending'" in low
    assert "when not costs_complete or cost_reviewed_at is null then 'configure_costs'" in low


def test_edge_callback_never_exposes_tokens():
    low = EDGE.lower()
    assert "meli_exchange_authorization_code" in low
    assert "cache-control" in low and "no-store" in low
    assert "access_token" not in low
    assert "refresh_token" not in low
