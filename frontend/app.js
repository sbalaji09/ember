// Ember frontend. No secrets live here — this file only ever talks to our
// own /assess endpoint (same origin) and renders values already present in
// the response. It never computes a risk number: the only math done in this
// file is plotting geometry (great-circle destination points, mirroring
// sampling.py's formula) so arrows land at the right pixel — the arrow's
// LENGTH and COLOR always come straight from scored_blob.bearings[...].directional_threat.

const EARTH_RADIUS_M = 6371000;

// Same calibration ceiling as config.py's max_directional_threat normalization
// range — used here only to keep the map's color/length scale consistent
// with the exposure band math, not to compute anything new.
const DIRECTIONAL_THREAT_SCALE_MAX = 1.8;

const BAND_COLORS = {
  Low: "#5b8266",
  Moderate: "#b9902c",
  High: "#c1622d",
  "Very High": "#9c3b2e",
};

const els = {
  form: document.getElementById("assess-form"),
  input: document.getElementById("address-input"),
  suggestions: document.getElementById("address-suggestions"),
  btn: document.getElementById("assess-btn"),
  empty: document.getElementById("empty-state"),
  loading: document.getElementById("loading-state"),
  error: document.getElementById("error-state"),
  results: document.getElementById("results"),
  tabData: document.getElementById("tab-data"),
  tabReport: document.getElementById("tab-report"),
  reportContent: document.getElementById("report-content"),
  exportPdfBtn: document.getElementById("export-pdf-btn"),
  legend: document.getElementById("map-legend"),
};

let map = null;
let mapLayerGroup = null;

function initMap() {
  map = L.map("map", { zoomControl: true }).setView([37.2, -119.5], 6);

  const esriSatellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      attribution:
        "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
      maxZoom: 19,
    }
  );
  const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  });

  esriSatellite.addTo(map);
  L.control.layers({ "Satellite (Esri)": esriSatellite, "Street map (OSM)": osm }, {}, { position: "topright" }).addTo(map);

  // featureGroup (not layerGroup) so we get getBounds() for auto-fit.
  mapLayerGroup = L.featureGroup().addTo(map);
}

// --- geometry (plotting only, mirrors sampling.py's destination_point) ---

function destinationPoint(lat, lng, bearingDeg, distanceM) {
  const lat1 = (lat * Math.PI) / 180;
  const lng1 = (lng * Math.PI) / 180;
  const bearing = (bearingDeg * Math.PI) / 180;
  const angDist = distanceM / EARTH_RADIUS_M;

  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(angDist) + Math.cos(lat1) * Math.sin(angDist) * Math.cos(bearing)
  );
  const lng2 =
    lng1 +
    Math.atan2(
      Math.sin(bearing) * Math.sin(angDist) * Math.cos(lat1),
      Math.cos(angDist) - Math.sin(lat1) * Math.sin(lat2)
    );

  return [(lat2 * 180) / Math.PI, (lng2 * 180) / Math.PI];
}

function clamp01(x) {
  return Math.max(0, Math.min(1, x));
}

// Interpolates blue -> gold -> orange -> red across normalized [0,1].
// Deliberately NOT green-based: green arrows disappeared against satellite
// imagery's trees/grass (the exact terrain this map exists to show). Blue
// has no natural analog in aerial photos, so even the "low" end of the
// scale stays visible. Keep in sync with --threat-* variables in style.css.
function colorForNormalizedThreat(t) {
  const stops = [
    [0.0, [47, 111, 176]], // blue
    [0.4, [212, 175, 55]], // gold
    [0.7, [214, 106, 33]], // orange
    [1.0, [176, 42, 30]], // red
  ];
  for (let i = 0; i < stops.length - 1; i++) {
    const [t0, c0] = stops[i];
    const [t1, c1] = stops[i + 1];
    if (t >= t0 && t <= t1) {
      const f = (t - t0) / (t1 - t0 || 1);
      const rgb = c0.map((v, idx) => Math.round(v + f * (c1[idx] - v)));
      return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
    }
  }
  return "rgb(156,59,46)";
}

function bandClass(band) {
  return "band-" + band.replace(/\s+/g, "-");
}

// --- map rendering ---

