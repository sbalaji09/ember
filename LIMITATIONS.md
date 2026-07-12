# Limitations Log

Running log of every null, `partial_failures` entry, resolution gap, and
judgment call hit while building and testing Ember. Kept for the write-up.

## Contract discrepancies vs. the README (Phase 0)

- The README lists `elevation, slope_degrees, lcms_class, tree_canopy_pct, `
  `ndvi_current, ndvi_change_5y, wildfire_annual_frequency` as "Expected from
  `wildfire_underwrite`." The live catalog (`GET /v1/meta/fields`) shows the
  actual preset is only 6 fields — it does **not** include
  `wildfire_annual_frequency`. That field lives in the `natural_hazard`
  preset instead. Ember requests it explicitly via `fields`, not via the
  preset. See `config.py:CENTROID_EXTRA_FIELDS`.
- `aspect_degrees` is not bundled in any of the 14 presets (only
  `aspect_cardinal` is, via `terrain`). Requested explicitly.
- `housing_units_density_per_km2`, `nearest_urban_area_distance_m`,
  `drought_category`, `days_above_32c_annual_count`, and
  `mean_annual_dry_bulb_temperature_degc` only appear bundled in siting
  presets (`data_center_siting`, `solar_siting`, `site_selection`,
  `wind_siting`) — none of which are wildfire-relevant. Requested explicitly.
- `dist_to_wui_m`, mentioned in the README as a fallback preference over the
  housing-density/urban-distance proxy, **does not exist** in the live
  catalog. Confirmed via `GET /v1/meta/fields` (255 fields, name absent).
  Ember uses the proxy (`housing_units_density_per_km2` +
  `nearest_urban_area_distance_m`) as the README's own fallback instructs.
- `parcel_address` is not bundled in any preset either — requested
  explicitly, alongside `tract_geoid` (needed for the report header, added
  during Phase 2 since the README's header spec calls for "tract" but no
  field was pre-selected for it).

## Phase 1 spike (Paradise, CA — 39.7596, -121.6219)

- All 19 requested fields returned `status: ok`. Zero `partial_failures`.
  Parcel geometry, address, and area were all populated — better than the
  README's "expect null on Regrid's free tier" caveat assumed for this
  particular point.
- `lcms_class` at that exact centroid returned `"Barren or Impervious"`
  with `tree_canopy_pct = 4.0%`, despite the surrounding area being
  forested WUI. The query point sits on/near Skyway road; the ~120m raster
  cell it falls in is dominated by pavement/cleared land, not the nearby
  canopy. This is a concrete, observed instance of the resolution mismatch
  the README warns about — a single centroid point can materially
  understate fuel load a few dozen meters away. It's the direct
  justification for ring sampling (25 points) rather than a single-point
  read.
- `dataset_vintage` was populated for some fields (`lcms_class`,
  `tree_canopy_pct`, `wildfire_annual_frequency`) and `null` for others
  (`ndvi_current`, `ndvi_change_5y`, `slope_degrees`). Treated as optional
  everywhere; never assumed present.

## Judgment calls made during scoring (Phase 2, documented since the README
   left them ambiguous)

- **Slope threat window center.** The README says "compute the uphill
  azimuth as the opposite of `aspect_degrees`" then "bearings within ±45°
  of 'fire approaching from downhill' get a multiplier." Ember interprets
  `aspect_degrees` itself (the downhill-facing compass direction) as the
  center of the threat window — a fire igniting downhill of the query point
  spreads upslope toward it, so the ring bearing pointing toward the
  downhill side is the dangerous approach direction. `uphill_azimuth` is
  computed and reported separately (for the "which way is uphill" line in
  the Terrain and Approach section) but is not the center of the multiplier
  window. See `scoring.py:slope_multiplier_for_bearing`.
- **Slope magnitude source.** `slope_degrees` is fetched per ring point
  (per the README's fetch strategy), not only at the centroid. Ember uses
  the mean `slope_degrees` across the 3 ring radii at each bearing as the
  multiplier's magnitude input, rather than the single centroid slope value,
  so a bearing with a locally steeper approach gets a stronger multiplier
  even if the centroid itself is flat.
- **Trend flag is landscape-wide, not per-bearing.** `ndvi_change_5y` is
  only fetched at the centroid (not part of `RING_FIELDS`, per the README's
  fetch strategy), so the drying/greening trend multiplier is applied
  uniformly across all 8 bearings rather than computed per direction.
- **Null/unresolved `lcms_class` scores as "low" fuel weight**, same as
  Barren/Impervious/Water, but is flagged as a data gap
  (`FUEL_CLASS_UNKNOWN_WEIGHT_KEY`) rather than silently treated as a real
  "low fuel" observation. Every gap is carried into `scored["gaps"]` and
  surfaced in the report, never dropped.
- **Missing overall-exposure drivers renormalize the composite** rather
  than being treated as zero. If, say, `drought_category` fails for a
  point, its weight is excluded from both the numerator and denominator of
  the weighted composite instead of dragging the score toward "Low" by
  default. The specific missing driver is still logged as a gap.
- **Parcel centroid is a vertex average**, not a true area-weighted
  polygon centroid — avoids adding a geometry library (shapely) for a
  small, roughly-convex residential parcel where the difference is
  immaterial. Falls back to the geocoded point with a fixed-radius ring
  when `parcel_boundary_geojson` is null/failed, per the README.

## Known resolution limits (carried into every report's "What this cannot
   see" section)

- `tree_canopy_pct` / `lcms_class`: ~120m block-mode rasters.
  `wildfire_annual_frequency`: census-tract resolution. Neither can resolve
  individual 5/30/100 ft defensible-space zones — Ember works at
  landscape/direction scale (100m/250m/500m rings) and maps the standard
  CAL FIRE zone checklist onto the directional findings.
- `ndvi_current` / `ndvi_change_5y`: ~10m Sentinel-2, but still a
  point-in-time snapshot — treated as indicative of dryness/trend, not a
  continuous moisture monitor.
- No hydrant, road-egress, evacuation, fuel-moisture, roof, vent, or
  structure-material fields exist in the Mireye catalog at all.
- Structure-hardening advice (`cal_fire_zones.py`) is static CAL FIRE
  guidance, never derived from an observation of the actual structure —
  Mireye's Overture-derived building fields give height/footprint/class,
  not roof material or vent type.
- CAL FIRE Zone 0 (ember-resistant zone, AB 3074 / PRC 4291) status caveat
  is carried in every report: statewide effective/enforcement dates were
  still being phased in as of this build; verify current status against
  CAL FIRE for the specific jurisdiction before treating it as settled.

## Environment / tooling

- Local Python 3.13 (`/Library/Frameworks/Python.framework`) has a broken
  system CA trust store — bare `urllib`/`http.client` requests to
  `api.mireye.com` fail with `CERTIFICATE_VERIFY_FAILED`. `requests` (which
  bundles `certifi`) works fine and is what `mireye_client.py` and
  `geocode.py` use. Worth a note if this is deployed to a similarly
  configured machine.
- `.env` held `MIREYE_TOKEN` but was not gitignored when the repo was
  created — added `.gitignore` (`.env`, `__pycache__/`, venvs) before any
  further work, so the token can't land in a commit.
