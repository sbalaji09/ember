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

## Fuel/history interpretation caveat (`fuel_history_caveat`)

Follow-up to the calibration investigation above. After the
`max_directional_threat` tuning fix, Paradise still scores `Low`. Its ring
data genuinely reads barren/low-canopy at multiple bearings — consistent
with post-Camp-Fire clearing and rebuild along Skyway. Rather than silently
accept or silently boost that `Low`, Ember now surfaces a **non-band-affecting
disclosure** when a property's current fuel reads low in a tract that still
has *some* recorded wildfire frequency: `Low` may reflect a recent burn or
clearing, not durable safety.

**Important honesty correction versus how this was originally framed.**
The original hypothesis (see the calibration section above) was "high
historical frequency + low current fuel." That framing doesn't survive
contact with the actual data: Paradise's own `wildfire_annual_frequency`
(0.0014) is **not elevated** — it's the second-lowest of the 7 addresses in
the survey, roughly 33x lower than Julian's (0.046). FEMA NRI's tract-level
annualized frequency does not appear to reflect Paradise's well-documented
catastrophic 2018 history (plausible causes: it measures event frequency,
not severity of a single catastrophic event; tract boundaries or the
underlying table may have been affected by the same disaster; the metric is
national and may not weight singular megafires the way local intuition
would). This is itself a real, separate data limitation worth stating
plainly, not something to paper over by mislabeling the trigger condition.

