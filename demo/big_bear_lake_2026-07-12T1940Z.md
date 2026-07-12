# Wildfire Hardening Report — 40650 Village Dr, Big Bear Lake, CA

**Matched Address:** 40650 VILLAGE DR, BIG BEAR LAKE, CA, 92315
**Parcel Area:** 19,417.34 m² (source: REGRID)
**Census Tract GEOID:** 06071011205 (source: CENSUS_GEOCODING)

---

## Overall Exposure

**Composite Score:** 0.1727
**Exposure Band:** Low

This composite is derived from a weighted blend of the following drivers:

| Driver | Raw Value | Normalized | Weight | Source | Confidence |
|---|---|---|---|---|---|
| Wildfire annual frequency | 0.013553222519485437 | 0.2711 | 0.3 | FEMA_NRI | medium |
| Max directional threat | 0.29905071309927206 | 0.1661 | 0.3 | — | — |
| Housing units density (per km²) | 160.4767400198713 | 0.0802 | 0.1 | CENSUS_TIGERWEB | medium |
| Drought category ordinal | 0 (status: absent) | 0.0 | 0.1 | USDM_CURRENT | high |
| Days above 32°C (annual count) | 1 | 0.0083 | 0.1 | NOAA_NCEI_NCLIMGRID_DAILY | medium |
| Design wind speed (mph) | 103.0 | 0.3273 | 0.1 | NOAA_ASCE_WIND_VECTORS | medium |

Note: the drought category value is marked **absent** in the underlying data (status: "absent") and contributed a normalized value of 0.0 to the composite. No overall data gaps were flagged beyond this.

---

## Interpretation Caveat

This area has a recorded wildfire history in the tract-level data, but the current fuel reading directly around the property is low. A low current fuel reading may reflect prior burn, clearing, or development rather than durable safety.

Associated wildfire annual frequency figure: **0.013553222519485437** (source: FEMA_NRI).

This is a note on how to interpret the fuel data alongside historical fire occurrence — it does not change or reinterpret the Low exposure band stated above.

---

## Terrain and Approach

- **Aspect:** 110.44° (slope faces this direction), sourced from USGS_3DEP_COG (confidence: medium).
- **Uphill azimuth:** 290.44° — fire moving upslope toward the parcel would generally approach from this direction.
- **Top directional threats:** South (directional threat 0.2991, average slope 15.14°) and Southwest (directional threat 0.2503, average slope 10.73°). Both carry a slope multiplier of 1.0.
- The slope-threat evaluation window is 45° around each compass label.

These directional and slope figures are landscape-scale findings (from ~120m and point-sampled data along rings around the parcel centroid) and describe the general terrain/fuel context in these directions — they are not observations of specific defensible-space zone contents.

---

## Directional Fuel Findings

| Direction | Fuel Score | Avg Slope (°) | Slope Multiplier | Directional Threat |
|---|---|---|---|---|
| N | 0.0478 | 5.16 | 1.0 | 0.0478 |
| NE | 0.1976 | 3.14 | 1.0 | 0.1976 |
| E | 0.0529 | 4.25 | 1.343 | 0.0711 |
| SE | 0.1059 | 4.52 | 1.368 | 0.1448 |
| S | 0.2991 | 15.14 | 1.0 | 0.2991 |
| SW | 0.2503 | 10.73 | 1.0 | 0.2503 |
| W | 0.1988 | 5.82 | 1.0 | 0.1988 |
| NW | 0.0471 | 3.14 | 1.0 | 0.0471 |

Underlying land cover in sampled points ranges from "Barren or Impervious" to "Trees" and "Water," with tree canopy cover percentages (from ~120m block-mean rasters) ranging roughly from 3% to 40% across sampled points, and NDVI readings (point-in-time, Sentinel-2, 60-day window ending 2026-07-12) varying widely by point. These are landscape-scale characterizations at ~120m resolution (canopy/land cover) or point samples (slope, NDVI) along direction rings — they do not resolve to specific 5/30/100 ft zone contents.

South and Southwest are the two highest-threat directions and are prioritized in the action plan below.

---

## Prioritized Action Plan

The following CAL FIRE defensible-space zone checklist is applied to the two highest-threat directions identified above: **South** (directional threat 0.2991) and **Southwest** (directional threat 0.2503). This checklist is a static, prescriptive standard — it is not a report of what currently exists at this property.

### Direction: South (directional threat 0.2991)

**Zone 0 (0–5 ft from structures, decks, and attachments)**
- Remove all combustible mulch, vegetation, and stored items within 5 ft of the structure.
- Use hardscape (gravel, pavers, concrete) instead of bark mulch or plants immediately against the house.
- Clear dead leaves and needles from roofs, gutters, and under decks.
- Do not stack firewood or store propane/fuel within this zone.

**Zone 1 (5–30 ft from structures)**
- Space tree canopies at least 10 ft apart; remove ladder fuels (shrubs under trees).
- Keep grass mowed to under 4 inches.
- Remove dead or dying vegetation and dispose of plant debris.
- Prune tree branches up 6–10 ft from the ground.

**Zone 2 (30–100 ft from structures)**
- Create horizontal and vertical spacing between shrubs and trees to break up continuous fuel.
- Remove fallen leaves, needles, and dead branches regularly.
- Reduce density of flammable brush, especially on slopes facing the structure.
- Maintain fire breaks along property lines shared with wildland vegetation.

### Direction: Southwest (directional threat 0.2503)

