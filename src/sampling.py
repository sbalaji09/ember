"""Ring generation and Mireye sampling: centroid + 8 bearings x 3 radii.

Parcel-aware: if the geocoded point's parcel_boundary_geojson resolves
(Polygon or MultiPolygon), the ring radiates from the parcel's centroid
instead of the raw geocoded point. If parcel geometry is null (expected on
Regrid's free tier per the README) or unparseable, falls back to a fixed
radius from the geocoded point.
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


def _strip_closing_vertex(ring):
    return ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring


def _vertex_average(coords):
    if not coords:
        return None
    avg_lng = sum(pt[0] for pt in coords) / len(coords)
    avg_lat = sum(pt[1] for pt in coords) / len(coords)
    return avg_lat, avg_lng


def _polygon_area_and_centroid(exterior_coords):
    """Signed area and centroid of a simple polygon's exterior ring via the
    shoelace formula. exterior_coords are (lng, lat) pairs with no closing
    duplicate. Returns (signed_area, (lat, lng)) or (0.0, None) if degenerate
    (fewer than 3 vertices, or zero area)."""
    n = len(exterior_coords)
    if n < 3:
        return 0.0, None

    area = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(n):
        x0, y0 = exterior_coords[i]
        x1, y1 = exterior_coords[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area *= 0.5
    if area == 0:
        return 0.0, None

    cx /= 6 * area
    cy /= 6 * area
    return area, (cy, cx)  # (lat, lng)


def parcel_centroid_from_geojson(geojson_str):
    """Centroid of a parcel's Polygon or MultiPolygon geometry.

    Polygon: vertex-average of the exterior ring. Not an area-weighted
    centroid (would need a geometry library for full correctness); for the
    small, roughly-convex residential parcels this targets, the vertex
    average is a reasonable approximation of the parcel center.

    MultiPolygon: area-weighted centroid across parts, computed via the
    shoelace formula on each part's exterior ring, weighted by |area| and
    combined. Chosen over "centroid of the largest part" because Regrid
    MultiPolygon parcels seen in practice (e.g. Latigo Canyon, Malibu) have
    a dominant part plus small slivers (easements, right-of-way clips) —
    area-weighting lets the dominant part drive the result while still
    accounting for the others, rather than discarding them outright. Falls
    back to a simple vertex-average across all parts' vertices if every
    part is degenerate (zero area).

    Returns (lat, lng) or None if the geometry can't be parsed/is empty —
    the caller falls back to the geocoded point in that case.
    """
    try:
        geom = json.loads(geojson_str)
    except (TypeError, ValueError):
        return None

    geom_type = geom.get("type")

    if geom_type == "Polygon":
        rings = geom.get("coordinates")
        if not rings or not rings[0]:
            return None
        coords = _strip_closing_vertex(rings[0])
        return _vertex_average(coords)

    if geom_type == "MultiPolygon":
        parts = geom.get("coordinates")
        if not parts:
            return None

        weighted_lat = 0.0
        weighted_lng = 0.0
        total_weight = 0.0
        all_vertices = []

        for part in parts:
            if not part or not part[0]:
                continue
            exterior = _strip_closing_vertex(part[0])
            if not exterior:
                continue
            all_vertices.extend(exterior)

            area, centroid = _polygon_area_and_centroid(exterior)
            if centroid is None:
                continue
            weight = abs(area)
            weighted_lat += centroid[0] * weight
            weighted_lng += centroid[1] * weight
            total_weight += weight

        if total_weight > 0:
            return weighted_lat / total_weight, weighted_lng / total_weight

        # Every part was degenerate (zero area) — fall back to a plain
        # vertex-average across all parts rather than giving up entirely.
        return _vertex_average(all_vertices)

    return None


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
