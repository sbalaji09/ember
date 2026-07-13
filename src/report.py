"""Turns already-scored, already-cited data into readable prose.

The LLM (Claude) never computes a risk number, never invents a source, and
never sees raw Mireye responses. As of this version it doesn't even see
full report_data: the deterministic parts of the report (header facts, the
exposure table, the directional-fuel table, the Sources table, the Zone
0/1/2 checklist, data-fetch failures, "what this cannot see") are assembled
directly in Python by report_format.render_report_markdown() — plain string
formatting, not LLM output, so the tables are always aligned, the Sources
list always has exactly one row per source, and the Zone checklist is never
duplicated per direction. Claude's only job is three short QUALITATIVE
narrative paragraphs (see NARRATIVE_SYSTEM_PROMPT) that describe the data
in prose without citing exact figures — it is deliberately not given the
precision to restate a number even if it wanted to.
"""

import json
import os
import re

import anthropic

import config
import cal_fire_zones
import scoring
import report_format

REPORT_MODEL = os.environ.get("EMBER_REPORT_MODEL", "claude-sonnet-5")

NARRATIVE_SYSTEM_PROMPT = """You are writing three SHORT interpretive paragraphs for a wildfire \
hardening report, from ALREADY-COMPUTED, ALREADY-CITED data. You do not compute, restate, or \
round any number — every number already appears in tables elsewhere in the report, so repeating \
exact figures here would just be redundant clutter. Write in plain, qualitative language instead: \
relative magnitude, direction, and severity words (e.g. "the steepest and most fuel-dense \
approach comes from the southwest"), never digits, percentages, or scores.

Non-negotiable rules:
- Never invent a number, risk level, fact, or exposure band not present in the JSON you're given.
- Never claim the structure (roof, vents, siding, eaves) was inspected or observed.
- Never imply resolution finer than the data supports — land-cover/canopy rasters are ~120m, \
wildfire frequency is census-tract level. Describe landscape/directional patterns only, never \
specific defensible-space zone contents.
- Do not mention any specific numeric value, percentage, or score, anywhere.
- Output EXACTLY this format and nothing else — no markdown headers, no leading/trailing \
commentary, no code fence:

===SUMMARY===
<1-2 sentences: plain-language framing of the overall exposure level and its main qualitative driver(s)>
===TERRAIN===
<2-3 sentences: slope/aspect and which approach directions are worst, described qualitatively>
===FUEL===
<2-3 sentences: what kind of vegetation surrounds the property and where it concentrates, described qualitatively>
"""


def _parse_narrative_sections(text):
    sections = {"summary": "", "terrain": "", "fuel": ""}
    pieces = re.split(r"===(SUMMARY|TERRAIN|FUEL)===", text)
    for i in range(1, len(pieces) - 1, 2):
        sections[pieces[i].lower()] = pieces[i + 1].strip()
    return sections


def _bearing_summary(bearing_result):
    return {
        "label": bearing_result["label"],
        "bearing_deg": bearing_result["bearing_deg"],
        "fuel_score": round(bearing_result["fuel_score"], 4),
        "avg_slope_degrees": bearing_result["avg_slope_degrees"],
        "slope_multiplier": round(bearing_result["slope_multiplier"], 3),
        "directional_threat": round(bearing_result["directional_threat"], 4),
        "gap_count": len(bearing_result["gaps"]),
        "gaps": bearing_result["gaps"],
        "citations": bearing_result["citations"],
    }


