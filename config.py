"""All tunable constants for Ember. Scoring weights live here, not in scoring.py."""

# --- Mireye API ---
MIREYE_BASE_URL_DEFAULT = "https://api.mireye.com"
MIREYE_MAX_RETRIES = 3
MIREYE_RETRY_BACKOFF_SECONDS = 1.5  # exponential: backoff * (2 ** attempt)
MIREYE_TIMEOUT_SECONDS = 30

# Coordinates are rounded to this many decimal degrees before cache lookup.
# 3 decimals ~= 85-111m at CA latitudes, close to the ~120m fuel-raster cell
# size, so nearby ring points that likely hit the same raster cell dedupe.
CACHE_COORD_PRECISION = 3

CENTROID_PRESET = "wildfire_underwrite"

# Fields requested only at the centroid (full field set).
CENTROID_EXTRA_FIELDS = [
    "wildfire_annual_frequency",
    "aspect_degrees",
    "aspect_cardinal",
    "land_use_class",
    "housing_units_density_per_km2",
    "nearest_urban_area_distance_m",
    "design_wind_speed_mph",
    "drought_category",
    "days_above_32c_annual_count",
    "mean_annual_dry_bulb_temperature_degc",
    "parcel_boundary_geojson",
    "parcel_area_m2",
    "parcel_address",
    "tract_geoid",
]

# Fields requested at every ring point (fuel + terrain only, per README fetch strategy).
RING_FIELDS = ["lcms_class", "tree_canopy_pct", "ndvi_current", "slope_degrees"]

# --- Sampling geometry ---
RING_RADII_M = [100, 250, 500]
# 8 compass bearings, degrees clockwise from true north.
BEARINGS_DEG = [0, 45, 90, 135, 180, 225, 270, 315]
BEARING_LABELS = {
    0: "N", 45: "NE", 90: "E", 135: "SE",
    180: "S", 225: "SW", 270: "W", 315: "NW",
}
EARTH_RADIUS_M = 6371000.0

# Weight applied to each ring radius when aggregating fuel score per bearing.
# Closer radii matter more: fuel 100m away is a more immediate structure
# threat than fuel 500m away. Must sum to 1.0.
RADIUS_WEIGHTS = {100: 0.5, 250: 0.3, 500: 0.2}

# --- Fuel scoring (scoring.py: per-bearing fuel score) ---
# lcms_class is free text from a fixed USFS taxonomy (Trees, Shrubs,
# Grass/Forb/Herb, cover mixes, Barren or Impervious, Water, Snow or Ice).
# Matched by substring, case-insensitive, in this priority order.
FUEL_TYPE_WEIGHTS = {
    "high": 1.0,    # Trees, Shrubs, or mixes containing either
    "medium": 0.5,  # Grass / Forb / Herb
    "low": 0.1,     # Barren, Impervious, Water, Snow, Ice
}
FUEL_CLASS_KEYWORDS = {
    "high": ["tree", "shrub"],
    "medium": ["grass", "forb", "herb"],
}
# lcms_class null/unresolvable (outside CONUS grid footprint, nodata cell):
# score as "low" but this is a data gap, not an observation. Flagged
# separately in LIMITATIONS output, never silently dropped.
FUEL_CLASS_UNKNOWN_WEIGHT_KEY = "low"

# Canopy scaling: tree_canopy_pct in [0, 100] maps to a multiplier in
# [CANOPY_SCALE_MIN, 1.0]. A canopy of 0% still keeps a floor, since
# lcms_class already carries most of the fuel-type signal.
CANOPY_SCALE_MIN = 0.3

# Dryness factor from ndvi_current. NDVI below NDVI_DRY reads as fully cured
# fuel (max dryness multiplier); above NDVI_GREEN reads as fully green
# (min dryness multiplier). Linear ramp in between.
NDVI_DRY = 0.15
NDVI_GREEN = 0.60
DRYNESS_FACTOR_MIN = 0.6   # green vegetation
DRYNESS_FACTOR_MAX = 1.4   # cured/dry vegetation