**Zone 0 (0–5 ft from structures, decks, and attachments)**
- Remove all combustible mulch, vegetation, and stored items within 5 ft of the structure.
- Use hardscape (gravel, pavers, concrete) instead of bark mulch or plants immediately against the house.
- Clear dead leaves and needles from roofs, gutters, and under decks.
- Do not stack firewood or store propane/fuel within this zone.

**Zone 1 (5–30 ft from structures)**
- Space tree canopies at least 10 ft apart; remove ladder fuels (shrubs under trees).
- Keep grass mowed to under 4 inches.
- Remove dead or dying vegetation and dispose of plant debris.
- Prune tree branches up 6–10 ft from the ground.

**Zone 2 (30–100 ft from structures)**
- Create horizontal and vertical spacing between shrubs and trees to break up continuous fuel.
- Remove fallen leaves, needles, and dead branches regularly.
- Reduce density of flammable brush, especially on slopes facing the structure.
- Maintain fire breaks along property lines shared with wildland vegetation.

**Zone 0 Regulatory Note:** Zone 0 (ember-resistant zone) comes from AB 3074 and PRC 4291. As of this report, statewide effective/enforcement dates were still being phased in. Verify current Zone 0 regulatory status for this property's jurisdiction against CAL FIRE before treating it as a compliance deadline.

Zone checklist source: CAL FIRE Defensible Space (PRC 4291 / AB 3074) — https://www.fire.ca.gov/dspace

### Structure Hardening (Generic Guidance)

Roof, vent, eave, and siding hardening guidance below is generic CAL FIRE prescriptive advice, not an observation of this structure. Mireye provides building height, footprint, and class through Overture, but does not observe roof material, vent type, or siding — this structure has not been inspected.

- Class A fire-rated roofing, with no gaps or damaged sections.
- 1/8-inch ember- and flame-resistant mesh screens on all attic, foundation, and soffit vents.
- Enclosed eaves; avoid open-eave construction where possible.
- Dual-pane or tempered glass windows to resist radiant heat cracking.
- Non-combustible or ignition-resistant siding within 6 inches of grade.

---

## Sources

| Source | Source URL | Confidence | Fetched At |
|---|---|---|---|
| REGRID | https://app.regrid.com/api/v2/parcels/point | high | 2026-07-12T18:39:36.540944+00:00 / 2026-07-12T18:39:36.540790+00:00 |
| CENSUS_GEOCODING | https://geocoding.geo.census.gov/geocoder/geographies/coordinates | high | 2026-07-12T18:39:36.531540+00:00 |
| FEMA_NRI | https://hazards.fema.gov/nri/ | medium | 2026-07-12T18:39:36.169052+00:00 |
| CENSUS_TIGERWEB | https://tigerweb.geo.census.gov/arcgisweb/ | medium | 2026-07-12T18:39:36.490588+00:00 |
| USDM_CURRENT | https://droughtmonitor.unl.edu/ | high | 2026-07-12T18:39:36.117503+00:00 |
| NOAA_NCEI_NCLIMGRID_DAILY | https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily | medium | 2026-07-12T18:39:39.547600+00:00 |
| NOAA_ASCE_WIND_VECTORS | https://services2.arcgis.com/C8EMgrsFcRFL6LrL/arcgis/rest/services/ASCE_Wind_Vectors/FeatureServer | medium | 2026-07-12T18:39:36.167928+00:00 |
| USGS_3DEP_COG | https://www.usgs.gov/3d-elevation-program | medium | multiple timestamps, 2026-07-12T18:39:37.140941+00:00 through 2026-07-12T18:48:55.629017+00:00 |
| USFS_LCMS | https://data.fs.usda.gov/geodata/rastergateway/LCMS/ | medium | multiple timestamps, 2026-07-12T18:39:39.664524+00:00 through 2026-07-12T19:08:08.550377+00:00 |
| USFS_NLCD_TCC | https://data.fs.usda.gov/geodata/rastergateway/treecanopycover/ | high | multiple timestamps, 2026-07-12T18:39:39.665227+00:00 through 2026-07-12T18:39:46.826777+00:00 |
| COPERNICUS_S2_SR_HARMONIZED | https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED | high | multiple timestamps, 2026-07-12T18:39:41.847946+00:00 through 2026-07-12T18:39:50.774590+00:00 |
| CAL FIRE Defensible Space (PRC 4291 / AB 3074) | https://www.fire.ca.gov/dspace | — | — |

---

## What This Cannot See

- **tree_canopy_pct** and **lcms_class** are ~120m block-mode rasters, and **wildfire_annual_frequency** is resolved at census-tract level. Individual 5/30/100 ft defensible-space zone contents cannot be resolved from these inputs — this report works at landscape/directional scale (rings around the parcel centroid) and maps the standard CAL FIRE zone checklist onto those directional findings, not onto observed zone-by-zone conditions.
- No hydrant, road-egress, evacuation-route, fuel-moisture, roof, vent, or structure-material fields are available from Mireye.
- Structure-hardening advice presented above is prescriptive CAL FIRE guidance, not evidence from an observation of this building's roof, vents, eaves, or siding.
- **ndvi_current** values are point-in-time snapshots (Sentinel-2, 60-day window ending 2026-07-12) and should be treated as indicative of conditions at that time, not a continuous monitor of vegetation dryness.
- Ring origin used for directional analysis: parcel centroid.
- The `max_directional_threat` driver in the Overall Exposure composite has no citation in the underlying data (citation: null) — it is a derived value from the directional analysis, not a separately sourced external dataset.
