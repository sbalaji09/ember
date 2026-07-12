"""Deterministic directional threat model. No LLM involvement — every number
here is computed from Mireye field values and the weights in config.py.

Every intermediate and final number carries its citation(s): a list of
{field, value, status, source, source_url, confidence, fetched_at,
dataset_vintage, point}. report.py renders these; it does not recompute
or reinterpret them.
"""

import config


def get_field(envelope, name):
    return envelope.get("fields", {}).get(name)


def get_value(envelope, name):
    field = get_field(envelope, name)
    if field is None or field.get("status") != "ok":
        return None
    return field.get("value")


def citation(field_name, envelope, point=None):
    field = get_field(envelope, field_name) or {}
    return {
        "field": field_name,
        "value": field.get("value"),
        "status": field.get("status", "absent"),
        "source": field.get("source"),
        "source_url": field.get("source_url"),
        "confidence": field.get("confidence", "unknown"),
        "fetched_at": field.get("fetched_at"),
        "dataset_vintage": field.get("dataset_vintage"),
        "point": point,
    }


def angular_diff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def fuel_type_weight(lcms_class_value):
    """Returns (weight, is_gap). is_gap=True means the class was unresolved
    (null/absent), scored as 'low' by convention but flagged as a gap."""
    if lcms_class_value is None:
        return config.FUEL_TYPE_WEIGHTS[config.FUEL_CLASS_UNKNOWN_WEIGHT_KEY], True

    text = lcms_class_value.lower()
    for keyword in config.FUEL_CLASS_KEYWORDS["high"]:
        if keyword in text:
            return config.FUEL_TYPE_WEIGHTS["high"], False
    for keyword in config.FUEL_CLASS_KEYWORDS["medium"]:
        if keyword in text:
            return config.FUEL_TYPE_WEIGHTS["medium"], False
    return config.FUEL_TYPE_WEIGHTS["low"], False


def canopy_scale(tree_canopy_pct):
    if tree_canopy_pct is None:
        return config.CANOPY_SCALE_MIN, True
    pct = max(0.0, min(100.0, tree_canopy_pct))
    scale = config.CANOPY_SCALE_MIN + (1.0 - config.CANOPY_SCALE_MIN) * (pct / 100.0)
    return scale, False


def dryness_factor(ndvi_current):
    if ndvi_current is None:
        midpoint = (config.DRYNESS_FACTOR_MIN + config.DRYNESS_FACTOR_MAX) / 2.0
        return midpoint, True
    clamped = max(config.NDVI_DRY, min(config.NDVI_GREEN, ndvi_current))
    frac_green = (clamped - config.NDVI_DRY) / (config.NDVI_GREEN - config.NDVI_DRY)
    factor = config.DRYNESS_FACTOR_MAX - frac_green * (
        config.DRYNESS_FACTOR_MAX - config.DRYNESS_FACTOR_MIN
    )
    return factor, False


def trend_multiplier(ndvi_change_5y):
    if ndvi_change_5y is None:
        return 1.0, True
    multiplier = 1.0 - config.NDVI_TREND_SENSITIVITY * ndvi_change_5y
    multiplier = max(config.NDVI_TREND_MULTIPLIER_MIN, min(config.NDVI_TREND_MULTIPLIER_MAX, multiplier))
    return multiplier, False


def slope_multiplier_for_bearing(bearing_deg, aspect_degrees, bearing_avg_slope):
    """Judgment call, documented in LIMITATIONS.md: the threat window is
    centered on aspect_degrees (the downhill azimuth) — fire igniting
    downhill of the house spreads upslope toward it."""
    if aspect_degrees is None or bearing_avg_slope is None:
        return config.SLOPE_MULTIPLIER_BASELINE, True

    diff = angular_diff(bearing_deg, aspect_degrees)
    if diff > config.SLOPE_THREAT_WINDOW_DEG:
        return config.SLOPE_MULTIPLIER_BASELINE, False

    multiplier = 2.0 ** (bearing_avg_slope / config.SLOPE_DOUBLING_DEGREES)
    return min(multiplier, config.SLOPE_MULTIPLIER_MAX), False


def score_bearing(bearing_deg, ring_points_for_bearing, trend_mult, trend_is_gap, aspect_degrees):
    """ring_points_for_bearing: list of ring-sample dicts (from sampling.py)
    at this bearing, one per radius, each with an 'envelope' key."""
    citations = []
    gaps = []
    weighted_fuel_sum = 0.0
    slopes = []

    for point in ring_points_for_bearing:
        envelope = point["envelope"]
        radius = point["radius_m"]
        loc = {"lat": point["lat"], "lng": point["lng"]}

        lcms_value = get_value(envelope, "lcms_class")
        tcp_value = get_value(envelope, "tree_canopy_pct")
        ndvi_value = get_value(envelope, "ndvi_current")
        slope_value = get_value(envelope, "slope_degrees")

        fuel_weight, fuel_gap = fuel_type_weight(lcms_value)
        canopy_mult, canopy_gap = canopy_scale(tcp_value)
        dry_mult, dry_gap = dryness_factor(ndvi_value)

        point_fuel_score = fuel_weight * canopy_mult * dry_mult
        radius_weight = config.RADIUS_WEIGHTS.get(radius, 0.0)
        weighted_fuel_sum += point_fuel_score * radius_weight

        if slope_value is not None:
            slopes.append(slope_value)

        for field_name, is_gap in (
            ("lcms_class", fuel_gap),
            ("tree_canopy_pct", canopy_gap),
            ("ndvi_current", dry_gap),
            ("slope_degrees", slope_value is None),
        ):
            citations.append(citation(field_name, envelope, point=loc))
            if is_gap:
                gaps.append(
                    {"field": field_name, "point": loc, "bearing": bearing_deg, "radius_m": radius}
                )

    bearing_avg_slope = sum(slopes) / len(slopes) if slopes else None
    fuel_score = weighted_fuel_sum * trend_mult
    if trend_is_gap:
        gaps.append({"field": "ndvi_change_5y", "point": None, "bearing": bearing_deg, "radius_m": None})

    slope_mult, slope_gap = slope_multiplier_for_bearing(bearing_deg, aspect_degrees, bearing_avg_slope)
    if slope_gap:
        gaps.append({"field": "aspect_degrees/slope_degrees", "point": None, "bearing": bearing_deg, "radius_m": None})

    directional_threat = fuel_score * slope_mult

    return {
        "bearing_deg": bearing_deg,
        "label": config.BEARING_LABELS[bearing_deg],
        "fuel_score": fuel_score,
        "avg_slope_degrees": bearing_avg_slope,
        "slope_multiplier": slope_mult,
        "directional_threat": directional_threat,
        "citations": citations,
        "gaps": gaps,
    }