function renderMap(blob) {
  mapLayerGroup.clearLayers();

  const origin = blob.header.ring_origin;
  const originLatLng = [origin.lat, origin.lng];

  // Parcel outline, or a fallback marker when geometry is unavailable.
  const parcelField = blob.header.parcel_boundary_geojson;
  let parcelDrawn = false;
  if (parcelField && parcelField.status === "ok" && parcelField.value) {
    try {
      const geom = JSON.parse(parcelField.value);
      const layer = L.geoJSON(geom, {
        style: { color: "#2b2822", weight: 2, fillColor: "#f6f4ef", fillOpacity: 0.12 },
      });
      layer.addTo(mapLayerGroup);
      parcelDrawn = true;
    } catch (e) {
      parcelDrawn = false;
    }
  }
  if (!parcelDrawn) {
    L.marker(originLatLng)
      .bindPopup(
        origin.parcel_aware
          ? "Ring origin (parcel centroid)"
          : "Ring origin — parcel geometry unavailable (free-tier parcel data); using a fixed radius from the geocoded point instead."
      )
      .addTo(mapLayerGroup);
  }

  L.circleMarker(originLatLng, {
    radius: 5,
    color: "#2b2822",
    weight: 2,
    fillColor: "#fff",
    fillOpacity: 1,
  })
    .bindTooltip("Ring origin")
    .addTo(mapLayerGroup);

  // 8 directional threat arrows.
  const bearings = blob.bearings;
  const worstLabels = new Set((blob.terrain.top_threats || []).map((t) => t.label));
  const baseLenM = 120;
  const maxLenM = 420;

  Object.values(bearings).forEach((b) => {
    const norm = clamp01(b.directional_threat / DIRECTIONAL_THREAT_SCALE_MAX);
    const lenM = baseLenM + norm * (maxLenM - baseLenM);
    const color = colorForNormalizedThreat(norm);
    const isWorst = worstLabels.has(b.label);

    const tip = destinationPoint(origin.lat, origin.lng, b.bearing_deg, lenM);
    const lineWeight = isWorst ? 5 : 3;

    // White halo underneath so the arrow reads against ANY satellite
    // background (dark forest, pale dirt, pavement) — the colored line
    // alone was getting lost against similarly-toned terrain.
    L.polyline([originLatLng, tip], {
      color: "#ffffff",
      weight: lineWeight + 4,
      opacity: 0.85,
    }).addTo(mapLayerGroup);

    L.polyline([originLatLng, tip], {
      color,
      weight: lineWeight,
      opacity: isWorst ? 1 : 0.9,
    }).addTo(mapLayerGroup);

    // arrowhead: filled triangle at the tip, with a white outline for the
    // same contrast reason as the halo above.
    const headBack = destinationPoint(tip[0], tip[1], (b.bearing_deg + 180) % 360, 22);
    const left = destinationPoint(headBack[0], headBack[1], (b.bearing_deg + 90) % 360, 12);
    const right = destinationPoint(headBack[0], headBack[1], (b.bearing_deg - 90 + 360) % 360, 12);
    L.polygon([tip, left, right], {
      color: "#ffffff",
      weight: 2,
      fillColor: color,
      fillOpacity: 1,
    }).addTo(mapLayerGroup);

    L.circleMarker(originLatLng, { radius: 0, opacity: 0 }); // no-op keeps origin referenced

    const label = `${b.label} — directional threat ${b.directional_threat.toFixed(3)}${
      isWorst ? " (top threat)" : ""
    }`;
    L.polyline([originLatLng, tip], { opacity: 0 }).bindTooltip(label).addTo(mapLayerGroup);
  });

  // Uphill azimuth arrow — distinct dashed blue-gray line.
  if (blob.terrain.uphill_azimuth !== null && blob.terrain.uphill_azimuth !== undefined) {
    const tip = destinationPoint(origin.lat, origin.lng, blob.terrain.uphill_azimuth, 200);
    L.polyline([originLatLng, tip], {
      color: "#4a5b73",
      weight: 3,
      dashArray: "6 6",
      opacity: 0.9,
    })
      .bindTooltip("Uphill — fire climbs toward the house from the opposite (downhill) direction")
      .addTo(mapLayerGroup);
  }

  const bounds = mapLayerGroup.getBounds();
  if (bounds.isValid()) {
    map.fitBounds(bounds.pad(0.25));
  } else {
    map.setView(originLatLng, 15);
  }

  renderLegend();
}