Because of this, the flag's trigger is **"a measurably non-zero recorded
frequency," not "elevated/significant" frequency** — it distinguishes tracts
with any recorded wildfire history at all from tracts reading a true 0.0
(pure urban core). The caveat text reflects this honestly ("a recorded
history," never "a significant/elevated history").

**Thresholds (`config.py`), empirically grounded against the same 7-address
survey used for the `max_directional_threat` fix:**

| Location | wildfire_annual_frequency | mean fuel_score (8 bearings) | Must fire? |
|---|---|---|---|
| Santa Rosa (flat, urban) | ~0.00001 | 0.065 | **must NOT** |
| Paradise (post-Camp-Fire) | 0.0014 | 0.148 | **must** |
| Big Bear Lake | 0.0136 | 0.150 | (not required, but legitimate) |
| Latigo Canyon, Malibu | 0.0127 | 0.288 | must NOT |
| Julian (Cedar Fire town) | 0.0460 | 0.206 | must NOT |
| Alpine | 0.0224 | 0.258 | must NOT |
| Forest Falls | 0.0314 | 0.339 | must NOT |

- `WILDFIRE_HISTORY_PRESENT_THRESHOLD = 0.001` — sits just above Santa
  Rosa's near-zero reading and at/below Paradise's 0.0014, so it separates
  "any recorded frequency" from "no recorded frequency," not "high" from
  "low."
- `LOW_CURRENT_FUEL_MEAN_SCORE_THRESHOLD = 0.16` — sits between the
  {Paradise, Big Bear} cluster (~0.148-0.150) and the next-lowest real
  sample, Julian, at 0.206.

**Actual firing results, run through the real pipeline (`./ember --json`),
not hand-calculated:**

| Location | Triggered? |
|---|---|
| Paradise | **TRIGGERED** ✓ (required) |
| Big Bear Lake | TRIGGERED (fuel legitimately reads just as low as Paradise's — same resolution-mismatch story, not a fluke) |
| Latigo Canyon | not triggered (fuel isn't low) |
| Forest Falls | not triggered |
| Julian | not triggered |
| Alpine | not triggered |
| Santa Rosa (flat) | **not triggered** ✓ (required) |

**Non-band-affecting by design.** `check_fuel_history_caveat()` in
`scoring.py` takes the centroid envelope and the mean per-bearing fuel score
as inputs and is never called by, or passed into, `score_overall_exposure()`
— there is no code path by which its output can influence `composite` or
`band`. Verified two ways:
1. A golden-value regression test
   (`test_fuel_history_caveat_is_additive_band_and_composite_unchanged`)
   locks the exact `composite` (`0.488939393939394`) and `band` (`"High"`)
   for the existing synthetic fixture, captured before this feature existed,
   and asserts they're still exactly equal after adding it.
2. Re-ran all 7 real addresses before and after: every band is identical.
   (Composite values drifted by a few hundredths between the two runs —
   e.g. Paradise 0.1809 -> 0.1516 — but that's live NDVI data changing
   under a rolling 60-day Sentinel-2 window between the two `./ember`
   invocations, not the code change; `max_directional_threat` and the other
   drivers were untouched by this feature and the band never moved.)

`fuel_history_caveat` is emitted as its own top-level key in the `--json`
output (`triggered`, `reason`, `wildfire_annual_frequency_citation`,
`mean_fuel_score`, `thresholds`) and, when `triggered` is true, rendered in
`report.py` as its own "Interpretation Caveat" section — the system prompt
requires Claude to render `reason` verbatim and forbids using it to imply
the exposure band should be read differently than stated.

## report.py live-key verification (first real render)

`render_report()` had never been run against a live `ANTHROPIC_API_KEY` until
this pass — it's the last untested path in the pipeline, and this was treated
as a verification pass rather than a demo.

**Bug found: silently empty reports.** The first live call used
`model="claude-sonnet-5"` with `max_tokens=4096` and no `thinking` parameter.
Extended thinking is on by default for this model and consumed the *entire*
4096-token budget before writing any output text — the API call succeeded
(HTTP 200, `stop_reason: "max_tokens"`), but `render_report()` returned an
empty string, and the CLI printed nothing with exit code 0. This would have
looked like a working, if terse, integration in any test that only checked
the exit code. Fixed with `max_tokens=8192` and `thinking={"type": "disabled"}`
in the `messages.create()` call.

**No automated test coverage for `render_report()`.** It requires a live
Anthropic API key, so `tests/test_scoring.py` (the only test file) can't
exercise it. It was verified manually instead: ran `./ember` (prose) and
`./ember --json` (ground truth) on the same live Paradise fetch and diffed
every number/citation in the prose against the JSON. All matched exactly —
no invented numbers, sources, or reinterpreted band. Three lesser gaps found
on the same pass and fixed via `SYSTEM_PROMPT` tightening (pass-through only,
no new LLM-originated data):
1. The Interpretation Caveat section stated its boilerplate reason text but
   not the `wildfire_annual_frequency` value/source that triggered it,
   leaving the reader to find it in the Overall Exposure table instead.
   Fixed: system prompt now requires rendering
   `fuel_history_caveat.wildfire_annual_frequency_citation`'s `.value` and
   `.source` inline, explicitly as a pass-through ("render the value
   present in the JSON," never "state the frequency").
2. The Header section dropped `parcel_area_m2` and `tract_geoid` even though
   both were present in `build_report_data`'s output — the README specifies
   "parcel size, tract" belongs in the header. Fixed: system prompt now
   requires both, pass-through only, omitted gracefully if either field's
   status isn't `"ok"`.
3. The whole response was wrapped in a stray ` ```markdown ` fence — cosmetic
   but meant the CLI's raw printed output had literal backticks around the
   entire report. Fixed: system prompt now explicitly forbids wrapping the
   full response in a code fence.

Re-rendered Paradise after the fix and confirmed all three: the caveat now
reads "Wildfire annual frequency: 0.0013979252442599456 (source: FEMA_NRI)"
inline, which matches `./ember --json`'s
`fuel_history_caveat.wildfire_annual_frequency_citation.value` exactly
(`0.0013979252442599456`) — proving pass-through, not LLM invention; the
header shows parcel size and tract; no code fence appears anywhere in the
output. All 22 tests still pass (none of them exercise `render_report`
itself, per the gap noted above).

## Non-determinism across runs (NDVI rolling window)

Ember's output is **not deterministic across runs at different times**, even
for the same address with no code changes. `ndvi_current`'s dataset vintage
is a rolling ~60-day Sentinel-2 composite window that advances with the
query date, so per-bearing fuel scores (and therefore `max_directional_threat`
and the overall composite) can drift run to run. Observed directly during
this investigation: Paradise's composite moved from 0.1809 to 0.1516 to
0.1809 again across three `./ember` invocations made within the same
session, with `S` bearing's fuel score alone moving from 0.1587 to 0.1040
between two consecutive runs. The exposure band was stable across all of
these (`Low` throughout), but the exact composite was not. **Any captured
demo report must be timestamped** and treated as a snapshot, not a fixed
reference value — re-running the same address later is expected to produce
slightly different numbers, and that's a property of the live data sources,
not a bug.

## partial_failures are transient/retryable, not persistent per-location gaps

While capturing demo reports, Big Bear Lake (40650 Village Dr) was re-fetched
to serve as the live demonstration of "a real partial_failures entry
surfaces, it isn't dropped" (it had shown 3 `slope_degrees` DEM read
failures twice before, during the Phase 2 spike and the recalibration
investigation). At capture time it came back with `partial_failures: []` —
clean. Three immediate direct `/v1/fetch` retries at the exact failing
coordinates also came back clean. A time-boxed probe (~5 min) of 3 more
remote/rugged CA coordinates (Yosemite high country, Trinity Alps, a Mt.
Whitney ridge point) found no live failures either.

**Conclusion:** the DEM COG read failures are transient/retryable server-side
issues (consistent with `retryable: true` on those specific failures), not a
persistent gap tied to that location. This means "surface a real gap, don't
drop it" can't be reliably demonstrated with a live capture on demand — it
depends on catching a transient failure at exactly the right moment. Instead,
verified deterministically: `tests/test_report.py` forces a synthetic
`mireye_partial_failures` list through `build_report_data()` and asserts
(a) the list survives unfiltered into `report_data`, and (b) the failing
field name and error text are both present in the exact JSON string that
gets sent to Claude — the actual mechanism that would let a gap go missing
if some future refactor filtered fields out before serialization. Also
added: a case confirming an empty `partial_failures` list still renders as
an explicit empty list (key present), never an absent key, and a case
confirming `scoring.py`'s own `gaps` (distinct from Mireye-level
`partial_failures` — a null/failed field status, not a request-level
failure) also survive into `report_data` unfiltered.

## Frontend build: MultiPolygon gap in sampling.py, and a Leaflet API mistake

Building `frontend/` (Leaflet map + FastAPI backend at `src/server.py`)
surfaced two things:

**FOUND AND FIXED — real code bug, not a data limitation.**
`sampling.py`'s `parcel_centroid_from_geojson()` only handled GeoJSON
`Polygon` geometry — it returned `None` (triggering the fixed-radius
fallback) for `MultiPolygon`, even when valid geometry was present.

*How it was caught* is the more interesting part: this was invisible to
every prior verification pass (unit tests, `./ember --json` diffs, live
prose-rendering checks) because none of them rendered the parcel geometry
itself — they only checked that `ring_origin.source` reported a valid-looking
value (`"geocoded_point_fixed_radius_fallback"`), which it did, correctly
and honestly. It only surfaced once the frontend actually drew the parcel
outline on a map: at Latigo Canyon, Malibu, `parcel_boundary_geojson` is a
genuine `MultiPolygon` with `status: "ok"`, so Leaflet's `L.geoJSON()`
(which handles `MultiPolygon` natively) drew the real parcel shape — while
the ring-origin marker sat at the geocoded point next to it, not the
parcel's centroid. The mismatch was visible on the map in a way no curl
check or JSON diff would have caught, because the bug wasn't in any single
returned value being wrong — `ring_origin.source` genuinely was
`"geocoded_point_fixed_radius_fallback"` — it was in *why* that fallback
fired: not "no geometry" (the fallback's documented reason) but "geometry
present, unhandled shape," which no test was asserting against.

**Fix** (`src/sampling.py`): `parcel_centroid_from_geojson()` now branches
on `geom["type"]`. The `Polygon` path is untouched (still a simple
vertex-average of the exterior ring). For `MultiPolygon`, added a
shoelace-formula area-and-centroid calculation (`_polygon_area_and_centroid`)
per part, combined via an **area-weighted average across parts** — chosen
over "centroid of the largest part alone" because real Regrid `MultiPolygon`
parcels (Latigo Canyon included) tend to have one dominant part plus small
slivers (easements, right-of-way clips); area-weighting lets the dominant
part drive the result while still folding in the others, rather than
discarding them outright. If every part is degenerate (zero area), falls
back to a plain vertex-average across all parts' vertices rather than
giving up. The existing "genuinely null geometry → fall back to the
geocoded point" path is unchanged.

Added `tests/test_sampling.py` (7 new tests, 36 total passing): the
existing `Polygon` behavior locked down as a regression check; a synthetic
two-part `MultiPolygon` proving the result is dominated by the larger part
and is NOT the same as a naive combined vertex-average; degenerate and
empty-geometry edge cases; and a regression test using the **actual**
Latigo Canyon `MultiPolygon` geometry captured live, asserting the computed
centroid falls within the real parcel's bounding box and is meaningfully
different from the geocoded-point fallback.

**Re-verified Latigo Canyon end-to-end after the fix** (captured
2026-07-12T2047Z, superseding the earlier 2026-07-12T1940Z demo artifact):

| | Before fix | After fix |
|---|---|---|
| `ring_origin.source` | `geocoded_point_fixed_radius_fallback` | `parcel_centroid` |
| Band | Moderate (0.3209) | Moderate (0.3728) |
| Top threat | SW: 1.147 | SW: 1.459 |
| 2nd threat | W: 1.088 | W: 1.100 |

Band held (`Moderate`, not near either boundary at 0.25/0.45). Dominant
directions held (SW, W). The composite moved up somewhat because the true
parcel centroid sits slightly further into the steeper part of the canyon
than the geocoded point did — a more accurate number telling the same
story, not a different story.

**Debugging note:** the map briefly failed to auto-fit its view around the
drawn arrows/parcel with `mapLayerGroup.getBounds is not a function` —
`L.layerGroup()` doesn't implement `getBounds()`, only `L.featureGroup()`
does. Caught immediately by the app's own error-state handling (the UI
correctly showed the error message rather than hanging silently), which is
also incidental confirmation that the frontend's try/catch discipline works
as intended, not just its happy path.

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