def normalize(value, lo, hi):
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def score_overall_exposure(centroid_envelope, max_directional_threat):
    drought_value = get_value(centroid_envelope, "drought_category")
    drought_ordinal = config.DROUGHT_CATEGORY_ORDINAL.get(drought_value, 0)

    raw_values = {
        "wildfire_annual_frequency": get_value(centroid_envelope, "wildfire_annual_frequency"),
        "max_directional_threat": max_directional_threat,
        "housing_units_density_per_km2": get_value(centroid_envelope, "housing_units_density_per_km2"),
        "drought_category_ordinal": drought_ordinal,
        "days_above_32c_annual_count": get_value(centroid_envelope, "days_above_32c_annual_count"),
        "design_wind_speed_mph": get_value(centroid_envelope, "design_wind_speed_mph"),
    }

    drivers = {}
    gaps = []
    available_weight = 0.0
    weighted_sum = 0.0

    for name, raw in raw_values.items():
        weight = config.EXPOSURE_DRIVER_WEIGHTS[name]
        lo, hi = config.EXPOSURE_DRIVER_RANGES[name]

        driver_citation = None
        if name == "max_directional_threat":
            driver_citation = None  # derived, not a single Mireye field; cited via per-bearing citations
        elif name == "drought_category_ordinal":
            driver_citation = citation("drought_category", centroid_envelope)
        else:
            driver_citation = citation(name, centroid_envelope)

        if raw is None:
            gaps.append({"field": name, "reason": "missing or failed at centroid"})
            drivers[name] = {"raw": None, "normalized": None, "weight": weight, "citation": driver_citation}
            continue

        normalized = normalize(raw, lo, hi)
        drivers[name] = {"raw": raw, "normalized": normalized, "weight": weight, "citation": driver_citation}
        weighted_sum += normalized * weight
        available_weight += weight

    composite = weighted_sum / available_weight if available_weight > 0 else 0.0

    band = config.EXPOSURE_BANDS[-1][1]
    for threshold, label in config.EXPOSURE_BANDS:
        if composite <= threshold:
            band = label
            break

    return {"composite": composite, "band": band, "drivers": drivers, "gaps": gaps}


def score_property(sample):
    """sample: output of sampling.sample_property(). Returns the full
    deterministic scoring result: per-bearing threat vectors, top threat
    directions, overall exposure band, uphill direction, and every gap
    encountered."""
    centroid_envelope = sample["centroid_envelope"]
    aspect_degrees = get_value(centroid_envelope, "aspect_degrees")
    uphill_azimuth = (aspect_degrees + 180.0) % 360.0 if aspect_degrees is not None else None

    ndvi_change_5y = get_value(centroid_envelope, "ndvi_change_5y")
    trend_mult, trend_gap = trend_multiplier(ndvi_change_5y)

    ring_by_bearing = {}
    for point in sample["ring"]:
        ring_by_bearing.setdefault(point["bearing"], []).append(point)

    bearings = {}
    all_gaps = []
    for bearing_deg in config.BEARINGS_DEG:
        points = ring_by_bearing.get(bearing_deg, [])
        result = score_bearing(bearing_deg, points, trend_mult, trend_gap, aspect_degrees)
        bearings[result["label"]] = result
        all_gaps.extend(result["gaps"])

    ranked = sorted(bearings.values(), key=lambda b: b["directional_threat"], reverse=True)
    top_threats = ranked[: config.TOP_THREAT_DIRECTIONS]
    max_directional_threat = ranked[0]["directional_threat"] if ranked else 0.0

    overall = score_overall_exposure(centroid_envelope, max_directional_threat)
    all_gaps.extend(overall["gaps"])

    if aspect_degrees is None:
        all_gaps.append({"field": "aspect_degrees", "point": None, "bearing": None, "radius_m": None})

    return {
        "aspect_degrees": aspect_degrees,
        "aspect_citation": citation("aspect_degrees", centroid_envelope),
        "uphill_azimuth": uphill_azimuth,
        "bearings": bearings,
        "top_threats": top_threats,
        "overall": overall,
        "gaps": all_gaps,
        "ndvi_change_5y_citation": citation("ndvi_change_5y", centroid_envelope),
    }
