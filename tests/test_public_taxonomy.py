from superbid_collector.probe_sanitize import safe_public_taxonomy


def test_safe_public_taxonomy_keeps_only_public_category_fields():
    payload = {
        "count": 2,
        "fieldFilterCategoryId": 44,
        "fieldFilterProductTypeId": 55,
        "productsType": [
            {
                "id": 101,
                "description": "Vehículos",
                "count": 123,
                "token": "must-not-leak",
                "categories": [
                    {"id": 1001, "description": "Automóviles", "count": 80, "email": "nope@example.com"}
                ],
            }
        ],
        "opaqueInternal": "ignore-me",
    }
    safe = safe_public_taxonomy(payload)
    assert safe["count"] == 2
    assert safe["fieldFilterCategoryId"] == 44
    assert safe["fieldFilterProductTypeId"] == 55
    assert safe["productsType"][0]["description"] == "Vehículos"
    assert safe["productsType"][0]["categories"][0]["description"] == "Automóviles"
    assert "token" not in safe["productsType"][0]
    assert "email" not in safe["productsType"][0]["categories"][0]
    assert "opaqueInternal" not in safe
