"""Display-layer formatting and deterministic Markdown assembly for the
Written Report / PDF export.

Nothing here computes a risk value, a score, or a band — every number
passed in already came out of scoring.py, unrounded, via build_report_data()
in report.py. This module only decides how those existing numbers are
DISPLAYED (rounding, units, humanized timestamps) and how the report
document is STRUCTURED (one Sources table, one Zone checklist, section
order). report_data itself is never mutated; these functions read from it
and return new strings/lists.

The only non-deterministic input is `narrative` — three short qualitative
paragraphs written by Claude (see report.py) that describe the data in
prose without citing exact figures. Everything else in the assembled
Markdown is plain Python string formatting.
"""

import math
import re
from datetime import datetime, timezone

import cal_fire_zones

_SUPERSCRIPT_DIGITS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


# --- number/timestamp formatting -------------------------------------------------


def humanize_timestamp(iso_str):
    """'2026-07-12T19:07:56.785283+00:00' -> '2026-07-12 19:07 UTC'."""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
    except ValueError:
        return str(iso_str)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def humanize_timestamp_range(iso_list):
    """Collapse multiple fetch timestamps for one source into a single
    humanized point or range, e.g. '2026-07-12 20:59–22:30 UTC'."""
    valid = sorted(t for t in iso_list if t)
    if not valid:
        return "—"
    if len(valid) == 1:
        return humanize_timestamp(valid[0])

    try:
        lo = datetime.fromisoformat(str(valid[0]).replace("Z", "+00:00")).astimezone(timezone.utc)
        hi = datetime.fromisoformat(str(valid[-1]).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return humanize_timestamp(valid[0])

    if lo.date() == hi.date():
        return f"{lo.strftime('%Y-%m-%d %H:%M')}–{hi.strftime('%H:%M')} UTC"
    return f"{lo.strftime('%Y-%m-%d %H:%M UTC')} – {hi.strftime('%Y-%m-%d %H:%M UTC')}"


def _sci_parts(x):
    exponent = math.floor(math.log10(abs(x)))
    mantissa = round(x / (10**exponent), 1)
    if abs(mantissa) >= 10:  # rounding carried a digit, e.g. 9.98 -> 10.0
        mantissa = round(mantissa / 10, 1)
        exponent += 1
    return mantissa, exponent


def format_frequency(x):
    """Annualized frequencies. Very small values get scientific notation
    plus a plain-language tag rather than raw sci-notation floats."""
    if x is None:
        return "—"
    if x == 0:
        return "0 (none recorded)"
    if abs(x) < 0.001:
        mantissa, exponent = _sci_parts(x)
        sign = "⁻" if exponent < 0 else ""
        exp_digits = str(abs(exponent)).translate(_SUPERSCRIPT_DIGITS)
        return f"≈{mantissa}×10{sign}{exp_digits} (negligible / effectively zero)"
    return f"{x:.4f}"


def format_score(x, decimals=3):
    if x is None:
        return "—"
    return f"{x:.{decimals}f}"


def format_slope(x):
    if x is None:
        return "—"
    return f"{x:.1f}°"


def format_multiplier(x):
    if x is None:
        return "—"
    return f"×{x:.2f}"


def format_wind(x):
    if x is None:
        return "—"
    return f"{x:.0f} mph"


def format_count_per_year(x):
    if x is None:
        return "—"
    return f"{round(x)} days/yr"


def format_density(x):
    if x is None:
        return "—"
    return f"{round(x)} units/km²"


def format_area_m2(x):
    if x is None:
        return "—"
    return f"{x:,.0f} m²"


# --- driver / bearing / source table assembly -------------------------------------


_DRIVER_LABELS = {
    "wildfire_annual_frequency": "Wildfire annual frequency (tract)",
    "max_directional_threat": "Max directional threat",
    "housing_units_density_per_km2": "Housing unit density",
    "drought_category_ordinal": "Drought category",
    "days_above_32c_annual_count": "Days above 32°C / year",
    "design_wind_speed_mph": "Design wind speed",
}

_DRIVER_FORMATTERS = {
    "wildfire_annual_frequency": format_frequency,
    "max_directional_threat": lambda x: format_score(x, 3),
    "housing_units_density_per_km2": format_density,
    "days_above_32c_annual_count": format_count_per_year,
    "design_wind_speed_mph": format_wind,
}


def _driver_value_display(key, driver):
    if key == "drought_category_ordinal":
        cite = driver.get("citation") or {}
        if cite.get("status") != "ok" or cite.get("value") is None:
            return "absent/null — contributed 0.0"
        return str(cite["value"])
    if driver.get("raw") is None:
        return "absent/null — contributed 0.0"
    formatter = _DRIVER_FORMATTERS.get(key, lambda x: format_score(x, 4))
    return formatter(driver["raw"])


def _driver_source_display(key, driver):
    if key == "max_directional_threat":
        return "(derived — no single citation)"
    cite = driver.get("citation") or {}
    if cite.get("status") == "ok" and cite.get("source"):
        return cite["source"]
    return "missing/failed (excluded, weight renormalized)"


def build_driver_rows(report_data):
    drivers = report_data["overall"]["drivers"]
    rows = []
    for key, driver in drivers.items():
        rows.append(
            {
                "label": _DRIVER_LABELS.get(key, key),
                "value_display": _driver_value_display(key, driver),
                "weight_pct": f"{driver['weight'] * 100:.0f}%",
                "source_display": _driver_source_display(key, driver),
            }
        )
    return rows


def build_bearing_rows(report_data):
    top_labels = {t["label"] for t in report_data["terrain"]["top_threats"]}
    rows = []
    for label, b in report_data["bearings"].items():
        rows.append(
            {
                "label": label,
                "is_top": label in top_labels,
                "fuel_score_display": format_score(b["fuel_score"], 3),
                "avg_slope_display": format_slope(b["avg_slope_degrees"]),
                "slope_multiplier_display": format_multiplier(b["slope_multiplier"]),
                "directional_threat_display": format_score(b["directional_threat"], 3),
            }
        )
    # stable compass order, matching config.BEARINGS_DEG / BEARING_LABELS
    order = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    rows.sort(key=lambda r: order.index(r["label"]) if r["label"] in order else 99)
    return rows


def build_priority_line(report_data):
    top = report_data["terrain"]["top_threats"]
    if not top:
        return "No directional priority could be computed for this property."
    parts = [t["label"] for t in top]
    if len(parts) == 1:
        return f"Focus first on {parts[0]}."
    return "Focus first on " + ", then ".join(parts) + "."


def _collect_citation(bucket, citation):
    if not citation or citation.get("status") != "ok" or not citation.get("source"):
        return
    key = (citation["source"], citation.get("source_url") or "")
    entry = bucket.setdefault(
        key, {"source": citation["source"], "source_url": citation.get("source_url"), "confidences": set(), "fetched_ats": set()}
    )
    if citation.get("confidence"):
        entry["confidences"].add(citation["confidence"])
    if citation.get("fetched_at"):
        entry["fetched_ats"].add(citation["fetched_at"])


def build_sources_table(report_data):
    """One row per distinct (source, source_url) actually used in this
    report, confidences and fetched_at timestamps deduplicated and
    humanized. Mirrors the same grouping the Data & Sources tab does in
    app.js's collectCitations(), just on the Python side for the prose
    report."""
    bucket = {}

    header = report_data["header"]
    for field in ("parcel_address", "parcel_area_m2", "parcel_boundary_geojson", "tract_geoid"):
        _collect_citation(bucket, header.get(field))

    for driver in report_data["overall"]["drivers"].values():
        _collect_citation(bucket, driver.get("citation"))

    _collect_citation(bucket, report_data["terrain"].get("aspect_citation"))

    for bearing in report_data["bearings"].values():
        for citation in bearing.get("citations", []):
            _collect_citation(bucket, citation)

    caveat = report_data.get("fuel_history_caveat") or {}
    _collect_citation(bucket, caveat.get("wildfire_annual_frequency_citation"))

    rows = []
    for entry in bucket.values():
        rows.append(
            {
                "source": entry["source"],
                "source_url": entry["source_url"],
                "confidence_display": ", ".join(sorted(entry["confidences"])) or "—",
                "fetched_display": humanize_timestamp_range(entry["fetched_ats"]),
            }
        )

    # static CAL FIRE checklist source, no fetch timestamp (it's not a live fetch)
    rows.append(
        {
            "source": cal_fire_zones.SOURCE,
            "source_url": cal_fire_zones.SOURCE_URL,
            "confidence_display": "—",
            "fetched_display": "static reference, not fetched",
        }
    )

    rows.sort(key=lambda r: r["source"])
    return rows


def _bearing_fuel_types(report_data, label):
    """Distinct lcms_class values observed at one bearing's ring points —
    real qualitative material for the fuel-findings narrative, without
    handing the model a number."""
    bearing = report_data["bearings"].get(label, {})
    values = []
    for citation in bearing.get("citations", []):
        if citation.get("field") == "lcms_class" and citation.get("status") == "ok" and citation.get("value"):
            values.append(citation["value"])
    seen = []
    for v in values:
        if v not in seen:
            seen.append(v)
    return seen


def build_narrative_input(report_data):
    """Compact, qualitative-only payload for the narrative LLM call — no
    full report_data, no invitation to restate a precise number."""
    top_threats = report_data["terrain"]["top_threats"]
    return {
        "overall_band": report_data["overall"]["band"],
        "fuel_history_caveat_triggered": bool((report_data.get("fuel_history_caveat") or {}).get("triggered")),
        "top_threat_directions": [t["label"] for t in top_threats],
        "fuel_types_by_top_direction": {t["label"]: _bearing_fuel_types(report_data, t["label"]) for t in top_threats},
        "has_aspect_data": report_data["terrain"]["aspect_degrees"] is not None,
    }


# --- final Markdown assembly -------------------------------------------------


def _md_escape_cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def _table(headers, rows, right_align_cols=()):
    """right_align_cols: 0-based column indices to right-align in the
    rendered HTML (see the !TABLE_RIGHT_COLS marker handled in app.js's
    renderProseSimpleMarkdown) — used for the actually-numeric columns in
    the driver-contributions and directional-fuel tables. Text columns
    (Source, Sources-table URL/confidence/fetched) stay left-aligned."""
    lines = []
    if right_align_cols:
        lines.append("!TABLE_RIGHT_COLS[" + ",".join(str(i) for i in right_align_cols) + "]")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(_md_escape_cell(c) for c in row) + " |")
    return "\n".join(lines)


