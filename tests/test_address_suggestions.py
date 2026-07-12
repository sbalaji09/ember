import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pytest
import address_suggestions


@pytest.fixture(autouse=True)
def clear_cache():
    address_suggestions._suggest_addresses_cached.cache_clear()


def _nominatim_item(house_number, road, city="Santa Rosa", importance=0.1, **overrides):
    address = {
        "house_number": house_number,
        "road": road,
        "city": city,
        "state": "California",
        "state_code": "CA",
        "postcode": "95401",
        "country_code": "us",
    }
    address.update(overrides.pop("address_overrides", {}))
    item = {
        "lat": overrides.pop("lat", "38.4405"),
        "lon": overrides.pop("lon", "-122.7144"),
        "importance": importance,
        "address": address,
    }
    item.update(overrides)
    return item


def test_suggest_addresses_filters_to_california_street_addresses_and_ranks(monkeypatch):
    payload = [
        _nominatim_item(None, "Main Street", importance=0.9),
        _nominatim_item("10", "Main Street", importance=0.2),
        _nominatim_item("20", "Main Street", importance=0.8, address_overrides={"state": "Nevada", "state_code": "NV"}),
        _nominatim_item("30", "Main Street", importance=0.7, lat="45.0"),
        _nominatim_item("40", "Main Street", importance=0.6, address_overrides={"neighbourhood": "Junior College"}),
    ]

    monkeypatch.setattr(address_suggestions, "_fetch_photon", lambda query, limit: [])
    monkeypatch.setattr(address_suggestions, "_fetch_nominatim", lambda query, limit: payload)

    suggestions = address_suggestions.suggest_addresses("main st", limit=6)

    assert [item["address"] for item in suggestions] == [
        "40 Main Street, Santa Rosa, CA 95401",
        "10 Main Street, Santa Rosa, CA 95401",
    ]
    assert suggestions[0]["rank"] == 1
    assert suggestions[0]["secondary"] == "Junior College"
    assert suggestions[0]["source"] == "OpenStreetMap Nominatim"
    assert "_match_score" not in suggestions[0]


def test_suggest_addresses_returns_matching_number_only_suggestions(monkeypatch):
    payload = [
        _nominatim_item(
            "11",
            "South Milpitas Boulevard",
            city="Milpitas",
            importance=0.9,
            address_overrides={"county": "Santa Clara County", "postcode": "95035"},
            lat="37.432",
            lon="-121.899",
        ),
        _nominatim_item(
            "1074",
            "Main Street",
            city="Santa Rosa",
            importance=0.2,
            address_overrides={"county": "Sonoma County"},
        ),
        _nominatim_item(
            "10740",
            "Foothill Boulevard",
            city="Rancho Cucamonga",
            importance=0.3,
            address_overrides={"county": "San Bernardino County", "postcode": "91730"},
            lat="34.106",
            lon="-117.571",
        ),
    ]

    queries = []

    def fake_fetch(query, limit):
        queries.append(query)
        return payload

    monkeypatch.setattr(address_suggestions, "_fetch_photon", lambda query, limit: [])
    monkeypatch.setattr(address_suggestions, "_fetch_nominatim", fake_fetch)

    suggestions = address_suggestions.suggest_addresses("1074", limit=6)

    assert [item["address"] for item in suggestions] == [
        "1074 Main Street, Santa Rosa, CA 95401",
        "10740 Foothill Boulevard, Rancho Cucamonga, CA 91730",
    ]
    assert queries[:3] == ["1074 california", "1074 ca", "1074"]


def test_suggest_addresses_requires_matching_house_number_when_typed(monkeypatch):
    payload = [
        _nominatim_item(
            "11",
            "South Milpitas Boulevard",
            city="Milpitas",
            importance=0.9,
            address_overrides={"county": "Santa Clara County", "postcode": "95035"},
            lat="37.432",
            lon="-121.899",
        ),
        _nominatim_item(
            "2430",
            "South Melrose Drive",
            city="Vista",
            importance=0.8,
            address_overrides={"county": "San Diego County", "postcode": "92081"},
            lat="33.20",
            lon="-117.24",
        ),
        _nominatim_item(
            "1074",
            "Main Street",
            city="Santa Rosa",
            importance=0.2,
            address_overrides={"county": "Sonoma County"},
        ),
    ]

    monkeypatch.setattr(address_suggestions, "_fetch_photon", lambda query, limit: [])
    monkeypatch.setattr(address_suggestions, "_fetch_nominatim", lambda query, limit: payload)

    suggestions = address_suggestions.suggest_addresses("1074 ma", limit=6)

    assert [item["address"] for item in suggestions] == ["1074 Main Street, Santa Rosa, CA 95401"]


def test_suggest_addresses_matches_partial_and_fuzzy_street_tokens(monkeypatch):
    photon_features = [
        {
            "properties": {
                "housenumber": "1074",
                "street": "Darrington Court",
                "city": "Sunnyvale",
                "county": "Santa Clara County",
                "state": "California",
                "countrycode": "US",
                "postcode": "94087",
            },
            "geometry": {"coordinates": [-122.0589, 37.3438]},
        },
        {
            "properties": {
                "housenumber": "1074",
                "street": "Davis Street",
                "city": "San Leandro",
                "county": "Alameda County",
                "state": "California",
                "countrycode": "US",
                "postcode": "94577",
            },
            "geometry": {"coordinates": [-122.16, 37.72]},
        },
    ]

    monkeypatch.setattr(address_suggestions, "_fetch_photon", lambda query, limit: photon_features)
    monkeypatch.setattr(address_suggestions, "_fetch_nominatim", lambda query, limit: [])

    suggestions = address_suggestions.suggest_addresses("1074 darringto corut", limit=6)

    assert [item["address"] for item in suggestions] == ["1074 Darrington Court, Sunnyvale, CA 94087"]


def test_suggest_addresses_returns_empty_for_short_queries(monkeypatch):
    def fake_fetch(*args, **kwargs):
        raise AssertionError("short queries should not call upstream providers")

    monkeypatch.setattr(address_suggestions, "_fetch_photon", fake_fetch)
    monkeypatch.setattr(address_suggestions, "_fetch_nominatim", fake_fetch)

    assert address_suggestions.suggest_addresses("ab") == []


def test_suggest_addresses_wraps_request_errors(monkeypatch):
    def fake_fetch(*args, **kwargs):
        raise address_suggestions.AddressSuggestionError("lookup failed: too slow")

    monkeypatch.setattr(address_suggestions, "_fetch_photon", fake_fetch)
    monkeypatch.setattr(address_suggestions, "_fetch_nominatim", fake_fetch)

    with pytest.raises(address_suggestions.AddressSuggestionError, match="lookup failed"):
        address_suggestions.suggest_addresses("123 main")
