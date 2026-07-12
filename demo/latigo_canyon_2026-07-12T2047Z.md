# Wildfire Hardening Report

**Property:** 3000 Latigo Canyon Rd, Malibu, CA (matched: 3000 LATIGO CANYON RD, MALIBU, CA, 90265)
**Parcel Area:** 11,326.02 m² (source: REGRID)
**Census Tract:** 06037800410 (source: CENSUS_GEOCODING)

---

## Overall Exposure

**Composite Score:** 0.373
**Band:** Moderate

This composite is derived from weighted drivers:

| Driver | Raw Value | Normalized | Weight | Source |
|---|---|---|---|---|
| Wildfire annual frequency | 0.01267 | 0.2534 | 0.30 | FEMA_NRI |
| Max directional threat | 1.4589 | 0.8105 | 0.30 | (computed, no external citation) |
| Housing unit density (per km²) | 2.544 | 0.0013 | 0.10 | CENSUS_TIGERWEB |
| Drought category ordinal | 0 (drought_category value absent) | 0.0 | 0.10 | USDM_CURRENT |
| Days above 32°C (annual count) | 25 | 0.2083 | 0.10 | NOAA_NCEI_NCLIMGRID_DAILY |
| Design wind speed (mph) | 103.0 | 0.3273 | 0.10 | NOAA_ASCE_WIND_VECTORS |

Note: the drought_category input value is marked **absent** in the underlying data (status: "absent"); its ordinal contribution to the composite is 0 as a result, not because drought conditions were confirmed absent. No other gaps were listed for this composite calculation.

---

## Terrain and Approach

- **Aspect:** 237.94° (source: USGS_3DEP_COG)
- **Uphill azimuth:** 57.94°
- **Slope-threat window:** 45°

The two highest directional threats both fall on the downhill/prevailing exposure side of the parcel:

| Direction | Directional Threat | Fuel Score | Slope Multiplier | Avg Slope (°) |
|---|---|---|---|---|
| SW | 1.4589 | 0.4123 | 3.538 | 18.23 |
| W | 1.0998 | 0.2750 | 4.000 | 30.03 |

These figures reflect landscape-scale directional modeling combining slope steepness and vegetation fuel signal — they are not point observations of specific defensible-space zone contents.

---

## Directional Fuel Findings

All eight compass directions were sampled at three ring distances outward from the parcel centroid. Values below are directional threat scores (fuel_score × slope_multiplier), each traceable to USFS_LCMS, USFS_NLCD_TCC, COPERNICUS_S2_SR_HARMONIZED, and USGS_3DEP_COG citations at ~120m raster / point resolution.

| Direction | Fuel Score | Avg Slope (°) | Slope Multiplier | Directional Threat |
|---|---|---|---|---|
| N | 0.2865 | 31.56 | 1.0 | 0.2865 |
| NE | 0.2448 | 19.32 | 1.0 | 0.2448 |
| E | 0.2627 | 25.42 | 1.0 | 0.2627 |
| SE | 0.2600 | 21.43 | 1.0 | 0.2600 |
| S | 0.2790 | 24.11 | 1.0 | 0.2790 |
| **SW** | **0.4123** | **18.23** | **3.538** | **1.4589** |
| **W** | **0.2750** | **30.03** | **4.000** | **1.0998** |
| NW | 0.2857 | 30.86 | 1.0 | 0.2857 |

The SW and W directions show markedly elevated directional threat, driven primarily by slope steepening (multipliers of 3.538 and 4.0 respectively) combined with tree-dominated land cover (`lcms_class: Trees`) at sampled points along those bearings. All other directions carry a slope multiplier of 1.0 and comparatively low directional threat.

These findings are landscape/directional in nature (sampled at ~120m resolution across 100–500m rings from parcel centroid) and cannot be resolved down to what is physically present within the 5/30/100 ft defensible-space zones immediately surrounding the structure.

---

## Prioritized Action Plan