function renderLegend() {
  els.legend.innerHTML = `
    <h4>Directional threat</h4>
    <div class="legend-gradient"></div>
    <div class="legend-labels"><span>lower</span><span>higher</span></div>
    <div class="legend-note">Arrow length and color both scale with each bearing's directional threat value (fuel score &times; slope multiplier). Longest/reddest = worst approach direction. Not the same scale as the overall exposure band below.</div>
    <div class="legend-uphill"><span class="legend-swatch-line"></span> Uphill (fire climbs toward house)</div>
  `;
}

// --- data panel rendering ---

// Hover/focus definitions for the Data & Sources tab. Keep this intentionally
// small: only composite or domain-specific concepts get a tooltip.
const GLOSSARY = {
  composite: "The single weighted number (0–1) combining all six drivers below into the overall exposure band. Not a probability — a relative severity score.",
  wildfire_annual_frequency: "How often wildfires are estimated to occur in this property's census tract per year, from FEMA's National Risk Index. A tract-level average, not specific to this parcel.",
  max_directional_threat: "The highest directional threat value (fuel score × slope amplification) among the 8 compass bearings sampled around the property.",
  zone_0: "0–5 ft from the structure — the 'ember-resistant zone,' highest priority for hardening.",
  zone_1: "5–30 ft from the structure — reduce and space out vegetation here.",
  zone_2: "30–100 ft from the structure — thin fuel to slow an approaching fire.",
};

function term(displayHtml, definition) {
  if (!definition) return displayHtml;
  return `<span class="term" tabindex="0">${displayHtml}<span class="term-tip" role="tooltip">${definition}</span></span>`;
}

function fmt(n, digits = 4) {
  if (n === null || n === undefined) return "—";
  if (typeof n !== "number") return String(n);
  return n.toFixed(digits).replace(/\.?0+$/, (m) => (m === "." ? "" : m)) || n.toFixed(digits);
}

function fmtFull(n) {
  if (n === null || n === undefined) return "—";
  return typeof n === "number" ? String(n) : String(n);
}

function citationSourceTag(citation) {
  if (!citation || citation.status !== "ok" || !citation.source) return "";
  return `<span class="src-tag">${citation.source}</span>`;
}

function renderHeaderCard(blob) {
  const h = blob.header;
  const parcelSize =
    h.parcel_area_m2 && h.parcel_area_m2.status === "ok"
      ? `${Number(h.parcel_area_m2.value).toLocaleString(undefined, { maximumFractionDigits: 0 })} m&sup2;`
      : null;
  const tract = h.tract_geoid && h.tract_geoid.status === "ok" ? h.tract_geoid.value : null;
  const ringOriginLabel = h.ring_origin.parcel_aware
    ? "parcel centroid"
    : "geocoded point (fixed-radius fallback)";

  return `
    <div class="card header-card">
      <div class="addr">${h.matched_address}</div>
      <div class="coords">${h.geocoded_lat.toFixed(5)}, ${h.geocoded_lng.toFixed(5)} &middot; ring origin: ${ringOriginLabel}</div>
      ${
        parcelSize
          ? `<div class="header-fact-row"><span class="header-fact-label">Parcel size</span><span class="header-fact-value">${parcelSize}${citationSourceTag(
              h.parcel_area_m2
            )}</span></div>`
          : ""
      }
      ${
        tract
          ? `<div class="header-fact-row"><span class="header-fact-label">Census tract</span><span class="header-fact-value">${tract}${citationSourceTag(
              h.tract_geoid
            )}</span></div>`
          : ""
      }
    </div>
  `;
}

