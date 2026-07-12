"""Street-address autocomplete suggestions for the web UI.

Suggestions come from OSM-backed providers because they are keyless and
already match the frontend map stack. The final assessment still submits the
selected address to the Census geocoder; this module is only for ranked,
street-address suggestions while the user types.
"""

from functools import lru_cache
from difflib import SequenceMatcher
import re

import requests


NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_SEARCH_URL = "https://photon.komoot.io/api/"
REQUEST_TIMEOUT_SECONDS = 8
MIN_QUERY_CHARS = 3
MAX_QUERY_CHARS = 120
MAX_UPSTREAM_RESULTS = 24
CALIFORNIA_VIEWBOX = "-124.5,42.1,-114.0,32.4"  # left,top,right,bottom
CALIFORNIA_BBOX = "-124.5,32.4,-114.0,42.1"  # min lon,min lat,max lon,max lat
CALIFORNIA_BOUNDS = {
    "min_lat": 32.4,
    "max_lat": 42.1,
    "min_lng": -124.5,
    "max_lng": -114.0,
}
USER_AGENT = "Ember wildfire hardening advisor address autocomplete"


class AddressSuggestionError(Exception):
    pass


def suggest_addresses(query, limit=6):
    """Return ranked California street-address suggestions for partial text."""
    normalized = _normalize_query(query)
    if len(normalized) < MIN_QUERY_CHARS:
        return []

    safe_limit = max(1, min(int(limit), 10))
    return list(_suggest_addresses_cached(normalized.lower(), safe_limit))


@lru_cache(maxsize=256)
def _suggest_addresses_cached(normalized_query, limit):
    constraints = _query_constraints(normalized_query)
    suggestions = []
    seen = set()

    last_error = None
    provider_succeeded = False
    providers = (
        (_fetch_photon, _suggestion_from_photon_feature),
        (_fetch_nominatim, _suggestion_from_nominatim_item),
    )

    for fetcher, formatter in providers:
        for provider_query in _provider_queries(normalized_query, constraints):
            try:
                items = fetcher(provider_query, limit)
            except AddressSuggestionError as exc:
                last_error = exc
                continue
            provider_succeeded = True
            for item in items:
                suggestion = formatter(item, constraints)
                if not suggestion:
                    continue
                key = suggestion["address"].lower()
                if key in seen:
                    continue
                seen.add(key)
                suggestions.append(suggestion)
        if len(suggestions) >= limit:
            break

    if not provider_succeeded and last_error:
        raise last_error

    suggestions.sort(key=lambda item: (-item["_match_score"], -item["importance"], item["display"]))
    for idx, suggestion in enumerate(suggestions[:limit], start=1):
        suggestion["rank"] = idx
        suggestion.pop("_match_score", None)
    return tuple(suggestions[:limit])


