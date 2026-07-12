# Wildfire Hardening Report: 3000 Latigo Canyon Rd, Malibu, CA

**Matched Address:** 3000 LATIGO CANYON RD, MALIBU, CA, 90265

- Parcel Area: 11,326.02 m² (source: REGRID)
- Census Tract: 06037800410 (source: CENSUS_GEOCODING)

---

## Overall Exposure

**Composite Score:** 0.3209 — **Band: Moderate**

This composite is derived from six weighted drivers:

| Driver | Raw Value | Normalized | Weight | Source |
|---|---|---|---|---|
| Wildfire annual frequency | 0.01267 | 0.2534 | 0.30 | FEMA_NRI |
| Max directional threat | 1.1474 | 0.6374 | 0.30 | (derived, no citation) |
| Housing unit density (per km²) | 2.544 | 0.0013 | 0.10 | CENSUS_TIGERWEB |
| Drought category ordinal | 0 (value absent) | 0.0 | 0.10 | USDM_CURRENT |
| Days above 32°C (annual count) | 25 | 0.2083 | 0.10 | NOAA_NCEI_NCLIMGRID_DAILY |
| Design wind speed (mph) | 103.0 | 0.3273 | 0.10 | NOAA_ASCE_WIND_VECTORS |

No gaps were flagged in the overall composite calculation, though note the drought category value itself is marked **absent** in its underlying citation (ordinal defaulted to 0 for scoring purposes).

---

## Terrain and Approach

- **Aspect:** 237.94° (source: USGS_3DEP_COG)
- **Uphill azimuth:** 57.94°
- **Slope-threat window:** 45°

The two highest-threat directions identified are:

| Direction | Directional Threat | Fuel Score | Slope Multiplier | Avg. Slope (°) |
|---|---|---|---|---|
| SW | 1.1474 | 0.2868 | 4.0 | 30.84 |
| W | 1.0875 | 0.2719 | 4.0 | 22.97 |

Both top-threat directions carry an elevated slope multiplier (4.0), indicating steep upslope alignment toward the structure from these bearings — this is the dominant factor pushing their directional threat scores above the other six compass bearings.

---

## Directional Fuel Findings

The following reflects landscape-scale fuel and terrain conditions by compass direction, drawn from ~120m block-mode/block-mean rasters (USFS LCMS, USFS/MRLC NLCD TCC) and point-in-time NDVI (Copernicus Sentinel-2), sampled at multiple distances along each bearing. These describe general vegetation/terrain character in each direction — not the specific contents of any 5/30/100 ft zone.

| Direction | Fuel Score | Directional Threat | Avg. Slope (°) | Slope Multiplier | Dominant LCMS Class (sampled points) |
|---|---|---|---|---|---|
| N | 0.2702 | 0.2702 | 23.18 | 1.0 | Trees |
| NE | 0.2593 | 0.2593 | 18.12 | 1.0 | Trees / Grass-Forb-Herb |
| E | 0.2618 | 0.2618 | 21.96 | 1.0 | Trees |
| SE | 0.3368 | 0.3368 | 24.87 | 1.0 | Trees |
| **S** | **0.3402** | **0.3402** | 24.13 | 1.0 | Trees |
| **SW** | 0.2868 | **1.1474** | 30.84 | **4.0** | Trees |
| **W** | 0.2719 | **1.0875** | 22.97 | **4.0** | Trees |
| NW | 0.2736 | 0.2736 | 31.20 | 1.0 | Trees |

Tree canopy cover percentages sampled across directions ranged roughly from 8% (N, far sample point) to 42% (E, far sample point), reflecting patchy tree cover typical of this landscape at ~120m resolution. NDVI snapshots (S2 SR, 60-day window ending 2026-07-12) ranged from approximately 0.33 to 0.78 across sampled points, indicating mixed vegetation vigor/moisture at the time of the satellite pass — this is a point-in-time reading, not a continuous fuel-moisture monitor.

South (S) and Southeast (SE) show the highest raw fuel scores (0.3402 and 0.3368) among all directions, but their slope multipliers remain at baseline (1.0), keeping their directional threat equal to fuel score. SW and W combine moderate fuel scores with a 4.0 slope multiplier, making them the two directions of greatest overall concern.

---

## Prioritized Action Plan

Directional threat is highest from **SW (1.1474)** and **W (1.0875)**. The standard CAL FIRE defensible-space zone checklist (PRC 4291 / AB 3074) is mapped onto these priority directions below.

### Priority Direction: SW (directional threat 1.1474)

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

### Priority Direction: W (directional threat 1.0875)

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

