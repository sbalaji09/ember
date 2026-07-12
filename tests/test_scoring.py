import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import config
import scoring


def make_field(value, status="ok"):
    return {
        "value": value,
        "unit": None,
        "source": "TEST_SOURCE",
        "source_url": "https://example.com/test",
        "confidence": "high",
        "fetched_at": "2026-01-01T00:00:00Z",
        "dataset_vintage": None,
        "ttl_seconds": 0,
        "notes": None,
        "status": status,
        "error": None if status == "ok" else "synthetic failure",
        "retryable": False,
    }


def make_envelope(**fields):
    return {
        "lat": 0.0,
        "lng": 0.0,
        "fetched_at": "2026-01-01T00:00:00Z",
        "fields": {name: make_field(value) for name, value in fields.items()},
        "partial_failures": [],
    }


def make_ring_point(bearing, radius, **fields):
    return {
        "label": f"{config.BEARING_LABELS[bearing]}_{radius}m",
        "bearing": bearing,
        "radius_m": radius,
        "lat": 0.0,
        "lng": 0.0,
        "envelope": make_envelope(**fields),
    }


def uniform_ring(bearing, lcms_class, tree_canopy_pct, ndvi_current, slope_degrees):
    return [
        make_ring_point(
            bearing,
            radius,
            lcms_class=lcms_class,
            tree_canopy_pct=tree_canopy_pct,
            ndvi_current=ndvi_current,
            slope_degrees=slope_degrees,
        )
        for radius in config.RING_RADII_M
    ]


# --- Unit-level component tests ---


def test_fuel_type_weight_forested_beats_barren():
    trees_weight, trees_gap = scoring.fuel_type_weight("Trees")
    barren_weight, barren_gap = scoring.fuel_type_weight("Barren or Impervious")
    assert trees_weight > barren_weight
    assert not trees_gap and not barren_gap


def test_fuel_type_weight_grass_is_medium():
    weight, gap = scoring.fuel_type_weight("Grass/Forb/Herb")
    assert weight == config.FUEL_TYPE_WEIGHTS["medium"]
    assert not gap


def test_fuel_type_weight_null_is_gap():
    weight, gap = scoring.fuel_type_weight(None)
    assert gap is True
    assert weight == config.FUEL_TYPE_WEIGHTS[config.FUEL_CLASS_UNKNOWN_WEIGHT_KEY]


def test_canopy_scale_monotonic():
    low, _ = scoring.canopy_scale(0.0)
    high, _ = scoring.canopy_scale(100.0)
    assert high > low
    assert low == config.CANOPY_SCALE_MIN


def test_dryness_factor_cured_beats_green():
    cured, cured_gap = scoring.dryness_factor(0.05)  # below NDVI_DRY floor
    green, green_gap = scoring.dryness_factor(0.9)  # above NDVI_GREEN ceiling
    assert cured > green
    assert not cured_gap and not green_gap


def test_trend_multiplier_drying_increases_score():
    drying, _ = scoring.trend_multiplier(-0.2)  # NDVI dropped over 5y
    greening, _ = scoring.trend_multiplier(0.2)  # NDVI rose over 5y
    assert drying > 1.0
    assert greening < 1.0
    assert drying > greening


def test_slope_multiplier_steep_downhill_bearing_amplifies():
    # aspect_degrees=0 means the slope faces (downhill direction is) north.
    # A bearing of 0 (north) is within the threat window.
    steep, gap = scoring.slope_multiplier_for_bearing(bearing_deg=0, aspect_degrees=0, bearing_avg_slope=30)
    assert not gap
    assert steep > config.SLOPE_MULTIPLIER_BASELINE


def test_slope_multiplier_outside_window_is_baseline():
    mult, gap = scoring.slope_multiplier_for_bearing(bearing_deg=180, aspect_degrees=0, bearing_avg_slope=30)
    assert not gap
    assert mult == config.SLOPE_MULTIPLIER_BASELINE


def test_slope_multiplier_flat_slope_near_baseline():
    mult, gap = scoring.slope_multiplier_for_bearing(bearing_deg=0, aspect_degrees=0, bearing_avg_slope=0)
    assert not gap
    assert mult == 1.0  # 2 ** (0/10) == 1.0


def test_slope_multiplier_missing_aspect_is_gap():
    mult, gap = scoring.slope_multiplier_for_bearing(bearing_deg=0, aspect_degrees=None, bearing_avg_slope=30)
    assert gap is True
    assert mult == config.SLOPE_MULTIPLIER_BASELINE


# --- score_bearing synthetic scenarios ---


def test_score_bearing_flat_vs_steep():
    flat_points = uniform_ring(0, "Trees", 50.0, 0.4, 2.0)
    steep_points = uniform_ring(0, "Trees", 50.0, 0.4, 30.0)

    flat = scoring.score_bearing(0, flat_points, trend_mult=1.0, trend_is_gap=False, aspect_degrees=0)
    steep = scoring.score_bearing(0, steep_points, trend_mult=1.0, trend_is_gap=False, aspect_degrees=0)

    assert steep["slope_multiplier"] > flat["slope_multiplier"]
    assert steep["directional_threat"] > flat["directional_threat"]


def test_score_bearing_forested_vs_barren():
    forested = uniform_ring(90, "Trees", 80.0, 0.4, 0.0)
    barren = uniform_ring(90, "Barren or Impervious", 0.0, 0.4, 0.0)

    forested_result = scoring.score_bearing(90, forested, trend_mult=1.0, trend_is_gap=False, aspect_degrees=None)
    barren_result = scoring.score_bearing(90, barren, trend_mult=1.0, trend_is_gap=False, aspect_degrees=None)

    assert forested_result["fuel_score"] > barren_result["fuel_score"]
    assert forested_result["directional_threat"] > barren_result["directional_threat"]