Priority is assigned to the two highest-threat directions, **SW** (directional threat 1.4589) and **W** (directional threat 1.0998), using the standard CAL FIRE defensible-space zone checklist (source: CAL FIRE Defensible Space, PRC 4291 / AB 3074, https://www.fire.ca.gov/dspace). This checklist is prescriptive guidance mapped onto the directional findings above — it is not a record of what currently exists in those zones on this property.

### SW-Facing Priority (directional threat: 1.4589)

**Zone 0 (0–5 ft):**
- Remove all combustible mulch, vegetation, and stored items within 5 ft of the structure.
- Use hardscape (gravel, pavers, concrete) instead of bark mulch or plants immediately against the house.
- Clear dead leaves and needles from roofs, gutters, and under decks.
- Do not stack firewood or store propane/fuel within this zone.

**Zone 1 (5–30 ft):**
- Space tree canopies at least 10 ft apart; remove ladder fuels (shrubs under trees).
- Keep grass mowed to under 4 inches.
- Remove dead or dying vegetation and dispose of plant debris.
- Prune tree branches up 6–10 ft from the ground.

**Zone 2 (30–100 ft):**
- Create horizontal and vertical spacing between shrubs and trees to break up continuous fuel.
- Remove fallen leaves, needles, and dead branches regularly.
- Reduce density of flammable brush, especially on slopes facing the structure.
- Maintain fire breaks along property lines shared with wildland vegetation.

### W-Facing Priority (directional threat: 1.0998)

**Zone 0 (0–5 ft):** Same actions as above.
**Zone 1 (5–30 ft):** Same actions as above.
**Zone 2 (30–100 ft):** Same actions as above.

> **Zone 0 regulatory note:** Zone 0 (ember-resistant zone) comes from AB 3074 and PRC 4291. As of this report, statewide effective/enforcement dates were still being phased in. Verify current Zone 0 regulatory status for this property's jurisdiction against CAL FIRE before treating it as a compliance deadline.

### General Structure-Hardening Guidance (Generic — Not Based on Observation)

Roof, vent, eave, and siding hardening guidance below is generic CAL FIRE prescriptive advice, not an observation of this structure. Mireye provides building height, footprint, and class through Overture, but does not observe roof material, vent type, or siding — this structure was not inspected.

- Class A fire-rated roofing, with no gaps or damaged sections.
- 1/8-inch ember- and flame-resistant mesh screens on all attic, foundation, and soffit vents.
- Enclosed eaves; avoid open-eave construction where possible.
- Dual-pane or tempered glass windows to resist radiant heat cracking.
- Non-combustible or ignition-resistant siding within 6 inches of grade.

---

## Sources

| Source | URL | Confidence | Fetched At |
|---|---|---|---|
| REGRID | https://app.regrid.com/api/v2/parcels/point | high | 2026-07-12T18:36:45.232149+00:00, 2026-07-12T18:36:45.232392+00:00 |
| CENSUS_GEOCODING | https://geocoding.geo.census.gov/geocoder/geographies/coordinates | high | 2026-07-12T18:36:44.847995+00:00 |
| FEMA_NRI | https://hazards.fema.gov/nri/ | medium | 2026-07-12T18:36:44.534503+00:00 |
| CENSUS_TIGERWEB | https://tigerweb.geo.census.gov/arcgisweb/ | medium | 2026-07-12T18:36:44.859591+00:00 |
| USDM_CURRENT | https://droughtmonitor.unl.edu/ | high | 2026-07-12T18:36:44.472194+00:00 |
| NOAA_NCEI_NCLIMGRID_DAILY | https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily | medium | 2026-07-12T18:36:47.585194+00:00 |
| NOAA_ASCE_WIND_VECTORS | https://services2.arcgis.com/C8EMgrsFcRFL6LrL/arcgis/rest/services/ASCE_Wind_Vectors/FeatureServer | medium | 2026-07-12T18:36:44.516740+00:00 |
| USGS_3DEP_COG | https://www.usgs.gov/3d-elevation-program | medium | multiple timestamps, 2026-07-12T20:46:02.006204+00:00 through 2026-07-12T20:46:12.117639+00:00 |
| USFS_LCMS | https://data.fs.usda.gov/geodata/rastergateway/LCMS/ | medium | multiple timestamps, 2026-07-12T18:36:44.493010+00:00 through 2026-07-12T20:46:11.972321+00:00 |
| USFS_NLCD_TCC | https://data.fs.usda.gov/geodata/rastergateway/treecanopycover/ | high | multiple timestamps, 2026-07-12T18:36:44.514585+00:00 through 2026-07-12T20:46:11.972993+00:00 |
| COPERNICUS_S2_SR_HARMONIZED | https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED | high | multiple timestamps, 2026-07-12T20:46:07.795827+00:00 through 2026-07-12T20:46:13.163884+00:00 |
| CAL FIRE Defensible Space (PRC 4291 / AB 3074) | https://www.fire.ca.gov/dspace | (checklist, no confidence/fetched_at supplied) | — |

---

## What This Cannot See

- `tree_canopy_pct` and `lcms_class` are ~120 m block-mode/block-mean rasters, and `wildfire_annual_frequency` is resolved at census-tract level. This report cannot and does not claim to know the specific contents of the individual 5/30/100 ft defensible-space zones immediately around the structure from these inputs — only landscape/directional findings mapped onto the standard zone checklist.
- No hydrant, road-egress, evacuation route, fuel-moisture, roof, vent, or structure-material fields are available from Mireye.
- Structure-hardening advice presented above is prescriptive CAL FIRE guidance only — it is not observed evidence about this building's roof, vents, eaves, or siding.
- `ndvi_current` values are point-in-time snapshots (60-day Sentinel-2 window as of 2026-07-12) and should be treated as indicative of vegetation greenness/dryness at time of capture, not a continuous monitor.
- The ring origin used for directional sampling was the parcel centroid.
- No `gaps` or `mireye_partial_failures` were flagged in the underlying data for this property beyond the drought_category absence noted in Overall Exposure.
