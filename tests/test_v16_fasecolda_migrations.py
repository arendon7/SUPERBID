from pathlib import Path


CORE = Path("supabase/migrations/20260820214043_fasecolda_matching_core_v16.sql")
GUARD = Path("supabase/migrations/20260820222123_fasecolda_line_identity_guard_v16.sql")
ACTIVATE = Path("supabase/migrations/20260820222529_activate_fasecolda_matcher_v16.sql")


def test_core_keeps_fasecolda_reference_separate_from_sale_price():
    sql = CORE.read_text(encoding="utf-8").lower()
    assert "fasecolda_value_history" in sql
    assert "current_value_cop" in sql
    assert "sale_price_confirmed" not in sql
    assert "reservedprice" not in sql
    assert "winnerbid" not in sql


def test_line_identity_guard_blocks_cross_model_fuzzy_matches():
    sql = GUARD.read_text(encoding="utf-8").lower()
    assert "fasecolda_line_compatible" in sql
    assert "trg_fasecolda_candidate_identity_guard" in sql
    assert "return null" in sql
    assert "model1" in sql
    assert "actual_brand" in sql


def test_fasecolda_functions_are_not_public_rpc():
    sql = (CORE.read_text(encoding="utf-8") + "\n" + GUARD.read_text(encoding="utf-8") + "\n" + ACTIVATE.read_text(encoding="utf-8")).lower()
    for signature in (
        "fasecolda_match_lot(bigint,boolean)",
        "fasecolda_match_due(integer)",
        "fasecolda_line_compatible(text,text,text)",
        "enqueue_fasecolda_match()",
    ):
        assert signature in sql
    assert "from public,anon,authenticated" in sql


def test_fasecolda_cron_is_gentle_and_continuous():
    sql = ACTIVATE.read_text(encoding="utf-8")
    assert "fasecolda-match-v16" in sql
    assert "*/5 * * * *" in sql
    assert "fasecolda_match_due(6)" in sql


def test_matcher_preserves_ambiguity_states():
    sql = CORE.read_text(encoding="utf-8")
    assert "HIGH" in sql
    assert "MEDIUM" in sql
    assert "AMBIGUOUS" in sql
    assert "UNMATCHED" in sql
    assert "candidate_min_cop" in sql
    assert "candidate_median_cop" in sql
    assert "candidate_max_cop" in sql
