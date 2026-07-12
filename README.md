# Ember

**A per-home wildfire hardening advisor for California properties.**

Type in a California address and get a defensible-space and structure-hardening plan grounded in federal fire, fuel, and terrain data. Every recommendation is traceable to its source.

## Why this exists

After the Tubbs, Camp, and Palisades fires, "harden your home" became standard advice. But the advice is usually generic: CAL FIRE publishes the same Zone 0/1/2 checklist for every house in the state.

What actually drives risk at a specific home is site-specific:

- Which direction the slope carries fire toward the parcel
- How much canopy and dry brush surrounds the structure
- Which side of the parcel has the heaviest fuel
- How often the surrounding area burns

Ember reads the fuel and terrain around a specific parcel from Mireye, then turns the standard checklist into a prioritized plan for that lot.

**Who it is for:** California wildland-urban interface homeowners, fire-safe councils, insurers, and mitigation contractors.

## Why Mireye

This is the core product argument:

| Alternative | Why it falls short |
| --- | --- |
| Google Maps | Has roads and satellite tiles, but not fuel load, slope, fire frequency, or parcel geometry. It cannot score defensible-space risk. |
| Generic LLM | Can confidently invent a risk level for an address, but has no grounded data or citations. That is unusable for homeowner action or insurance pricing. |
| GIS analyst | Could produce a credible assessment, but not per-home at scale and not in seconds. |

Ember fuses land cover, terrain, fire-weather context, and parcel data from one provenance-tagged source. Every line in the report carries `source`, `source_url`, `fetched_at`, and `confidence`.

That audit trail is the product. It is what makes the plan defensible to a homeowner, a fire-safe council, or an underwriter.

## Hard Design Constraint

Mireye's `tree_canopy_pct` and `lcms_class` come from roughly 120 m block-mode grids. `wildfire_annual_frequency` is census-tract resolution.

That means Ember **cannot** resolve a 5 ft vs. 30 ft vs. 100 ft defensible-space zone from those fields. Points that close together can fall in the same raster cell. Do not pretend otherwise.

Ember therefore works at two honest scales:

| Scale | What Ember does |
| --- | --- |
| Landscape scale | Samples a ring of points outward from the parcel at radii the rasters can actually resolve: about 100 m, 250 m, and 500 m. This characterizes the fuel landscape and slope/aspect gradient around the home. |
| Zone scale | Maps the standard CAL FIRE Zone 0/1/2 actions onto those directional findings. Example: "Prioritize Zone 2 fuel reduction on the northeast side, where canopy is densest and slope runs uphill toward the house." |

`ndvi_current` and `ndvi_change_5y` are Sentinel-2, roughly 10 m resolution. Use them for surrounding vegetation dryness and drying trends, not for per-zone geometry.

Being explicit about this resolution mismatch is also the "where Mireye fell short" write-up.

## Architecture

```text
address
  └─► Census Geocoder
        free, US-only, no key
        returns lat/lng

lat/lng
  └─► sampling.py
        centroid + 8 compass bearings × {100m, 250m, 500m}
        25 points total

sample points
  └─► mireye_client.py
        POST /v1/fetch
        wildfire_underwrite preset + extras
        parallel + cached

Mireye values
  └─► scoring.py
        deterministic directional threat vectors
        overall exposure band
        no LLM risk scoring

scored, cited inputs
  └─► report.py
        Claude writes readable prose from the scored numbers
        citations pass through untouched

report
  └─► CLI + optional web UI + optional MCP tool
```

**Key judgment call:** risk scoring is deterministic and transparent. The LLM never invents a risk number. Claude's job in `report.py` is only to turn scored vectors and cited Mireye values into readable, zone-organized prose.

## Data Sources

### Geocoding

Use the Census Geocoder, not Mireye:

```text
https://geocoding.geo.census.gov/geocoder/locations/onelineaddress
```

It is free, US-only, keyless, and federal.

### Mireye `/v1/fetch`

