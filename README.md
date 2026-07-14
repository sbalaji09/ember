# Ember

**A per-home wildfire hardening advisor for California properties.**

Type in an address. Get back which side of the house the fire risk actually comes from, why, and a defensible-space plan reordered around that — not the same statewide checklist CAL FIRE hands every homeowner.

"Harden your home" advice in California is almost always generic, because most tools have no way to make it specific. What actually differs house to house is which direction the slope carries fire toward the parcel, which side has the heaviest and driest fuel, and how close the neighbors are. Ember reads that directly from federal terrain, land-cover, and fire-weather data, scores it deterministically, and turns the standard Zone 0/1/2 checklist into a plan for *that* lot — with every number traceable back to its source.

**Who it's for:** California wildland-urban interface homeowners, fire-safe councils, insurers, and mitigation contractors — anyone who needs a defensible-space assessment they can actually stand behind, not a plausible-sounding guess.

## What a report looks like

```text
Wildfire Hardening Report — 6626 SKYWAY, PARADISE, CA, 95969

  Low

Composite score: 0.181 — Band: Low

Overall exposure for this property sits at the low end of the scale, with the
main influence coming from vegetation and terrain conditions concentrated to
the west and southwest rather than from any widespread hazard.

Interpretation Caveat
  This area has a recorded wildfire history in the tract-level data, but the
  current fuel reading directly around the property is low. A low current
  fuel reading may reflect prior burn, clearing, or development rather than
  durable safety.

Worst approach directions: W (0.451), SW (0.215)

Priority: W — Zone 1 (5–30 ft): space tree canopies at least 10 ft apart;
remove ladder fuels (shrubs under trees) ...
```

Every value above — the band, the composite, the caveat, the directional scores — is deterministic and cited. The only thing an LLM writes is the paragraph of prose around them, and it's never given the freedom to compute or restate a number.

## What it does

