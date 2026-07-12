# Limitations Log

Running log of every null, `partial_failures` entry, resolution gap, and
judgment call hit while building and testing Ember. Kept for the write-up.

## Calibration investigation: Paradise, CA scored `Low` (post-Phase-2)

**Symptom.** `./ember --json` on 6626 Skyway, Paradise, CA (Camp Fire town,
2018) returned an overall exposure band of `Low` (composite 0.140). Paradise
being the highest-profile CA wildfire disaster of the last decade, a `Low`
band there is the kind of result that makes a reviewer distrust the whole
tool on sight — worth investigating before treating it as acceptable.

**Investigation.** Ran a known-severe control (3000 Latigo Canyon Rd,
Malibu — steep Santa Monica Mountains chaparral/oak canyon) through the same
pipeline. It also came back `Low` (composite 0.216), with its worst bearing's
**slope multiplier pinned at the config cap (4.0/4.0)** — i.e. the model's
own steepest-terrain signal was maxed out and the property still didn't
clear "Moderate." That's decisive on its own: a compressed-scale problem,
not a Paradise-specific one. To rule out cherry-picking a single control, four
more real addresses in independently well-known severe-fire WUI locations
were run through the full pipeline:

| Location | wildfire_annual_frequency (raw) | max_directional_threat (raw) | Band (before fix) | Composite |
|---|---|---|---|---|
| Paradise, CA | 0.0014 | 0.448 | Low | 0.140 |
| Latigo Canyon, Malibu | 0.0127 | 1.147 (slope mult at cap) | Low | 0.216 |
| Big Bear Lake | 0.0136 | 0.299 | Low | 0.145 |
| Forest Falls (San Bernardino NF) | 0.0314 | 0.896 | Moderate | 0.290 |
| Julian (2003 Cedar Fire town) | 0.0460 | 0.359 | Moderate | 0.379 |
| Alpine (San Diego backcountry) | 0.0224 | 0.815 | Moderate | 0.299 |

None of six real, independently-chosen severe-WUI properties reached `High`
or `Very High` — including Julian, the town the largest fire in California
history (at the time) nearly destroyed. **World (a): TUNING problem**, not
"the data genuinely can't see it."

**Root cause.** `EXPOSURE_DRIVER_RANGES["max_directional_threat"]` was set to
`(0.0, 4.0)` — the *theoretical* ceiling if a single ring bearing hit max
fuel weight (1.0), 100% canopy, fully cured NDVI (dryness factor 1.4), and
the slope multiplier cap (4.0) all simultaneously. That combination
essentially never occurs in real raster data: 120m block-mode canopy cells
rarely read 100%, and a cell rarely sits at the NDVI dry floor while also at
peak canopy. Across all 6 real test properties, the observed max was 1.147
(Latigo Canyon) — even with the slope multiplier already at its cap. Every
real directional threat value was landing in roughly the bottom quarter of
the normalization range no matter how severe the underlying terrain/fuel
actually was, which dragged the whole composite toward `Low` regardless of
real severity.

By contrast, `wildfire_annual_frequency`'s range `(0.0, 0.05)` was **not**
the problem — an 18-point spot-check across historically fire-prone CA
tracts (Clearlake, Julian, Alpine, La Tuna Canyon, Cobb, Fillmore, Pulga/Camp
Fire origin, and others) found an empirical ceiling around 0.046 (Julian),
which already normalizes to ~0.92 under the existing range. Left unchanged.

**Fix.** Single, minimal change in `config.py`:
`EXPOSURE_DRIVER_RANGES["max_directional_threat"]` changed from `(0.0, 4.0)`
to `(0.0, 1.8)`, calibrated against the observed real-world max (1.147) plus
headroom, not against any single address's desired outcome. No band
thresholds, weights, or other driver ranges were touched.

**Before/after, all 7 addresses (including a flat-terrain control,
100 Santa Rosa Ave, that should NOT move bands):**

| Location | Before | After | Notes |
|---|---|---|---|
| Paradise, CA | Low (0.140) | Low (0.181) | Stays Low — genuinely barren/low-canopy at the sampled ring (see Phase 1 note below), correctly does not flip |
| Latigo Canyon, Malibu | Low (0.216) | **Moderate (0.321)** | Flips band — steep, forested, real terrain now counted properly |
| Big Bear Lake | Low (0.145) | Low (0.173) | Stays Low — partial DEM read failures there limited the slope signal at this specific point (see `partial_failures` note) |
| Forest Falls | Moderate (0.290) | Moderate (0.366) | Moves up within-band, doesn't flip |
| Julian (Cedar Fire town) | Moderate (0.379) | Moderate (0.412) | Moves up within-band, doesn't flip |
| Alpine | Moderate (0.299) | Moderate (0.374) | Moves up within-band, doesn't flip |
| Santa Rosa (flat, low-severity control) | Low (0.111) | Low (0.125) | Barely moves — confirms the fix doesn't inflate genuinely low-risk properties |

The flat control staying flat, and Paradise staying `Low`, are the important
negative results here: this wasn't a fix that inflates everything or that
was reverse-engineered to move Paradise specifically. `tests/test_scoring.py`
was re-run after the change — all 18 tests passed with no modifications
needed (the synthetic "low vs. very high" exposure test uses
`max_directional_threat=4.0` for its high case, which now clamps to the new
range's ceiling exactly as it clamped to the old one, so its assertions were
unaffected by construction).

**Remaining open question (explaining, not tuning).** Even after the fix,
Paradise stays `Low`. Its ring data genuinely reads `lcms_class = "Barren or
Impervious"` with `tree_canopy_pct` in the single digits at multiple
bearings — consistent with post-Camp-Fire clearing and rebuild, not with the
forested ridge the town sat on before 2018. This is very plausibly a case
where **current fuel is genuinely low** even though **tract-level historical
frequency is not trivial** — the "recently burned, currently cleared" signal
and the "used to be, and may again become, severely exposed" signal are in
real tension, and the tool as built averages them into one composite number
rather than flagging the tension itself. This wasn't fixed as part of this
investigation (the six-address survey showed the dominant problem was a
genuine tuning bug, not this), but it's a legitimate follow-up: a dedicated
flag for "high historical tract frequency + low current fuel reading" would
make the report more honest about recently-burned properties like Paradise
specifically. Not implemented yet — flagging for a future pass before
demos are captured for a Paradise-area address.

**Incidental finding, not a scoring bug.** `design_wind_speed_mph` returned
exactly `103.0` mph at every one of 6 widely separated CA points tested
(San Francisco, Los Angeles, Redding, Sequoia NF, Julian, Clearlake) during
this investigation. Real ASCE 7 basic wind speed maps for non-hurricane-prone
interior/coastal California are genuinely coarse, so this may not be a data
bug — but it means this driver currently contributes a constant, essentially
non-discriminating ~0.033 to every property's composite. Harmless to the
Low/Moderate/High ordering (it's a wash across candidates), but worth noting
if the weighting is revisited later.

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