Fetch Mireye data per sampled point. Start from the `wildfire_underwrite` preset and add the fields below. Confirm the exact request body and preset membership against the live catalog before implementation.

| Group | Fields | Notes |
| --- | --- | --- |
| Core wildfire preset | `elevation`, `slope_degrees`, `lcms_class`, `tree_canopy_pct`, `ndvi_current`, `ndvi_change_5y`, `wildfire_annual_frequency` | Expected from `wildfire_underwrite`. |
| Terrain | `aspect_degrees`, `aspect_cardinal` | Aspect is approximately the downhill direction. Fire approaching from the downhill side climbs toward the house. |
| Land cover and WUI proxy | `land_use_class`, `housing_units_density_per_km2`, `nearest_urban_area_distance_m` | Use as a structure-to-structure ignition proxy. If `dist_to_wui_m` exists in the live catalog, use it and drop the proxy. |
| Fire-weather context | `design_wind_speed_mph`, `drought_category`, `days_above_32c_annual_count`, `mean_annual_dry_bulb_temperature_degc` | Context for exposure scoring. |
| Parcels | `parcel_boundary_geojson`, `parcel_area_m2`, `parcel_address` | Use for mapping and parcel-aware bearings. Expect these to be null on Regrid's free tier and degrade gracefully. |

### Fetch Strategy

You do not need every field at all 25 points.

- Fetch the full field set at the centroid.
- Fetch only fuel and terrain fields on the ring: `lcms_class`, `tree_canopy_pct`, `ndvi_current`, `slope_degrees`.
- Fire ring calls in parallel.
- Cache by rounded coordinate.
- Dedupe aggressively because nearby points may hit the same raster cell.

### Provenance Rules

Carry provenance through the entire pipeline:

- `source`
- `source_url`
- `fetched_at`
- `confidence`

Read `partial_failures` on every response. Render failures explicitly, log them, and treat them as data-gap notes. Never silently drop them.

## Scoring Model

The scoring model is deterministic, documented, and tunable. Put all weights in `config.py`.

### Per-bearing fuel score

For each of the 8 compass bearings, aggregate across ring points:

```text
fuel type weight from lcms_class
  Trees / Shrubs -> high
  Grass          -> medium
  Barren/Impervious/Water -> low

× tree_canopy_pct scaling
× dryness factor from ndvi_current
× trend flag from ndvi_change_5y
```

Lower NDVI in a vegetated class means more cured or dry fuel, which increases the score.

### Slope threat

Compute the uphill azimuth as the opposite of `aspect_degrees`.

Bearings within ±45° of "fire approaching from downhill" get a multiplier that scales with `slope_degrees`. Fire spread roughly doubles per about 10° of upslope; cite this as a rule of thumb, not as a Mireye value.

### Directional threat

```text
directional threat vector = fuel score × slope multiplier
```

Surface the top 1-2 worst approach directions.

### Overall property exposure

Calculate a banded level:

- Low
- Moderate
- High
- Very High

Use these inputs:

- `wildfire_annual_frequency` as the tract baseline
- Maximum directional threat
- WUI density
- Drought category
- Days above 32 C
- Design wind speed

Show the input drivers. Do not hide the result behind a black-box number.

## Report Output

Each report should include:

- **Header:** address, coordinates, parcel size, tract
- **Overall exposure:** exposure band and cited drivers
- **Terrain and approach:** slope magnitude, uphill direction, and worst approach vectors in plain English
- **Directional fuel findings:** where heavy or dry fuel sits relative to the home
- **Prioritized action plan:** CAL FIRE Zone 0, Zone 1, and Zone 2 actions reordered by highest-threat directions
- **Sources:** every value mapped to `source`, `source_url`, `fetched_at`, and `confidence`
- **What this cannot see:** resolution caveats stated plainly

## CAL FIRE Framework Notes

Use CAL FIRE's defensible-space zone model:

- Zone 0: 0-5 ft, ember-resistant
- Zone 1: 5-30 ft
- Zone 2: 30-100 ft