def test_score_bearing_cured_vs_green():
    cured = uniform_ring(180, "Shrubs", 40.0, 0.05, 0.0)
    green = uniform_ring(180, "Shrubs", 40.0, 0.9, 0.0)

    cured_result = scoring.score_bearing(180, cured, trend_mult=1.0, trend_is_gap=False, aspect_degrees=None)
    green_result = scoring.score_bearing(180, green, trend_mult=1.0, trend_is_gap=False, aspect_degrees=None)

    assert cured_result["fuel_score"] > green_result["fuel_score"]


def test_score_bearing_missing_fields_flagged_as_gaps_not_crash():
    point = make_ring_point(0, 100, lcms_class=None, tree_canopy_pct=None, ndvi_current=None, slope_degrees=None)
    result = scoring.score_bearing(0, [point], trend_mult=1.0, trend_is_gap=False, aspect_degrees=None)
    assert result["directional_threat"] >= 0
    gap_fields = {g["field"] for g in result["gaps"]}
    assert {"lcms_class", "tree_canopy_pct", "ndvi_current", "slope_degrees"} <= gap_fields


def test_score_bearing_failed_status_treated_as_missing():
    envelope = make_envelope()
    envelope["fields"]["lcms_class"] = make_field("Trees", status="failed")
    point = {"label": "N_100m", "bearing": 0, "radius_m": 100, "lat": 0.0, "lng": 0.0, "envelope": envelope}
    result = scoring.score_bearing(0, [point], trend_mult=1.0, trend_is_gap=False, aspect_degrees=None)
    gap_fields = {g["field"] for g in result["gaps"]}
    assert "lcms_class" in gap_fields


# --- score_overall_exposure ---


def test_overall_exposure_bands_low_vs_very_high():
    low_centroid = make_envelope(
        wildfire_annual_frequency=0.0005,
        housing_units_density_per_km2=50.0,
        drought_category=None,
        days_above_32c_annual_count=5,
        design_wind_speed_mph=85.0,
    )
    low = scoring.score_overall_exposure(low_centroid, max_directional_threat=0.1)

    high_centroid = make_envelope(
        wildfire_annual_frequency=0.05,
        housing_units_density_per_km2=1800.0,
        drought_category="D4",
        days_above_32c_annual_count=110,
        design_wind_speed_mph=140.0,
    )
    high = scoring.score_overall_exposure(high_centroid, max_directional_threat=4.0)

    assert low["composite"] < high["composite"]
    assert low["band"] == "Low"
    assert high["band"] == "Very High"


def test_overall_exposure_missing_driver_is_gap_not_crash():
    centroid = make_envelope(
        wildfire_annual_frequency=0.01,
        # housing_units_density_per_km2 omitted entirely (absent field)
        drought_category="D1",
        days_above_32c_annual_count=40,
        design_wind_speed_mph=100.0,
    )
    result = scoring.score_overall_exposure(centroid, max_directional_threat=1.0)
    assert result["band"] in {"Low", "Moderate", "High", "Very High"}
    gap_fields = {g["field"] for g in result["gaps"]}
    assert "housing_units_density_per_km2" in gap_fields


# --- score_property end-to-end with a synthetic sample ---


def _synthetic_sample():
    centroid_envelope = make_envelope(
        wildfire_annual_frequency=0.01,
        aspect_degrees=0.0,  # downhill faces north
        aspect_cardinal="N",
        land_use_class="Forest",
        housing_units_density_per_km2=200.0,
        nearest_urban_area_distance_m=1000.0,
        design_wind_speed_mph=100.0,
        drought_category="D2",
        days_above_32c_annual_count=50,
        mean_annual_dry_bulb_temperature_degc=15.0,
        parcel_boundary_geojson=None,
        parcel_area_m2=None,
        parcel_address=None,
        ndvi_change_5y=-0.1,
        elevation=500.0,
        slope_degrees=10.0,
        lcms_class="Trees",
        tree_canopy_pct=60.0,
        ndvi_current=0.3,
    )

    ring = []
    for bearing in config.BEARINGS_DEG:
        for radius in config.RING_RADII_M:
            # North bearing (aligned with aspect=0) is steep + forested + cured;
            # everything else is flat + barren + green.
            if bearing == 0:
                fields = dict(lcms_class="Trees", tree_canopy_pct=80.0, ndvi_current=0.1, slope_degrees=35.0)
            else:
                fields = dict(lcms_class="Barren or Impervious", tree_canopy_pct=0.0, ndvi_current=0.7, slope_degrees=1.0)
            ring.append(make_ring_point(bearing, radius, **fields))

    return {
        "geocoded": {"lat": 39.75, "lng": -121.6},
        "origin": {"lat": 39.75, "lng": -121.6, "source": "geocoded_point_fixed_radius_fallback", "parcel_aware": False},
        "centroid_envelope": centroid_envelope,
        "ring": ring,
    }


def test_score_property_identifies_worst_direction():
    result = scoring.score_property(_synthetic_sample())
    assert result["top_threats"][0]["label"] == "N"
    assert result["uphill_azimuth"] == 180.0  # opposite of aspect_degrees=0
    assert result["overall"]["band"] in {"Low", "Moderate", "High", "Very High"}
    # every bearing present
    assert set(result["bearings"].keys()) == set(config.BEARING_LABELS.values())
