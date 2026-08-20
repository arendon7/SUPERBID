from superbid_collector.probe_sanitize import public_query_values, public_endpoint_recipe


def test_public_query_values_allow_only_non_sensitive_route_params():
    url = (
        "https://offer-query.superbid.net/seo/offers/?"
        "portalId=7&locale=es-CO&requestOrigin=MARKETPLACE&timeZoneId=America%2FBogota&"
        "urlSeo=mazda-3-mod-2017-4972833&filter=opaque-secret-like-value&token=nope"
    )
    values = public_query_values(url)
    assert values == {
        "portalId": "7",
        "locale": "es-CO",
        "requestOrigin": "MARKETPLACE",
        "timeZoneId": "America/Bogota",
        "urlSeo": "mazda-3-mod-2017-4972833",
    }
    assert "filter" not in values
    assert "token" not in values


def test_public_endpoint_recipe_drops_opaque_filter():
    recipe = public_endpoint_recipe(
        "https://offer-query.superbid.net/seo/offers/?portalId=10&urlSeo=abc-1234567&filter=opaque"
    )
    assert recipe["host"] == "offer-query.superbid.net"
    assert recipe["path"] == "/seo/offers/"
    assert recipe["params"] == {"portalId": "10", "urlSeo": "abc-1234567"}
