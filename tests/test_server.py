"""Shape tests for the /assess endpoint. Deterministic — no live Mireye or
Anthropic calls. The pipeline functions server.py wires together (geocode,
MireyeClient, sample_property, render_report) are monkeypatched; scoring
itself runs for real (it's pure, cheap compute) via the same synthetic
fixture test_scoring.py already uses.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pytest
from fastapi.testclient import TestClient

import server
from test_scoring import _synthetic_sample


class _FakeMireyeClient:
    def __init__(self, *args, **kwargs):
        self.all_partial_failures = []


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        server,
        "geocode",
        lambda address: {"lat": 39.75, "lng": -121.6, "matched_address": "TEST ADDRESS, CA"},
    )
    monkeypatch.setattr(server, "MireyeClient", _FakeMireyeClient)
    monkeypatch.setattr(server, "sample_property", lambda client, lat, lng: _synthetic_sample())
    return TestClient(server.app)


def test_assess_without_anthropic_key_degrades_gracefully(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    resp = client.post("/assess", json={"address": "123 Main St, Somewhere, CA"})
    assert resp.status_code == 200

    body = resp.json()
    assert set(body.keys()) == {"scored_blob", "prose", "prose_available", "prose_error"}
    assert body["prose"] is None
    assert body["prose_available"] is False
    assert "ANTHROPIC_API_KEY" in body["prose_error"]

    # scored_blob must be the real, fully-shaped report_data — not a stub.
    blob = body["scored_blob"]
    assert blob["overall"]["band"] in {"Low", "Moderate", "High", "Very High"}
    assert "fuel_history_caveat" in blob
    assert "bearings" in blob and len(blob["bearings"]) == 8
    # the env var NAME may appear in a diagnostic message (that's fine); the
    # actual secret VALUE must never appear anywhere in the response
    assert "sk-ant-" not in str(body)


def test_assess_with_prose_available(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-for-test")
    monkeypatch.setattr(server, "render_report", lambda report_data, client=None: "# Fake rendered report")

    resp = client.post("/assess", json={"address": "123 Main St, Somewhere, CA"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["prose_available"] is True
    assert body["prose"] == "# Fake rendered report"
    assert body["prose_error"] is None
    assert "sk-ant-fake-for-test" not in str(body)


def test_assess_geocode_failure_returns_422(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def _raise(address):
        raise server.GeocodeError(f"No geocode match for address: {address!r}")

    monkeypatch.setattr(server, "geocode", _raise)

    resp = client.post("/assess", json={"address": "not a real address"})
    assert resp.status_code == 422
    assert "No geocode match" in resp.json()["detail"]


def test_assess_empty_address_returns_400(client):
    resp = client.post("/assess", json={"address": "   "})
    assert resp.status_code == 400


def test_address_suggestions_returns_backend_suggestions(client, monkeypatch):
    monkeypatch.setattr(
        server,
        "suggest_addresses",
        lambda query, limit=6: [
            {
                "address": "123 Main St, Santa Rosa, CA 95401",
                "display": "123 Main St, Santa Rosa, CA 95401",
                "secondary": "Sonoma County",
                "lat": 38.44,
                "lng": -122.71,
                "importance": 0.4,
                "rank": 1,
                "source": "OpenStreetMap Nominatim",
            }
        ],
    )

    resp = client.get("/address-suggestions", params={"q": "123 main", "limit": 3})
    assert resp.status_code == 200

    body = resp.json()
    assert body["suggestions"][0]["address"] == "123 Main St, Santa Rosa, CA 95401"
    assert body["suggestions"][0]["rank"] == 1


def test_address_suggestions_empty_query_returns_empty_list(client):
    resp = client.get("/address-suggestions", params={"q": "   "})
    assert resp.status_code == 200
    assert resp.json() == {"suggestions": []}