- **Directional, not generic.** Samples a ring of points around the parcel at 100m/250m/500m in all 8 compass directions, scores fuel density and slope-driven fire spread per direction, and surfaces the worst 1–2 approach directions — then maps the CAL FIRE Zone 0/1/2 checklist onto those directions instead of printing it once per house.
- **Deterministic scoring, LLM-written prose.** Every risk number, band, and directional score comes out of a fixed, documented formula (weights live in `config.py`). Claude's only job is turning already-scored numbers into readable paragraphs — it cannot invent a risk level or a source, and it's structurally prevented from restating a number wrong.
- **An interpretation caveat that doesn't move the needle.** When a property has a real fire history but the current fuel reading around it is low, Ember flags that tension explicitly — without silently boosting the score to make the low band feel more "correct."
- **Full provenance, end to end.** Every value in a report carries its source, source URL, confidence, and fetch time, from the raw API response to the final PDF. That audit trail is the actual product: it's what makes a report defensible to a homeowner, a fire-safe council, or an underwriter.
- **CLI, web app, and PDF export.** Same pipeline, three surfaces — a terminal command for quick lookups, a map-based web app with directional threat arrows, and one-click PDF export for anything that needs to leave the browser.
- **Honest about resolution.** The underlying rasters can't resolve a 5 ft vs. 100 ft defensible-space zone, so Ember doesn't pretend they can — see [Known Limitations](#known-limitations).

## Quick start

Requires a Mireye API token. An Anthropic API key is optional — without one, you get the full scored data with no written narrative.

```bash
pip install -r requirements.txt

export MIREYE_TOKEN=<your token>
export ANTHROPIC_API_KEY=<your key>   # optional — enables the written report
```

**Command line:**

```bash
./ember "123 Main St, Santa Rosa, CA"
./ember --json "123 Main St, Santa Rosa, CA"   # raw scored data, no LLM call
```

**Web app** (map with directional threat arrows, sourced data browser, PDF export):

```bash
python3 -m uvicorn src.server:app --reload --port 8420
```

Then open `http://127.0.0.1:8420/`. See [`frontend/README.md`](frontend/README.md) for details.

## How it works

Ember fuses land cover, terrain, fire-weather, and parcel data from Mireye — one provenance-tagged source, rather than stitching together several APIs with no shared audit trail. An address resolves to coordinates via the (free, federal) Census Geocoder; a ring of 25 points around the parcel gets sampled from Mireye; a deterministic model turns those readings into per-direction threat scores and an overall exposure band; and Claude writes the narrative around numbers it never touches directly.

| Alternative | Why it falls short |
| --- | --- |
| Google Maps | Roads and satellite tiles, but no fuel load, slope, fire frequency, or parcel geometry — nothing to score defensible-space risk from. |
| Generic LLM | Will confidently invent a risk level for an address with no grounding or citations. Unusable for homeowner action or insurance pricing. |
| GIS analyst | Could produce a credible assessment, but not per-home, at scale, in seconds. |

## Data it's grounded in

- **Geocoding:** the [Census Geocoder](https://geocoding.geo.census.gov/geocoder/locations/onelineaddress) — free, US-only, keyless.
- **Terrain & fuel:** slope, aspect, elevation, land-cover class, tree canopy percent, and NDVI (current + 5-year trend), sampled at the parcel centroid and around it.
- **Fire & weather context:** tract-level wildfire frequency, drought category, design wind speed, and extreme-heat day counts.
- **Parcel data:** boundary geometry, area, and address, used to sample from the real parcel centroid when available (falling back to a fixed radius around the geocoded point otherwise).

Every one of those fields carries its own source, URL, confidence level, and fetch timestamp, browsable in full from the web app's Sources tab.

## Known limitations

Stated plainly, not buried:

- `tree_canopy_pct` and `lcms_class` are ~120m rasters; `wildfire_annual_frequency` is census-tract resolution. Neither can resolve an individual 5/30/100 ft defensible-space zone — Ember works at landscape/direction scale and maps the standard checklist onto that, not the other way around.
- No hydrant, road-egress, evacuation, fuel-moisture, roof, vent, or structure-material data is available. Structure-hardening advice is prescriptive CAL FIRE guidance, not an observation of the actual building.
- Tract-level wildfire frequency can be quietly disconnected from a location's real history — a known, documented case exists in `LIMITATIONS.md`.
- NDVI is a point-in-time snapshot on a rolling window, so re-running the same address later can shift the exact numbers slightly, even though the underlying conditions haven't changed. The band is stable; the third decimal place isn't a fixed reference value.
- Free-tier parcel data can lack geometry; Ember falls back to a fixed radius around the geocoded point when that happens.

For the full, ongoing record of every null, data gap, and resolution caveat encountered — including the case where tract-level fire frequency didn't reflect a well-documented historical fire — see [`LIMITATIONS.md`](LIMITATIONS.md).

## Repository layout

```text
ember/
  config.py              # scoring weights, ring radii, field lists — the whole model in one place
  src/
    geocode.py            # Census geocoder
    mireye_client.py       # /v1/fetch wrapper: auth, retry, cache, partial_failures
    sampling.py            # ring generation, parcel-aware with radius fallback
    scoring.py              # deterministic directional threat model
    report_format.py       # deterministic report structure/number formatting
    report.py              # Claude-written narrative, slotted into that structure
    cli.py                  # ember "123 Main St, Santa Rosa, CA"
    server.py               # FastAPI backend for the web app
    mcp_server.py           # assess_wildfire_risk(address) MCP tool (stub)
  frontend/                # map + data-viz web app — see frontend/README.md
  tests/
  demo/
    addresses.md            # captured example reports across four real properties
```

## Further reading

- [`LIMITATIONS.md`](LIMITATIONS.md) — the full, honest record of every data gap, calibration decision, and bug found along the way.
- [`demo/addresses.md`](demo/addresses.md) — four real captured reports (a flat suburban WUI that burned in the Tubbs Fire, a steep Malibu canyon, Paradise, and Big Bear Lake), each annotated with what it demonstrates.
- [`frontend/README.md`](frontend/README.md) — running and developing the web app.
