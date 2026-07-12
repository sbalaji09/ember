"""Ring generation and Mireye sampling: centroid + 8 bearings x 3 radii.

Parcel-aware: if the geocoded point's parcel_boundary_geojson resolves, the
ring radiates from the parcel's (vertex-average) centroid instead of the
raw geocoded point. If parcel geometry is null (expected on Regrid's free
tier per the README), falls back to a fixed radius from the geocoded point.
"""

import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

import config


def destination_point(lat_deg, lng_deg, bearing_deg, distance_m):
    """Great-circle destination point given a start point, bearing, and distance."""
    lat1 = math.radians(lat_deg)
    lng1 = math.radians(lng_deg)
    bearing = math.radians(bearing_deg)
    ang_dist = distance_m / config.EARTH_RADIUS_M

    lat2 = math.asin(
        math.sin(lat1) * math.cos(ang_dist)
        + math.cos(lat1) * math.sin(ang_dist) * math.cos(bearing)
    )
    lng2 = lng1 + math.atan2(
        math.sin(bearing) * math.sin(ang_dist) * math.cos(lat1),
        math.cos(ang_dist) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lng2)


def parcel_centroid_from_geojson(geojson_str):
    """Vertex-average centroid of a parcel Polygon's exterior ring.

    Not an area-weighted centroid (would need a geometry library for that);
    for the small, roughly-convex residential parcels this targets, the
    vertex average is a reasonable approximation of the parcel center.
    Returns (lat, lng) or None if the geometry can't be parsed.
    """
    try:
        geom = json.loads(geojson_str)
    except (TypeError, ValueError):
        return None

    if geom.get("type") != "Polygon":
        return None
    rings = geom.get("coordinates")
    if not rings or not rings[0]:
        return None

    exterior = rings[0]
    # GeoJSON polygons repeat the first vertex as the last; drop the dup.
    coords = exterior[:-1] if len(exterior) > 1 and exterior[0] == exterior[-1] else exterior
    if not coords:
        return None

    avg_lng = sum(pt[0] for pt in coords) / len(coords)
    avg_lat = sum(pt[1] for pt in coords) / len(coords)
    return avg_lat, avg_lng


def generate_ring_points(origin_lat, origin_lng):
    """25 points: centroid + 8 bearings x 3 radii."""
    points = [
        {"label": "centroid", "bearing": None, "radius_m": 0, "lat": origin_lat, "lng": origin_lng}
    ]
    for bearing in config.BEARINGS_DEG:
        for radius in config.RING_RADII_M:
            lat, lng = destination_point(origin_lat, origin_lng, bearing, radius)
            points.append(
                {
                    "label": f"{config.BEARING_LABELS[bearing]}_{radius}m",
                    "bearing": bearing,
                    "radius_m": radius,
                    "lat": lat,
                    "lng": lng,
                }
            )
    return points


def resolve_origin(geocode_lat, geocode_lng, centroid_envelope):
    """Decide whether to radiate the ring from the parcel centroid or the
    raw geocoded point. Returns (origin_lat, origin_lng, source_label, parcel_aware)."""
    parcel_field = centroid_envelope.get("fields", {}).get("parcel_boundary_geojson", {})
    if parcel_field.get("status") == "ok" and parcel_field.get("value"):
        centroid = parcel_centroid_from_geojson(parcel_field["value"])
        if centroid is not None:
            return centroid[0], centroid[1], "parcel_centroid", True

    return geocode_lat, geocode_lng, "geocoded_point_fixed_radius_fallback", False


def sample_property(client, geocode_lat, geocode_lng, max_workers=8):
    """Fetch the full centroid field set at the geocoded point, resolve the
    parcel-aware ring origin, then fetch fuel/terrain fields at all 24 ring
    points in parallel. Returns a dict with geocoded point, resolved origin,
    centroid envelope, and per-ring-point envelopes."""
    centroid_envelope = client.fetch(
        geocode_lat, geocode_lng, fields=config.CENTROID_EXTRA_FIELDS, preset=config.CENTROID_PRESET
    )

    origin_lat, origin_lng, origin_source, parcel_aware = resolve_origin(
        geocode_lat, geocode_lng, centroid_envelope
    )

    ring_points = generate_ring_points(origin_lat, origin_lng)[1:]  # drop centroid, already fetched

    def fetch_point(point):
        envelope = client.fetch(point["lat"], point["lng"], fields=config.RING_FIELDS)
        return {**point, "envelope": envelope}

    ring_results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_point, p): p for p in ring_points}
        for future in as_completed(futures):
            ring_results.append(future.result())

    ring_results.sort(key=lambda r: (r["bearing"], r["radius_m"]))

    return {
        "geocoded": {"lat": geocode_lat, "lng": geocode_lng},
        "origin": {
            "lat": origin_lat,
            "lng": origin_lng,
            "source": origin_source,
            "parcel_aware": parcel_aware,
        },
        "centroid_envelope": centroid_envelope,
        "ring": ring_results,
    }