*(Zone checklist source: CAL FIRE Defensible Space, PRC 4291 / AB 3074 — https://www.fire.ca.gov/dspace)*

### Generic Structure Hardening Guidance

The following is generic CAL FIRE prescriptive advice and is **not** based on any inspection or observation of this structure. Mireye provides building height, footprint, and class via Overture, but does not observe roof material, vent type, or siding.

- Class A fire-rated roofing, with no gaps or damaged sections.
- 1/8-inch ember- and flame-resistant mesh screens on all attic, foundation, and soffit vents.
- Enclosed eaves; avoid open-eave construction where possible.
- Dual-pane or tempered glass windows to resist radiant heat cracking.
- Non-combustible or ignition-resistant siding within 6 inches of grade.

---

## Sources

| Source | URL | Confidence | Fetched At (example timestamp(s)) |
|---|---|---|---|
| REGRID | https://app.regrid.com/api/v2/parcels/point | high | 2026-07-12T18:36:45.232149+00:00 |
| CENSUS_GEOCODING | https://geocoding.geo.census.gov/geocoder/geographies/coordinates | high | 2026-07-12T18:36:44.847995+00:00 |
| FEMA_NRI | https://hazards.fema.gov/nri/ | medium | 2026-07-12T18:36:44.534503+00:00 |
| CENSUS_TIGERWEB | https://tigerweb.geo.census.gov/arcgisweb/ | medium | 2026-07-12T18:36:44.859591+00:00 |
| USDM_CURRENT | https://droughtmonitor.unl.edu/ | high | 2026-07-12T18:36:44.472194+00:00 |
| NOAA_NCEI_NCLIMGRID_DAILY | https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily | medium | 2026-07-12T18:36:47.585194+00:00 |
| NOAA_ASCE_WIND_VECTORS | https://services2.arcgis.com/C8EMgrsFcRFL6LrL/arcgis/rest/services/ASCE_Wind_Vectors/FeatureServer | medium | 2026-07-12T18:36:44.516740+00:00 |
| USGS_3DEP_COG | https://www.usgs.gov/3d-elevation-program | medium | multiple, e.g. 2026-07-12T18:36:45.014818+00:00 through 2026-07-12T18:36:55.174883+00:00 |
| USFS_LCMS | https://data.fs.usda.gov/geodata/rastergateway/LCMS/ | medium | multiple, e.g. 2026-07-12T18:36:49.719008+00:00 through 2026-07-12T19:08:06.394304+00:00 |
| USFS_NLCD_TCC | https://data.fs.usda.gov/geodata/rastergateway/treecanopycover/ | high | multiple, e.g. 2026-07-12T18:36:49.719693+00:00 through 2026-07-12T18:36:55.145656+00:00 |
| COPERNICUS_S2_SR_HARMONIZED | https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED | high | multiple, e.g. 2026-07-12T18:36:51.857859+00:00 through 2026-07-12T18:36:57.532316+00:00 |
| CAL FIRE Defensible Space (PRC 4291 / AB 3074) | https://www.fire.ca.gov/dspace | — | — |

---

## What This Cannot See

- **tree_canopy_pct** and **lcms_class** are ~120m block-mode/block-mean rasters, and **wildfire_annual_frequency** is resolved at census-tract level. Individual 5/30/100 ft defensible-space zone contents cannot be resolved from these inputs — this report works at landscape/directional scale and maps the standard CAL FIRE zone checklist onto those directional findings, not onto observed on-the-ground zone conditions.
- No hydrant, road-egress, evacuation route, fuel-moisture, roof, vent, or structure-material fields are available from Mireye for this property.
- Structure-hardening advice provided above is prescriptive CAL FIRE guidance only — it does not reflect any inspection or observation of this building's roof, vents, eaves, or siding.
- **ndvi_current** values are point-in-time snapshots (S2 SR, 60-day window ending 2026-07-12) and should be treated as indicative of vegetation condition at that moment, not a continuous fuel-moisture monitor.
- The **parcel_address** field was absent/unresolved in the underlying data (REGRID), and no parcel geometry was available. The analysis ring for directional/terrain findings therefore radiates from the geocoded point (**geocoded_point_fixed_radius_fallback**), not from a parcel centroid.
- The **drought_category** value underlying the "drought category ordinal" driver in the Overall Exposure composite is marked **absent** in its source citation (USDM_CURRENT); it was scored as ordinal 0 by default, not from an observed current drought level.
- The **max_directional_threat** driver in the Overall Exposure composite has no citation entry — it is a derived quantity from the directional/terrain analysis rather than a direct external data source.