def _narrative_or_fallback(narrative, key, fallback):
    text = (narrative or {}).get(key, "").strip()
    return text if text else fallback


def render_report_markdown(report_data, narrative=None):
    header = report_data["header"]
    overall = report_data["overall"]
    caveat = report_data.get("fuel_history_caveat") or {}
    terrain = report_data["terrain"]
    action_plan = report_data["action_plan"]
    gaps = report_data.get("gaps") or []
    failures = report_data.get("mireye_partial_failures") or []

    parts = []

    # --- header block ---
    parts.append(f"# Wildfire Hardening Report — {header['matched_address']}")
    parts.append(f"!BAND[{overall['band']}]")

    fact_lines = []
    parcel_area = header.get("parcel_area_m2") or {}
    if parcel_area.get("status") == "ok":
        fact_lines.append(f"**Parcel size:** {format_area_m2(parcel_area['value'])} (source: {parcel_area['source']})")
    tract = header.get("tract_geoid") or {}
    if tract.get("status") == "ok":
        fact_lines.append(f"**Census tract:** {tract['value']} (source: {tract['source']})")
    ring_origin_label = "parcel centroid" if header["ring_origin"]["parcel_aware"] else "geocoded point (fixed-radius fallback)"
    fact_lines.append(
        f"**Coordinates:** {header['geocoded_lat']:.5f}, {header['geocoded_lng']:.5f} · Ring origin: {ring_origin_label}"
    )
    parts.append("  \n".join(fact_lines))

    # --- overall exposure ---
    parts.append("## Overall Exposure")
    parts.append(f"**Composite score:** {format_score(overall['composite'], 3)} — **Band: {overall['band']}**")
    parts.append(_narrative_or_fallback(narrative, "summary", "(interpretive summary unavailable for this report)"))
    driver_rows = build_driver_rows(report_data)
    parts.append(
        _table(
            ["Driver", "Value", "Weight", "Source"],
            [[d["label"], d["value_display"], d["weight_pct"], d["source_display"]] for d in driver_rows],
            right_align_cols=(1, 2),
        )
    )

    # --- interpretation caveat (visually distinct but calm — never styled as elevated risk) ---
    if caveat.get("triggered"):
        cite = caveat.get("wildfire_annual_frequency_citation") or {}
        parts.append("## Interpretation Caveat")
        caveat_body = [
            caveat["reason"],
            f"**Wildfire annual frequency:** {format_frequency(cite.get('value'))} (source: {cite.get('source', '—')})",
            "*This is a note on how to interpret the data above — it does not change the exposure band shown above.*",
        ]
        parts.append("!BLOCK_START[caveat]\n\n" + "\n\n".join(caveat_body) + "\n\n!BLOCK_END")

    # --- terrain and approach ---
    parts.append("## Terrain and Approach")
    aspect_line = (
        f"**Slope aspect:** {format_slope(terrain['aspect_degrees'])} · **Uphill azimuth:** {format_slope(terrain['uphill_azimuth'])}"
        if terrain["aspect_degrees"] is not None
        else "**Slope aspect:** not available for this property"
    )
    parts.append(aspect_line)
    parts.append(_narrative_or_fallback(narrative, "terrain", "(interpretive terrain narrative unavailable for this report)"))
    if terrain["top_threats"]:
        worst = ", ".join(f"{t['label']} ({format_score(t['directional_threat'], 3)})" for t in terrain["top_threats"])
        parts.append(f"**Worst approach directions:** {worst}")

    # --- directional fuel findings ---
    parts.append("## Directional Fuel Findings")
    parts.append(_narrative_or_fallback(narrative, "fuel", "(interpretive fuel narrative unavailable for this report)"))
    bearing_rows = build_bearing_rows(report_data)
    parts.append(
        _table(
            ["Direction", "Fuel Score", "Avg Slope", "Slope Multiplier", "Directional Threat"],
            [
                [
                    f"**{b['label']}**" if b["is_top"] else b["label"],
                    b["fuel_score_display"],
                    b["avg_slope_display"],
                    b["slope_multiplier_display"],
                    b["directional_threat_display"],
                ]
                for b in bearing_rows
            ],
            right_align_cols=(1, 2, 3, 4),
        )
    )

    # --- prioritized action plan (deduplicated: one checklist, not one per direction) ---
    parts.append("## Prioritized Action Plan")
    parts.append(build_priority_line(report_data))
    for zone_name, zone in action_plan["zones"].items():
        zone_lines = [f"**{zone_name} ({zone['range']})**"] + [f"- {a}" for a in zone["actions"]]
        parts.append("\n".join(zone_lines))
    parts.append(f"*{action_plan['zone_0_status_caveat']}*")
    hardening_lines = [f"**Structure Hardening (Generic CAL FIRE Guidance)**", action_plan["structure_hardening_note"]] + [
        f"- {a}" for a in action_plan["structure_hardening_actions"]
    ]
    parts.append("\n".join(hardening_lines))

    # --- sources ---
    parts.append("## Sources")
    source_rows = build_sources_table(report_data)
    parts.append(
        _table(
            ["Source", "Confidence", "Fetched"],
            [
                [f"[{s['source']}]({s['source_url']})" if s["source_url"] else s["source"], s["confidence_display"], s["fetched_display"]]
                for s in source_rows
            ],
        )
    )

    # --- data-fetch failures (always present, even when empty) ---
    parts.append("## Data-Fetch Failures")
    if failures:
        parts.append(
            _table(
                ["Field", "Source", "Error", "Retryable"],
                [[f.get("field", "—"), f.get("source", "—"), f.get("error", "—"), "yes" if f.get("retryable") else "no"] for f in failures],
            )
        )
    else:
        parts.append("None recorded for this request — every requested field returned a value or an explicit null.")

    # --- what this cannot see (distinct calm card, same treatment as the caveat) ---
    parts.append("## What This Cannot See")
    limitations = report_data.get("known_limitations") or []
    gap_note = (
        f"{len(gaps)} scoring data gap(s) were encountered (null/failed field reads) and factored in as documented above, not silently dropped."
        if gaps
        else "No scoring data gaps were encountered for this property."
    )
    limitations_body = "\n".join(f"- {item}" for item in limitations) + "\n\n" + gap_note
    parts.append("!BLOCK_START[limitations]\n\n" + limitations_body + "\n\n!BLOCK_END")

    return "\n\n".join(p for p in parts if p)
