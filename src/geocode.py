"""Address -> lat/lng via the Census Geocoder. Free, US-only, keyless."""

import requests

CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
CENSUS_BENCHMARK = "Public_AR_Current"
REQUEST_TIMEOUT_SECONDS = 15


class GeocodeError(Exception):
    pass


def geocode(address):
    """Return {"lat": float, "lng": float, "matched_address": str} or raise GeocodeError."""
    params = {
        "address": address,
        "benchmark": CENSUS_BENCHMARK,
        "format": "json",
    }
    try:
        resp = requests.get(CENSUS_GEOCODER_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise GeocodeError(f"Census geocoder request failed: {exc}") from exc

    if resp.status_code != 200:
        raise GeocodeError(f"Census geocoder returned HTTP {resp.status_code}: {resp.text[:500]}")

    try:
        payload = resp.json()
    except ValueError as exc:
        raise GeocodeError(f"Census geocoder returned non-JSON response: {resp.text[:500]}") from exc

    matches = payload.get("result", {}).get("addressMatches", [])
    if not matches:
        raise GeocodeError(f"No geocode match for address: {address!r}")

    match = matches[0]
    coords = match.get("coordinates", {})
    lat = coords.get("y")
    lng = coords.get("x")
    if lat is None or lng is None:
        raise GeocodeError(f"Geocode match missing coordinates for address: {address!r}")

    return {
        "lat": float(lat),
        "lng": float(lng),
        "matched_address": match.get("matchedAddress", address),
    }