function renderBandCard(blob) {
  const o = blob.overall;
  const driverLabels = {
    wildfire_annual_frequency: "Wildfire annual frequency (tract)",
    max_directional_threat: "Max directional threat",
    housing_units_density_per_km2: "Housing unit density",
    drought_category_ordinal: "Drought category",
    days_above_32c_annual_count: "Days above 32&deg;C / year",
    design_wind_speed_mph: "Design wind speed",
  };
  const driverTooltipKeys = new Set(["wildfire_annual_frequency", "max_directional_threat"]);

  const driverRows = Object.entries(o.drivers)
    .map(([key, d]) => {
      const pct = d.normalized === null ? 0 : Math.round(d.normalized * 100);
      const raw = d.raw === null ? "no data" : typeof d.raw === "number" ? fmt(d.raw, 4) : d.raw;
      const source = d.citation && d.citation.status === "ok" ? d.citation.source : null;
      const sourceHtml = source ? ` &middot; ${source}` : "";
      const label = driverLabels[key] || key;
      return `
        <div class="driver-row">
          <div class="driver-row-top">
            <span class="driver-name">${driverTooltipKeys.has(key) ? term(label, GLOSSARY[key]) : label}</span>
            <span class="driver-weight">weight ${(d.weight * 100).toFixed(0)}%</span>
          </div>
          <div class="driver-bar-track"><div class="driver-bar-fill" style="width:${pct}%"></div></div>
          <div class="driver-meta">raw: ${raw}${sourceHtml || (d.raw === null ? " &middot; missing/failed (excluded, weight renormalized)" : " &middot; computed internally, no single citation")}</div>
        </div>
      `;
    })
    .join("");

  return `
    <div class="card">
      <h3>Overall exposure</h3>
      <span class="band-badge ${bandClass(o.band)}">${o.band}</span>
      <div class="band-composite">${term("composite score", GLOSSARY.composite)} ${fmt(o.composite, 4)} &mdash; every driver below is shown, not a black box</div>
      ${driverRows}
    </div>
  `;
}

function renderCaveatCard(blob) {
  const c = blob.fuel_history_caveat;
  if (!c || !c.triggered) return "";
  const cite = c.wildfire_annual_frequency_citation;
  return `
    <div class="caveat-card">
      <h3>Interpretation caveat</h3>
      <p>${c.reason}</p>
      <div class="caveat-inline">Wildfire annual frequency: ${fmtFull(cite.value)} (source: ${cite.source})</div>
      <div class="caveat-disclaimer">This is a note on how to interpret the data above — it does not change the exposure band shown above.</div>
    </div>
  `;
}

function renderFailuresCard(blob) {
  const failures = blob.mireye_partial_failures || [];
  if (failures.length === 0) {
    return `<div class="card"><h3>Data-fetch failures</h3><div class="gap-note">None for this request — every requested field returned a value or an explicit null.</div></div>`;
  }
  const items = failures
    .map(
      (f) => `
      <div class="fail-item">
        <span class="fail-field">${f.field}</span> from ${f.source || "unknown source"} &mdash;
        <span class="fail-error">${f.error}</span>
        ${f.lat && f.lng ? `<div class="gap-note">at ${f.lat.toFixed(4)}, ${f.lng.toFixed(4)}${f.retryable ? " (retryable)" : ""}</div>` : ""}
      </div>`
    )
    .join("");
  return `
    <div class="fail-card">
      <h3>Data-fetch failures (${failures.length})</h3>
      ${items}
    </div>
  `;
}

const ZONE_GLOSSARY_KEYS = { "Zone 0": "zone_0", "Zone 1": "zone_1", "Zone 2": "zone_2" };

function renderZonesCard(blob) {
  const ap = blob.action_plan;
  const priorities = ap.zone_priority_directions
    .map((p) => {
      const zoneBlocks = Object.entries(p.zones)
        .map(
          ([zoneName, zone]) => `
        <div class="zone-block">
          <strong>${term(zoneName, GLOSSARY[ZONE_GLOSSARY_KEYS[zoneName]])} (${zone.range})</strong>
          <ul>${zone.actions.map((a) => `<li>${a}</li>`).join("")}</ul>
        </div>
      `
        )
        .join("");
      return `
        <div class="zone-priority">
          <h4>Priority: ${p.direction} &mdash; directional threat ${fmt(p.directional_threat, 3)}</h4>
          ${zoneBlocks}
        </div>
      `;
    })
    .join("");

  return `
    <div class="card">
      <h3>Prioritized action plan</h3>
      ${priorities}
      <div class="reg-note">${ap.zone_0_status_caveat}</div>
      <div class="hardening-note"><strong>Structure hardening (generic CAL FIRE guidance)</strong><br/>${ap.structure_hardening_note}<ul>${ap.structure_hardening_actions
        .map((a) => `<li>${a}</li>`)
        .join("")}</ul></div>
    </div>
  `;
}