def _fetch_photon(query, limit):
    params = {
        "q": query,
        "limit": str(max(MAX_UPSTREAM_RESULTS, limit * 3)),
        "lang": "en",
        "bbox": CALIFORNIA_BBOX,
    }
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}

    try:
        resp = requests.get(PHOTON_SEARCH_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise AddressSuggestionError(f"Address suggestion lookup failed: {exc}") from exc

    if resp.status_code != 200:
        raise AddressSuggestionError(f"Address suggestion lookup returned HTTP {resp.status_code}: {resp.text[:300]}")

    try:
        payload = resp.json()
    except ValueError as exc:
        raise AddressSuggestionError(f"Address suggestion lookup returned non-JSON response: {resp.text[:300]}") from exc

    return payload.get("features", [])


def _suggestion_from_photon_feature(feature, constraints):
    props = feature.get("properties") or {}
    coords = (feature.get("geometry") or {}).get("coordinates") or []
    if len(coords) < 2:
        return None

    address = {
        "house_number": props.get("housenumber"),
        "road": props.get("street"),
        "city": props.get("city"),
        "town": props.get("town"),
        "village": props.get("village"),
        "county": props.get("county"),
        "state": props.get("state"),
        "postcode": props.get("postcode"),
        "country_code": (props.get("countrycode") or "").lower(),
        "neighbourhood": props.get("district"),
        "suburb": props.get("locality"),
        "name": props.get("name"),
    }

    if not _is_california_street_address(address):
        return None
    if not _matches_query_constraints(address, constraints):
        return None

    try:
        lng = float(coords[0])
        lat = float(coords[1])
    except (TypeError, ValueError):
        return None

    if not _within_california_bounds(lat, lng):
        return None

    street = _street_line(address)
    city = _city_name(address)
    state_zip = _state_zip(address)
    concise = ", ".join(part for part in (street, city, state_zip) if part)
    if not concise:
        return None

    return {
        "address": concise,
        "display": concise,
        "secondary": _secondary_label(address),
        "lat": lat,
        "lng": lng,
        "importance": _importance(props),
        "_match_score": _match_score(address, constraints),
        "source": "Photon / OpenStreetMap",
    }


def _fetch_nominatim(query, limit):
    params = {
        "format": "jsonv2",
        "addressdetails": "1",
        "limit": str(max(MAX_UPSTREAM_RESULTS, limit * 3)),
        "countrycodes": "us",
        "viewbox": CALIFORNIA_VIEWBOX,
        "bounded": "1",
        "dedupe": "1",
        "q": query,
    }
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}

    try:
        resp = requests.get(NOMINATIM_SEARCH_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise AddressSuggestionError(f"Address suggestion lookup failed: {exc}") from exc

    if resp.status_code != 200:
        raise AddressSuggestionError(f"Address suggestion lookup returned HTTP {resp.status_code}: {resp.text[:300]}")

    try:
        return resp.json()
    except ValueError as exc:
        raise AddressSuggestionError(f"Address suggestion lookup returned non-JSON response: {resp.text[:300]}") from exc


def _suggestion_from_nominatim_item(item, constraints):
    address = item.get("address") or {}
    if not _is_california_street_address(address):
        return None
    if not _matches_query_constraints(address, constraints):
        return None

    try:
        lat = float(item["lat"])
        lng = float(item["lon"])
    except (KeyError, TypeError, ValueError):
        return None

    if not _within_california_bounds(lat, lng):
        return None

    street = _street_line(address)
    city = _city_name(address)
    state_zip = _state_zip(address)
    concise = ", ".join(part for part in (street, city, state_zip) if part)
    if not concise:
        return None

    return {
        "address": concise,
        "display": concise,
        "secondary": _secondary_label(address),
        "lat": lat,
        "lng": lng,
        "importance": _importance(item),
        "_match_score": _match_score(address, constraints),
        "source": "OpenStreetMap Nominatim",
    }


def _normalize_query(query):
    normalized = re.sub(r"\s+", " ", str(query or "")).strip()
    return normalized[:MAX_QUERY_CHARS]


def _query_constraints(query):
    query = _normalize_query(query).casefold()
    house_number_prefix = ""
    text = query
    match = re.match(r"^(\d+[a-z]?)\b", query)
    if match:
        house_number_prefix = _normalize_house_number(match.group(1))
        text = query[match.end() :]

    return {
        "house_number_prefix": house_number_prefix,
        "tokens": _meaningful_query_tokens(text),
    }


def _provider_queries(normalized_query, constraints):
    queries = []

    def add(query):
        query = _normalize_query(query).casefold()
        if query and query not in queries:
            queries.append(query)

    if constraints["house_number_prefix"] and not constraints["tokens"]:
        add(f"{constraints['house_number_prefix']} california")
        add(f"{constraints['house_number_prefix']} ca")
        add(normalized_query)
        return queries

    add(normalized_query)
    if " ca" not in f" {normalized_query} " and "california" not in normalized_query:
        add(f"{normalized_query} california")
        add(f"{normalized_query} ca")
    return queries[:3]


def _meaningful_query_tokens(text):
    stopwords = {
        "apt",
        "apartment",
        "ave",
        "avenue",
        "blvd",
        "boulevard",
        "ca",
        "california",
        "circle",
        "cir",
        "court",
        "ct",
        "dr",
        "drive",
        "lane",
        "ln",
        "place",
        "pl",
        "road",
        "rd",
        "st",
        "street",
        "suite",
        "unit",
        "usa",
        "way",
    }
    tokens = []
    for token in re.findall(r"[a-z0-9]+", text.casefold()):
        if len(token) < 2 or token in stopwords:
            continue
        tokens.append(token)
    return tokens


def _matches_query_constraints(address, constraints):
    house_number_prefix = constraints["house_number_prefix"]
    if house_number_prefix:
        house_number = _normalize_house_number(address.get("house_number"))
        if not house_number.startswith(house_number_prefix):
            return False

    tokens = constraints["tokens"]
    if not tokens:
        return bool(house_number_prefix)

    return all(_best_token_match(token, address)["score"] > 0 for token in tokens)


def _match_score(address, constraints):
    score = 0.0
    house_number_prefix = constraints["house_number_prefix"]
    if house_number_prefix:
        house_number = _normalize_house_number(address.get("house_number"))
        score += 4.0 if house_number == house_number_prefix else 2.0

    road = (_road_name(address) or "").casefold()
    city = (_city_name(address) or "").casefold()
    for token in constraints["tokens"]:
        match = _best_token_match(token, address)
        score += match["score"]
        if match["field"] == "road" and road.startswith(token):
            score += 1.0
        elif match["field"] == "city" and city.startswith(token):
            score += 0.5
    return score


def _best_token_match(token, address):
    candidates = (
        ("name", address.get("name"), 3.5),
        ("road", _road_name(address), 4.0),
        ("city", _city_name(address), 3.0),
        ("postcode", address.get("postcode"), 2.5),
        ("county", address.get("county"), 2.0),
        ("neighbourhood", address.get("neighbourhood") or address.get("suburb"), 2.0),
    )
    best = {"score": 0.0, "field": None}
    for field, value, weight in candidates:
        for part in _match_parts(value):
            score = _token_part_score(token, part, weight)
            if score > best["score"]:
                best = {"score": score, "field": field}
    return best


def _match_parts(value):
    return re.findall(r"[a-z0-9]+", str(value or "").casefold())


def _token_part_score(token, part, weight):
    if not token or not part:
        return 0.0
    if part == token:
        return weight
    if part.startswith(token):
        return weight * 0.92
    if token in part:
        return weight * 0.72
    if len(token) >= 4 and SequenceMatcher(None, token, part).ratio() >= 0.78:
        return weight * 0.55
    return 0.0


def _normalize_house_number(value):
    return re.sub(r"[^0-9a-z]", "", str(value or "").casefold())


def _is_california_street_address(address):
    if address.get("country_code") != "us":
        return False
    state = (address.get("state") or "").casefold()
    state_code = (address.get("state_code") or "").casefold()
    iso = (address.get("ISO3166-2-lvl4") or "").casefold()
    if state != "california" and state_code != "ca" and iso != "us-ca":
        return False
    return bool(address.get("house_number") and _road_name(address))


def _within_california_bounds(lat, lng):
    return (
        CALIFORNIA_BOUNDS["min_lat"] <= lat <= CALIFORNIA_BOUNDS["max_lat"]
        and CALIFORNIA_BOUNDS["min_lng"] <= lng <= CALIFORNIA_BOUNDS["max_lng"]
    )


def _street_line(address):
    return " ".join(part for part in (address.get("house_number"), _road_name(address)) if part)


def _road_name(address):
    for key in ("road", "pedestrian", "residential", "footway", "cycleway", "path"):
        if address.get(key):
            return address[key]
    return ""


def _city_name(address):
    for key in ("city", "town", "village", "hamlet", "county"):
        if address.get(key):
            return address[key]
    return ""


def _state_zip(address):
    state = "CA"
    postcode = address.get("postcode")
    return " ".join(part for part in (state, postcode) if part)


def _secondary_label(address):
    parts = []
    name = address.get("name")
    if name and name != _road_name(address):
        parts.append(name)
    for key in ("neighbourhood", "suburb", "county"):
        value = address.get(key)
        if value and value not in parts:
            parts.append(value)
    return ", ".join(parts)


def _importance(item):
    try:
        return float(item.get("importance") or 0)
    except (TypeError, ValueError):
        return 0.0
