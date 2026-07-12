# Ember frontend

A static, dependency-free (no build step) frontend backed by a thin FastAPI
server that runs the existing Ember pipeline. One process, one command.

## Run it

From the repo root, with `MIREYE_TOKEN` (required) and `ANTHROPIC_API_KEY`
(optional — see below) exported in your shell:

```bash
export MIREYE_TOKEN=...       # required
export ANTHROPIC_API_KEY=...  # optional — see "Without an LLM key" below
python3 -m uvicorn src.server:app --reload --port 8420
```

Then open `http://127.0.0.1:8420/`. Type a California address and click
**Assess**.

Never export these into `.env` if `.env` is committed, and never put them in
any file under `frontend/` — the browser never sees either value. Both are
read from the server process's own environment only
(`src/server.py`/`src/mireye_client.py`/`src/report.py`), never accepted from
a request body or query string.

## Without an LLM key

If `ANTHROPIC_API_KEY` isn't set, `/assess` still returns the full scored
data — every panel (header, exposure band with driver breakdown,
interpretation caveat, zone checklist, sources, data-fetch failures) renders
normally. Only the "Written Report" tab shows a note explaining that no
prose was generated, instead of Claude-authored narrative text. This is the
graceful-degradation path, not an error state.

## Architecture

- `src/server.py` — FastAPI app. `GET /address-suggestions?q=...` returns
  ranked California street-address suggestions from OSM-backed providers
  (Photon first, Nominatim fallback), and `POST /assess {address}` runs the
  *existing* pipeline unchanged: `geocode` → `sample_property` →
  `score_property` → `build_report_data` → (if a key is present)
  `render_report`. Returns `{scored_blob, prose, prose_available,
  prose_error}`, where `scored_blob` is exactly what `./ember --json`
  produces. No scoring or fetching logic is reimplemented here — this file
  is wiring, not a second pipeline. Also serves `frontend/` as static files
  via `StaticFiles`, so the API and the UI are one process.
- `frontend/index.html`, `style.css`, `app.js` — vanilla JS (ES module), no
  bundler, no framework. Talks to `/address-suggestions` and `/assess` on
  the same origin. Address autocomplete is debounced, aborts superseded
  requests, caches recent queries client-side, supports loading/no-match
  states, and can be navigated with keyboard arrows + Enter. The only math it
  does locally is plotting geometry (great-circle destination points,
  mirroring `sampling.py`'s formula, so directional-threat arrows land at the
  right pixel) — every risk *value* (arrow length, arrow color, band, driver
  contributions) is read directly from `scored_blob`, never computed in the
  browser.
- Map: [Leaflet](https://leafletjs.com/) loaded from a CDN, two keyless base
  layers (Esri World Imagery satellite, default; OpenStreetMap standard).
  No API key required for either.

## Key boundary, enforced

- `MIREYE_TOKEN` and `ANTHROPIC_API_KEY` are read via `os.environ` only,
  inside `src/mireye_client.py` and `src/report.py` respectively — both
  already existing modules, unchanged for this frontend work.
- Neither value is ever included in an `/assess` response body, an error
  message, or any file under `frontend/`.
- Verified: ran the app against all four demo addresses with a live key and
  inspected every response body and the browser's network requests — no
  secret value appears anywhere client-side. See the main `LIMITATIONS.md`
  for the specific verification notes from this pass.

## Known gap found while building this

`sampling.py`'s `parcel_centroid_from_geojson` only handles GeoJSON
`Polygon` geometry, not `MultiPolygon`. When a parcel's boundary is a
`MultiPolygon` (seen live at the Latigo Canyon, Malibu demo address), the
Python backend falls back to the geocoded point for ring sampling instead of
the true parcel centroid — even though the geometry itself is present and
valid. The frontend map draws the parcel outline correctly regardless
(Leaflet's `L.geoJSON()` handles `MultiPolygon` natively), so this is
visible as a mismatch: the map shows the real parcel shape, but the ring
origin marker sits at the geocoded point next to it, not the parcel's
centroid. Not fixed as part of this frontend work — logged in
`LIMITATIONS.md` as a real gap in the existing sampling code.