Zone 0 comes from AB 3074 and PRC 4291. Verify the current Zone 0 regulatory and effective status against CAL FIRE before shipping because the ember-resistant-zone rules were still being phased in.

Structure-hardening advice for roof, vents, and eaves is generic CAL FIRE guidance, not observed building evidence. Mireye gives building height, footprint, and class through Overture; it does not observe roof material or vent type. Do not imply the structure was inspected.

## Repository Layout

```text
ember/
  README.md              # this file
  config.py              # scoring weights, ring radii, field lists
  src/
    geocode.py           # Census geocoder
    mireye_client.py     # /v1/fetch wrapper, auth, retry, cache, partial_failures
    sampling.py          # ring generation, parcel-aware with radius fallback
    scoring.py           # deterministic threat model
    report.py            # Claude-written prose from scored/cited data
    cli.py               # ember "123 Main St, Santa Rosa, CA"
    server.py             # FastAPI backend for the frontend: POST /assess, serves frontend/
    app.py                # unimplemented stub -- superseded by server.py + frontend/
    mcp_server.py        # optional assess_wildfire_risk(address) MCP tool
  frontend/
    index.html, style.css, app.js  # map + data-viz UI -- see frontend/README.md to run it
  tests/
  demo/
    addresses.md         # the four demo homes + captured outputs
```

## Environment

```text
MIREYE_TOKEN=<bearer token>
MIREYE_BASE_URL=https://api.mireye.com
```

Never hardcode the token.

## Build Plan

1. **Confirm the API contract.** Fetch `https://docs.mireye.ai/llms.txt`, then the `/api-reference/fetch` and `/ask` pages. Lock the exact `/v1/fetch` request body, response envelope, provenance field names, and `partial_failures` shape.
2. **Verify fields.** Pull `GET /v1/meta/fields`, verify every named field still exists, and note preset membership.
3. **Run a validation spike.** Fetch the `wildfire_underwrite` preset at one known California fire-country coordinate. Confirm that `tree_canopy_pct`, `lcms_class`, `ndvi_*`, `slope_degrees`, and `wildfire_annual_frequency` come back populated. Print raw provenance.
4. **Build the data path.** Implement geocoder, Mireye client with cache/retry/partial-failure surfacing, and sampling.
5. **Implement scoring.** Add deterministic `scoring.py` with unit tests for flat vs. steep, forested vs. barren, and wet vs. cured synthetic inputs.
6. **Generate reports.** Feed Claude only the scored vectors and cited values. The system prompt must forbid inventing risk levels or sources.
7. **Ship the CLI.** Get the end-to-end CLI working first, then add optional web UI and/or MCP tool.
8. **Capture demos.** Run the three demo homes, capture outputs into `demo/`, and keep a running `LIMITATIONS.md` of every null, `partial_failures`, and resolution gap.

## Demo Homes

Pick real addresses in each location and pre-capture their reports for the 30-minute call.

| Area | Why it matters |
| --- | --- |
| Coffey Park, Santa Rosa | Flat, dense suburban WUI that still burned in Tubbs in 2017. Tests the structure-to-structure and low-slope/high-density case. |
| Canyon home above Malibu | Steep slope plus chaparral. Tests the slope-driven directional model. |
| Paradise, Butte County | Forested ridge affected by the 2018 Camp Fire. Tests canopy, tract fire frequency, and terrain together. |

## Known Limitations

Surface these directly:

- 120 m fuel rasters and tract-level fire frequency cannot resolve individual defensible-space zones.
- Ember gives landscape-and-direction guidance, then maps the standard zone checklist onto it.
- No hydrant, road-egress, evacuation, fuel-moisture, roof, vent, or structure-material fields are available.
- Structure-hardening advice is prescriptive, not observed.
- NDVI is a point-in-time snapshot; treat dryness as indicative.
- Free-tier parcels may lack geometry or zoning; fall back to a fixed radius.

## Stretch Ideas

- Let the user drop a pin instead of typing an address.
- Compare a home to a known past-fire coordinate.
- Add batch mode for a whole street, producing a fire-safe council heat map of which homes to prioritize.