function collectCitations(blob) {
  const bySource = new Map();
  const add = (c) => {
    if (!c || c.status !== "ok" || !c.source) return;
    const key = c.source + "|" + (c.source_url || "");
    if (!bySource.has(key)) {
      bySource.set(key, { source: c.source, source_url: c.source_url, confidences: new Set(), fetchedAts: new Set() });
    }
    const entry = bySource.get(key);
    if (c.confidence) entry.confidences.add(c.confidence);
    if (c.fetched_at) entry.fetchedAts.add(c.fetched_at);
  };

  add(blob.header.parcel_address);
  add(blob.header.parcel_area_m2);
  add(blob.header.parcel_boundary_geojson);
  add(blob.header.tract_geoid);
  Object.values(blob.overall.drivers).forEach((d) => add(d.citation));
  add(blob.terrain.aspect_citation);
  Object.values(blob.bearings).forEach((b) => (b.citations || []).forEach(add));
  if (blob.fuel_history_caveat) add(blob.fuel_history_caveat.wildfire_annual_frequency_citation);

  return Array.from(bySource.values()).sort((a, b) => a.source.localeCompare(b.source));
}

function renderSourcesCard(blob) {
  const rows = collectCitations(blob)
    .map((s) => {
      const confidences = Array.from(s.confidences)
        .map((c) => `<span class="confidence-tag">${c}</span>`)
        .join(" ");
      const fetchedAts = Array.from(s.fetchedAts);
      const fetchedDisplay =
        fetchedAts.length > 1 ? `${fetchedAts.length} timestamps (multiple sample points)` : fetchedAts[0] || "—";
      return `
        <tr>
          <td>${s.source}</td>
          <td>${s.source_url ? `<a href="${s.source_url}" target="_blank" rel="noopener">link</a>` : "—"}</td>
          <td>${confidences}</td>
          <td>${fetchedDisplay}</td>
        </tr>
      `;
    })
    .join("");

  return `
    <div class="card">
      <h3>Sources (browse the provenance)</h3>
      <table class="sources-table">
        <thead><tr><th>Source</th><th>URL</th><th>Confidence</th><th>Fetched at</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function renderLimitationsCard(blob) {
  const items = (blob.known_limitations || []).map((l) => `<li>${l}</li>`).join("");
  const gaps = blob.gaps || [];
  return `
    <div class="card">
      <h3>What this cannot see</h3>
      <ul class="limitations-list">${items}</ul>
      ${
        gaps.length
          ? `<div class="gap-note" style="margin-top:8px;">${gaps.length} scoring data gap(s) encountered (null/failed field reads) — factored in as documented, not silently dropped.</div>`
          : `<div class="gap-note" style="margin-top:8px;">No scoring data gaps for this property.</div>`
      }
    </div>
  `;
}

function renderDataPanel(blob) {
  els.tabData.innerHTML =
    renderHeaderCard(blob) +
    renderBandCard(blob) +
    renderCaveatCard(blob) +
    renderZonesCard(blob) +
    renderFailuresCard(blob) +
    renderSourcesCard(blob) +
    renderLimitationsCard(blob);
}

function renderProseSimpleMarkdown(md) {
  // Minimal, dependency-free Markdown -> HTML for the server-rendered prose.
  // Prose is trusted output from our own backend (same discipline as the
  // rest of the app — nothing here originates content, it only formats it).
  const escapeHtml = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const lines = md.split("\n");
  let html = "";
  let inTable = false;
  let inList = false;
  let pendingRightAlignCols = null; // set by !TABLE_RIGHT_COLS[...] for the next table only

  const closeList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };
  const closeTable = () => {
    if (inTable) {
      html += "</tbody></table>";
      inTable = false;
      pendingRightAlignCols = null;
    }
  };

  for (let raw of lines) {
    const line = raw;
    if (/^\s*$/.test(line)) {
      closeList();
      closeTable();
      continue;
    }
    // Deterministic band badge marker emitted by report_format.py — reuses
    // the same .band-badge/.band-* classes as the Data & Sources tab, so
    // the Written Report and PDF show the identical, already-tested badge
    // rather than the LLM trying (and inevitably sometimes failing) to
    // reproduce colored HTML through plain Markdown.
    const bandMatch = line.match(/^!BAND\[(.+)\]$/);
    if (bandMatch) {
      closeList();
      closeTable();
      const band = bandMatch[1];
      html += `<div class="report-band-block"><span class="band-badge ${bandClass(band)}">${escapeHtml(band)}</span></div>`;
      continue;
    }
    // Distinct-but-calm card wrapper for the Interpretation Caveat and What
    // This Cannot See sections — reuses the Data tab's .caveat-card (a
    // neutral parchment info card, never styled red/alarming) and a plain
    // .limitations-card. The content between START/END is still ordinary
    // Markdown (headers/lists/bold), just rendered inside the wrapping div.
    const blockStartMatch = line.match(/^!BLOCK_START\[(\w+)\]$/);
    if (blockStartMatch) {
      closeList();
      closeTable();
      const blockClass = blockStartMatch[1] === "caveat" ? "caveat-card" : "limitations-card";
      html += `<div class="${blockClass}">`;
      continue;
    }
    if (/^!BLOCK_END$/.test(line)) {
      closeList();
      closeTable();
      html += "</div>";
      continue;
    }
    if (/^#{1,3}\s+/.test(line)) {
      closeList();
      closeTable();
      const level = line.match(/^#{1,3}/)[0].length;
      html += `<h${level}>${inlineMd(line.replace(/^#{1,3}\s+/, ""))}</h${level}>`;
      continue;
    }
    // Emitted by report_format.py's _table() immediately before a table,
    // when some columns hold actual numbers (not names/URLs/timestamps) —
    // applied to the next table only, then consumed.
    const rightAlignMatch = line.match(/^!TABLE_RIGHT_COLS\[([\d,]+)\]$/);
    if (rightAlignMatch) {
      pendingRightAlignCols = new Set(rightAlignMatch[1].split(",").map(Number));
      continue;
    }
    if (/^\|/.test(line.trim())) {
      const cells = line.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      if (cells.every((c) => /^-+$/.test(c))) continue; // separator row
      const cellStyle = (i) => (pendingRightAlignCols && pendingRightAlignCols.has(i) ? ' style="text-align:right"' : "");
      if (!inTable) {
        html += "<table><thead>";
        html += "<tr>" + cells.map((c, i) => `<th${cellStyle(i)}>${inlineMd(c)}</th>`).join("") + "</tr>";
        html += "</thead><tbody>";
        inTable = true;
      } else {
        html += "<tr>" + cells.map((c, i) => `<td${cellStyle(i)}>${inlineMd(c)}</td>`).join("") + "</tr>";
      }
      continue;
    }
    closeTable();
    if (/^[-*]\s+/.test(line)) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${inlineMd(line.replace(/^[-*]\s+/, ""))}</li>`;
      continue;
    }
    closeList();
    html += `<p>${inlineMd(line)}</p>`;
  }
  closeList();
  closeTable();
  return html;

  function inlineMd(s) {
    let out = escapeHtml(s);
    out = out.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    out = out.replace(/\*(.+?)\*/g, "<em>$1</em>");
    out = out.replace(/`(.+?)`/g, "<code>$1</code>");
    // [text](url) — source names in the Sources table link to source_url.
    // Safe to allow here: url text comes from our own backend's static
    // Mireye/CAL FIRE source catalog, not user input.
    out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return out;
  }
}

function renderReportPanel(data) {
  if (!data.prose_available || !data.prose) {
    els.reportContent.innerHTML = `
      <div class="prose-note">${data.prose_error || "No written report available for this request."}</div>
      <div class="prose-note">The scored data above is complete regardless — the written report is a Claude-authored narrative summary of it, not a separate data source.</div>
    `;
    return;
  }
  els.reportContent.innerHTML = `<div class="prose-body">${renderProseSimpleMarkdown(data.prose)}</div>`;
}

// --- top-level flow ---

function showState(name) {
  els.empty.classList.toggle("hidden", name !== "empty");
  els.loading.classList.toggle("hidden", name !== "loading");
  els.error.classList.toggle("hidden", name !== "error");
  els.results.classList.toggle("hidden", name !== "results");
}

function switchTab(tabName) {
  document.querySelectorAll(".tab-btn").forEach((b) => {
    const active = b.dataset.tab === tabName;
    b.classList.toggle("active", active);
    b.setAttribute("aria-selected", active ? "true" : "false");
  });
  els.tabData.classList.toggle("hidden", tabName !== "data");
  els.tabReport.classList.toggle("hidden", tabName !== "report");
}

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// Export as PDF: switch to the report tab, then hand off to the browser's
// native print dialog ("Save as PDF" in every modern browser's print UI).
// No PDF-generation library needed — style.css's @media print rules hide
// everything except the rendered report prose.
els.exportPdfBtn.addEventListener("click", () => {
  switchTab("report");
  window.print();
});

// --- address autocomplete ---
// Uses the backend /address-suggestions endpoint so address lookup stays
// same-origin. The backend filters ranked OSM-backed provider results down
// to California street-address candidates. The final geocode for scoring still
// goes through the Census Geocoder in /assess.
const AUTOCOMPLETE_MIN_CHARS = 3;
const AUTOCOMPLETE_DEBOUNCE_MS = 180;
const AUTOCOMPLETE_CACHE_LIMIT = 40;

let autocompleteTimer = null;
let autocompleteAbortController = null;
let currentSuggestions = [];
let highlightedIndex = -1;
let activeSuggestionQuery = "";
const suggestionCache = new Map();

function escapeHtmlLite(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function isAutocompleteQueryReady(query) {
  const trimmed = query.trim();
  if (trimmed.length < AUTOCOMPLETE_MIN_CHARS) return false;

  const leadingHouseNumber = trimmed.match(/^\d+[A-Za-z]?\b/);
  if (!leadingHouseNumber) return true;
  return trimmed.length >= AUTOCOMPLETE_MIN_CHARS;
}

function autocompleteCacheKey(query) {
  return query.trim().replace(/\s+/g, " ").toLowerCase();
}

function getCachedSuggestions(query) {
  const key = autocompleteCacheKey(query);
  if (!suggestionCache.has(key)) return null;
  const value = suggestionCache.get(key);
  suggestionCache.delete(key);
  suggestionCache.set(key, value);
  return value;
}

function cacheSuggestions(query, suggestions) {
  const key = autocompleteCacheKey(query);
  if (!key) return;
  if (suggestionCache.has(key)) suggestionCache.delete(key);
  suggestionCache.set(key, suggestions);
  while (suggestionCache.size > AUTOCOMPLETE_CACHE_LIMIT) {
    suggestionCache.delete(suggestionCache.keys().next().value);
  }
}

async function fetchAddressSuggestions(query) {
  if (autocompleteAbortController) autocompleteAbortController.abort();
  autocompleteAbortController = new AbortController();

  const params = new URLSearchParams({
    q: query,
    limit: "10",
  });

  try {
    const resp = await fetch(`/address-suggestions?${params}`, {
      signal: autocompleteAbortController.signal,
      headers: { Accept: "application/json" },
    });
    if (!resp.ok) {
      console.warn(`Address autocomplete: server returned HTTP ${resp.status}`);
      return [];
    }
    const body = await resp.json();
    return body.suggestions || [];
  } catch (err) {
    if (err.name === "AbortError") return null; // superseded by a newer keystroke
    // Fail silently in the UI (no dropdown) but leave a trace for anyone
    // debugging via devtools, since this is otherwise invisible.
    console.warn("Address autocomplete: suggestion fetch failed —", err);
    return [];
  }
}

function hideSuggestions() {
  // Cancel any pending debounce/in-flight request too — otherwise a slow
  // autocomplete response can resolve after the form's already been
  // submitted and pop the dropdown back open over the results.
  clearTimeout(autocompleteTimer);
  if (autocompleteAbortController) autocompleteAbortController.abort();
  els.suggestions.classList.add("hidden");
  els.input.setAttribute("aria-expanded", "false");
  els.input.removeAttribute("aria-activedescendant");
  els.suggestions.removeAttribute("aria-busy");
  els.suggestions.innerHTML = "";
  currentSuggestions = [];
  highlightedIndex = -1;
  activeSuggestionQuery = "";
}

function updateHighlight() {
  Array.from(els.suggestions.children).forEach((el, i) => {
    const active = i === highlightedIndex;
    el.classList.toggle("highlighted", active);
    el.setAttribute("aria-selected", active ? "true" : "false");
    if (active) {
      els.input.setAttribute("aria-activedescendant", el.id);
      el.scrollIntoView({ block: "nearest" });
    }
  });
  if (highlightedIndex < 0) els.input.removeAttribute("aria-activedescendant");
}

function renderSuggestionState(kind, message) {
  currentSuggestions = [];
  highlightedIndex = -1;
  els.suggestions.innerHTML = `
    <li class="suggestion-status suggestion-status-${kind}" role="option" aria-disabled="true">
      ${kind === "loading" ? '<span class="suggestion-spinner" aria-hidden="true"></span>' : ""}
      <span>${escapeHtmlLite(message)}</span>
    </li>
  `;
  els.suggestions.classList.remove("hidden");
  els.input.setAttribute("aria-expanded", "true");
  els.input.removeAttribute("aria-activedescendant");
  els.suggestions.setAttribute("aria-busy", kind === "loading" ? "true" : "false");
}

function renderSuggestions(items) {
  currentSuggestions = items || [];
  highlightedIndex = -1;
  if (!currentSuggestions.length) {
    renderSuggestionState("empty", "No matching addresses");
    return;
  }
  els.suggestions.innerHTML = currentSuggestions
    .map(
      (item, i) => `
        <li id="address-suggestion-${i}" class="suggestion-item" data-idx="${i}" role="option" aria-selected="false">
          <span class="suggestion-main">${escapeHtmlLite(item.display || item.address)}</span>
          ${item.secondary ? `<span class="suggestion-secondary">${escapeHtmlLite(item.secondary)}</span>` : ""}
        </li>
      `
    )
    .join("");
  els.suggestions.classList.remove("hidden");
  els.input.setAttribute("aria-expanded", "true");
  els.suggestions.setAttribute("aria-busy", "false");
}

function selectSuggestion(idx) {
  const item = currentSuggestions[idx];
  if (!item) return;
  const address = item.address || item.display;
  els.input.value = address;
  hideSuggestions();
  els.input.focus();
}

els.input.addEventListener("input", () => {
  const query = els.input.value.trim();
  clearTimeout(autocompleteTimer);
  activeSuggestionQuery = query;
  if (!isAutocompleteQueryReady(query)) {
    hideSuggestions();
    return;
  }
  const cached = getCachedSuggestions(query);
  if (cached) {
    renderSuggestions(cached);
  } else {
    renderSuggestionState("loading", "Searching addresses");
  }
  autocompleteTimer = setTimeout(async () => {
    const queryAtRequest = query;
    const items = await fetchAddressSuggestions(query);
    if (items === null) return; // aborted — a newer request is already in flight
    if (autocompleteCacheKey(activeSuggestionQuery) !== autocompleteCacheKey(queryAtRequest)) return;
    cacheSuggestions(queryAtRequest, items);
    renderSuggestions(items);
  }, AUTOCOMPLETE_DEBOUNCE_MS);
});

els.input.addEventListener("keydown", (e) => {
  if (els.suggestions.classList.contains("hidden") || currentSuggestions.length === 0) return;
  if (e.key === "ArrowDown") {
    e.preventDefault();
    highlightedIndex = Math.min(highlightedIndex + 1, currentSuggestions.length - 1);
    updateHighlight();
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    highlightedIndex = Math.max(highlightedIndex - 1, 0);
    updateHighlight();
  } else if (e.key === "Enter") {
    if (highlightedIndex >= 0) {
      e.preventDefault();
      selectSuggestion(highlightedIndex);
    } else {
      hideSuggestions(); // let the normal form submit proceed with typed text
    }
  } else if (e.key === "Escape") {
    hideSuggestions();
  }
});

els.suggestions.addEventListener("click", (e) => {
  const li = e.target.closest(".suggestion-item");
  if (!li) return;
  selectSuggestion(Number(li.dataset.idx));
});

els.suggestions.addEventListener("pointermove", (e) => {
  const li = e.target.closest(".suggestion-item");
  if (!li) return;
  const idx = Number(li.dataset.idx);
  if (idx === highlightedIndex) return;
  highlightedIndex = idx;
  updateHighlight();
});

document.addEventListener("click", (e) => {
  if (!e.target.closest(".search-form")) hideSuggestions();
});

async function runAssessment(address) {
  showState("loading");
  els.btn.disabled = true;
  try {
    const resp = await fetch("/assess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (HTTP ${resp.status})`);
    }
    const data = await resp.json();
    showState("results");
    map.invalidateSize();
    renderMap(data.scored_blob);
    renderDataPanel(data.scored_blob);
    renderReportPanel(data);
    switchTab("data");
  } catch (err) {
    els.error.textContent = err.message || String(err);
    showState("error");
  } finally {
    els.btn.disabled = false;
  }
}

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  hideSuggestions();
  const address = els.input.value.trim();
  if (!address) return;
  runAssessment(address);
});

initMap();