def build_report_data(address_input, geocode_result, sample, scored):
    centroid_envelope = sample["centroid_envelope"]

    header = {
        "input_address": address_input,
        "matched_address": geocode_result["matched_address"],
        "geocoded_lat": geocode_result["lat"],
        "geocoded_lng": geocode_result["lng"],
        "ring_origin": sample["origin"],
        "parcel_address": scoring.citation("parcel_address", centroid_envelope),
        "parcel_area_m2": scoring.citation("parcel_area_m2", centroid_envelope),
        "parcel_boundary_geojson": scoring.citation("parcel_boundary_geojson", centroid_envelope),
        "tract_geoid": scoring.citation("tract_geoid", centroid_envelope),
    }

    top_threats = [
        {
            "label": t["label"],
            "directional_threat": round(t["directional_threat"], 4),
            "fuel_score": round(t["fuel_score"], 4),
            "slope_multiplier": round(t["slope_multiplier"], 3),
            "avg_slope_degrees": t["avg_slope_degrees"],
        }
        for t in scored["top_threats"]
    ]

    terrain = {
        "aspect_degrees": scored["aspect_degrees"],
        "aspect_citation": scored["aspect_citation"],
        "uphill_azimuth": scored["uphill_azimuth"],
        "top_threats": top_threats,
        "slope_threat_window_deg": config.SLOPE_THREAT_WINDOW_DEG,
    }

    bearings = {label: _bearing_summary(result) for label, result in scored["bearings"].items()}

    zone_priority = []
    for threat in top_threats:
        zone_priority.append(
            {
                "direction": threat["label"],
                "directional_threat": threat["directional_threat"],
                "zones": cal_fire_zones.ZONES,
            }
        )

    action_plan = {
        "zone_priority_directions": zone_priority,
        "zones": cal_fire_zones.ZONES,
        "zone_0_status_caveat": cal_fire_zones.ZONE_0_STATUS_CAVEAT,
        "zone_source": cal_fire_zones.SOURCE,
        "zone_source_url": cal_fire_zones.SOURCE_URL,
        "structure_hardening_note": cal_fire_zones.STRUCTURE_HARDENING_NOTE,
        "structure_hardening_actions": cal_fire_zones.STRUCTURE_HARDENING_ACTIONS,
    }

    known_limitations = [
        "tree_canopy_pct and lcms_class are ~120m block-mode rasters; wildfire_annual_frequency "
        "is census-tract resolution. Individual 5/30/100 ft defensible-space zones cannot be "
        "resolved from them — this report works at landscape/direction scale (100m/250m/500m "
        "rings) and maps the standard zone checklist onto those directional findings.",
        "No hydrant, road-egress, evacuation, fuel-moisture, roof, vent, or structure-material "
        "fields are available from Mireye.",
        "Structure-hardening advice is prescriptive CAL FIRE guidance, not observed building "
        "evidence.",
        "ndvi_current is a point-in-time snapshot; treat dryness readings as indicative, not a "
        "continuous monitor.",
        f"Ring origin used: {sample['origin']['source']}"
        + (
            "."
            if sample["origin"]["parcel_aware"]
            else " — parcel geometry was unavailable, so the ring radiates from the geocoded "
            "point instead of a parcel centroid."
        ),
    ]

    return {
        "header": header,
        "overall": scored["overall"],
        "fuel_history_caveat": scored["fuel_history_caveat"],
        "terrain": terrain,
        "bearings": bearings,
        "action_plan": action_plan,
        "gaps": scored["gaps"],
        "mireye_partial_failures": sample.get("mireye_partial_failures", []),
        "known_limitations": known_limitations,
    }


def render_report(report_data, client=None):
    """Returns the full Markdown report: deterministic structure/tables
    assembled in Python (report_format), with three short qualitative
    narrative paragraphs from Claude slotted in. Raises if
    ANTHROPIC_API_KEY is not set — never silently skips citation data."""
    if client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. report.py needs it to render prose from the "
                "already-scored, already-cited data; never hardcode it."
            )
        client = anthropic.Anthropic(api_key=api_key)

    narrative_input = report_format.build_narrative_input(report_data)

    response = client.messages.create(
        model=REPORT_MODEL,
        max_tokens=1024,
        thinking={"type": "disabled"},
        system=NARRATIVE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(narrative_input, indent=2, default=str)}],
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()
    narrative = _parse_narrative_sections(raw_text)

    return report_format.render_report_markdown(report_data, narrative)
