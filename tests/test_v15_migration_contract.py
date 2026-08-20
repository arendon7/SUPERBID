from pathlib import Path


MIGRATION = Path("supabase/migrations/20260820212105_supabase_worker_functions_v15.sql")
ACTIVATION = Path("supabase/migrations/20260820212220_activate_supabase_cron_worker_v15.sql")


def test_v15_migration_never_persists_hidden_reserve_or_bidder_identity():
    sql = MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()
    assert "reservedprice" not in lowered
    assert "winnerbid" not in lowered
    assert "bidder" not in lowered.replace("bidder identity storage", "")
    assert "seller, initial_bid_cop" in lowered
    assert "phone" not in lowered


def test_v15_operational_functions_are_not_public_rpc():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    for signature in (
        "superbid_upsert_offer(jsonb,text,boolean)",
        "superbid_discover_open_vehicles(integer,integer)",
        "superbid_refresh_due(integer)",
    ):
        assert f"revoke all on function public.{signature} from public, anon, authenticated" in sql


def test_v15_cron_contract():
    sql = ACTIVATION.read_text(encoding="utf-8")
    assert "superbid-discovery-v15" in sql
    assert "*/15 * * * *" in sql
    assert "superbid-refresh-v15" in sql
    assert "* * * * *" in sql
    assert "superbid_refresh_due(40)" in sql