# Trend flag from ndvi_change_5y (centroid-level, applied uniformly across
# all bearings — the ring does not fetch ndvi_change_5y per point).
# Negative change (drying trend over 5y) increases the multiplier.
NDVI_TREND_SENSITIVITY = 0.5  # multiplier = 1 - sensitivity * ndvi_change_5y
NDVI_TREND_MULTIPLIER_MIN = 0.8
NDVI_TREND_MULTIPLIER_MAX = 1.2

# --- Slope threat ---
# Judgment call (documented in LIMITATIONS.md): aspect_degrees is the
# compass direction the slope faces, i.e. the downhill direction from the
# query point. A fire igniting downhill of the house spreads upslope toward
# it, so the threat window is centered on aspect_degrees itself (the
# downhill azimuth), not on the uphill azimuth. uphill_azimuth
# (= aspect_degrees + 180) is computed separately and reported to the user
# as "which way is uphill", but it is not the center of the threat window.
SLOPE_THREAT_WINDOW_DEG = 45  # +/- around the downhill azimuth
SLOPE_DOUBLING_DEGREES = 10.0  # "spread roughly doubles per 10 degrees upslope" rule of thumb
SLOPE_MULTIPLIER_MAX = 4.0     # cap so a single steep bearing can't blow out the scale
SLOPE_MULTIPLIER_BASELINE = 1.0  # applied outside the threat window

# --- Overall exposure band ---
# Each driver is normalized to [0, 1] via clamp((value - lo) / (hi - lo), 0, 1)
# then combined by weighted sum. Weights must sum to 1.0.
EXPOSURE_DRIVER_RANGES = {
    "wildfire_annual_frequency": (0.0, 0.05),      # FEMA NRI annualized frequency
    # NOT the theoretical max (SLOPE_MULTIPLIER_MAX * FUEL_TYPE_WEIGHTS["high"] *
    # DRYNESS_FACTOR_MAX =~ 6.7): that combination (100% canopy AND fully cured
    # NDVI AND max slope multiplier, all at once) essentially never occurs in
    # real raster data. Calibrated instead against real ring-sampled directional
    # threat vectors across 6 genuinely severe CA WUI properties (Paradise,
    # Latigo Canyon/Malibu, Big Bear, Forest Falls, Julian, Alpine) with the
    # observed max at 1.147 (Latigo Canyon, slope multiplier already at cap) and
    # headroom above it. See LIMITATIONS.md for the calibration data.
    "max_directional_threat": (0.0, 1.8),
    "housing_units_density_per_km2": (0.0, 2000.0),
    "drought_category_ordinal": (0.0, 4.0),        # D0=0 .. D4=4, null="not in drought"=-1 clamped to 0
    "days_above_32c_annual_count": (0.0, 120.0),
    "design_wind_speed_mph": (85.0, 140.0),         # ASCE 7 design wind speeds rarely fall below ~85mph
}
EXPOSURE_DRIVER_WEIGHTS = {
    "wildfire_annual_frequency": 0.30,
    "max_directional_threat": 0.30,
    "housing_units_density_per_km2": 0.10,
    "drought_category_ordinal": 0.10,
    "days_above_32c_annual_count": 0.10,
    "design_wind_speed_mph": 0.10,
}
EXPOSURE_BANDS = [
    (0.25, "Low"),
    (0.45, "Moderate"),
    (0.65, "High"),
    (1.01, "Very High"),  # anything up to 1.0 (upper bound exclusive-safe)
]

DROUGHT_CATEGORY_ORDINAL = {None: 0, "D0": 0, "D1": 1, "D2": 2, "D3": 3, "D4": 4}

# Top N worst approach directions to surface in the report.
TOP_THREAT_DIRECTIONS = 2
