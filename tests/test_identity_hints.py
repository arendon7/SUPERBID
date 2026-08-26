from superbid_collector.identity_hints import (
    ENGINE_CC_NOMINAL_TOLERANCE,
    IDENTITY_HINT_GUARDRAIL,
    compare_vehicle_identity_hints,
    extract_vehicle_identity_hints,
)


def test_identity_hint_guardrail_is_explicit():
    assert IDENTITY_HINT_GUARDRAIL == "AUTOMATED_IDENTITY_HINT_NOT_HUMAN_EVIDENCE_OR_MATCH"
    assert ENGINE_CC_NOMINAL_TOLERANCE == 50


def test_extracts_literal_engine_transmission_drivetrain_and_fuel():
    hints = extract_vehicle_identity_hints("RENAULT DUSTER 2000 CC MT 4X4 GASOLINA")
    assert hints.engine_cc == 2000
    assert hints.transmission == "MANUAL"
    assert hints.drivetrain == "4X4_AWD"
    assert hints.fuel == "GASOLINE"


def test_normalizes_automatic_and_awd_synonyms_without_claiming_exact_gearbox_subtype():
    for text in ("CVT", "DCT", "DSG", "AT", "TP", "AUTOMÁTICA"):
        assert extract_vehicle_identity_hints(text).transmission == "AUTOMATIC"
    for text in ("AWD", "4WD", "4 x 4"):
        assert extract_vehicle_identity_hints(text).drivetrain == "4X4_AWD"


def test_hybrid_and_electric_propulsion_are_not_downgraded_to_gasoline():
    assert extract_vehicle_identity_hints("HÍBRIDO GASOLINA").fuel == "HYBRID"
    assert extract_vehicle_identity_hints("PHEV GASOLINA").fuel == "HYBRID"
    assert extract_vehicle_identity_hints("ELÉCTRICO BEV").fuel == "ELECTRIC"


def test_ambiguous_multiple_literal_values_fail_closed_to_unknown():
    assert extract_vehicle_identity_hints("1000 CC / 1600 CC").engine_cc is None
    assert extract_vehicle_identity_hints("MT AT").transmission is None
    assert extract_vehicle_identity_hints("4X2 4X4").drivetrain is None
    assert extract_vehicle_identity_hints("DIESEL GASOLINA").fuel is None


def test_comparison_is_descriptive_not_a_candidate_score():
    comparison = compare_vehicle_identity_hints(
        "RENAULT SANDERO 2000 CC MT",
        "RENAULT SANDERO RS MT 2000CC",
    )
    assert comparison["engine_cc"] == {"lot": 2000, "candidate": 2000, "status": "CONSISTENT"}
    assert comparison["transmission"] == {"lot": "MANUAL", "candidate": "MANUAL", "status": "CONSISTENT"}
    assert comparison["drivetrain"]["status"] == "LOT_UNKNOWN"
    assert comparison["fuel"]["status"] == "LOT_UNKNOWN"
    assert "score" not in comparison


def test_nominal_engine_displacement_is_compatible_but_not_exactly_equal():
    for lot_cc, candidate_cc in ((1598, 1600), (2999, 3000), (5193, 5200), (1451, 1500)):
        comparison = compare_vehicle_identity_hints(f"{lot_cc} CC", f"{candidate_cc}CC")
        assert comparison["engine_cc"]["status"] == "NOMINAL_COMPATIBLE"
    assert compare_vehicle_identity_hints("1450 CC", "1501CC")["engine_cc"]["status"] == "DIFFERS"


def test_difference_and_missing_candidate_hint_remain_explicit():
    differs = compare_vehicle_identity_hints("2000 CC MT", "1600 CC AT")
    assert differs["engine_cc"]["status"] == "DIFFERS"
    assert differs["transmission"]["status"] == "DIFFERS"

    missing = compare_vehicle_identity_hints("2000 CC", "RENAULT SANDERO")
    assert missing["engine_cc"]["status"] == "CANDIDATE_UNKNOWN"
