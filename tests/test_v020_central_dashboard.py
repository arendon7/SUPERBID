from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIG = (ROOT / "supabase/migrations/20260821044355_central_read_api_v20.sql").read_text(encoding="utf-8").lower()
API = (ROOT / "supabase/functions/superbid-read-api/index.ts").read_text(encoding="utf-8").lower()
DASH = (ROOT / "supabase/functions/superbid-dashboard/index.ts").read_text(encoding="utf-8").lower()


def test_central_view_is_backend_only():
    assert "revoke all on public.dashboard_lot_current from public, anon, authenticated" in MIG
    assert "grant select on public.dashboard_lot_current to service_role" in MIG


def test_dashboard_token_secret_is_only_referenced_by_name():
    assert "superbid_dashboard_read_token" in MIG
    assert "vault.decrypted_secrets" in MIG
    assert "actual dashboard token is provisioned separately" in MIG


def test_read_api_requires_custom_authorization():
    # Guard semantics, not internal helper names/formatting.
    assert "dashboard_token_valid" in API
    assert "unauthorized" in API
    assert "401" in API
    assert "supabase_service_role_key" in API
    guard_pos = API.index("unauthorized")
    first_route_pos = API.index('p==="/health"')
    assert guard_pos < first_route_pos
    assert "cache-control" in API and "no-store" in API


def test_dashboard_uses_secure_http_only_cookie():
    assert "httponly; secure; samesite=strict" in DASH
    assert 'type="password"' in DASH
    assert "dashboard_token_valid" in DASH


def test_dashboard_never_claims_review_now_is_buy():
    assert "review_now es prioridad de revisión, no recomendación de compra" in DASH
    assert "comprar" not in DASH


def test_dashboard_is_server_rendered_without_client_script():
    assert "<script" not in DASH
    assert "deno.serve" in DASH
