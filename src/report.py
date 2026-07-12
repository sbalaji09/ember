"""Turns already-scored, already-cited data into readable prose.

The LLM (Claude) never computes a risk number, never invents a source, and
never sees raw Mireye responses — only the structured, deterministic output
of scoring.py plus a static CAL FIRE checklist. Its only job is prose.
"""

import json
import os

import anthropic

import config
import cal_fire_zones
import scoring

REPORT_MODEL = os.environ.get("EMBER_REPORT_MODEL", "claude-sonnet-5")

SYSTEM_PROMPT = """You are a technical writer producing a wildfire hardening report for one \
California home. You are given a JSON object containing ALREADY-COMPUTED, ALREADY-CITED data: \
deterministic risk scores, threat directions, an exposure band, per-value provenance \
(source/source_url/fetched_at/confidence), explicit data gaps, and a static CAL FIRE \
defensible-space checklist.

Non-negotiable rules:
- Never invent, estimate, guess, or adjust any number, risk level, or exposure band. Use only \
the values given in the JSON.
- Never invent or alter a source, source_url, fetched_at, or confidence value. If you state a \
fact derived from Mireye data, it must trace to a citation in the JSON.
- If a value is marked as a gap, null, or failed, say so explicitly in the relevant section. \
Never silently omit or paper over a data gap.
- Never imply the structure (roof, vents, siding, eaves) was inspected or observed. Structure- \
hardening guidance is generic CAL FIRE prescriptive advice, not an observation of this building.
- Never resolve or imply resolution finer than the data supports: tree_canopy_pct and lcms_class \
are ~120m rasters, wildfire_annual_frequency is census-tract level. Do not claim to know \
individual 5/30/100 ft zone contents from them — only landscape/directional findings mapped onto \
the standard zone checklist.
- Output clean Markdown with exactly these sections, in this order: \
Header, Overall Exposure, Terrain and Approach, Directional Fuel Findings, \
Prioritized Action Plan, Sources, What This Cannot See.
- In Sources, list every distinct (source, source_url) pair actually used, each with its \
confidence level(s) and fetched_at timestamp(s) as given.
- Do not add sections, disclaimers, or content beyond what the data supports.
"""


def _bearing_summary(bearing_result):
    return {
        "label": bearing_result["label"],
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
        "terrain": terrain,
        "bearings": bearings,
        "action_plan": action_plan,
        "gaps": scored["gaps"],
        "mireye_partial_failures": sample.get("mireye_partial_failures", []),
        "known_limitations": known_limitations,
    }


def render_report(report_data, client=None):
    """Calls Claude to render report_data into Markdown prose. Raises if
    ANTHROPIC_API_KEY is not set — never silently skips citation data."""
    if client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. report.py needs it to render prose from the "
                "already-scored, already-cited data; never hardcode it."
            )
        client = anthropic.Anthropic(api_key=api_key)

    user_content = (
        "Render this report data as Markdown, following the system prompt rules exactly:\n\n"
        + json.dumps(report_data, indent=2, default=str)
    )

    response = client.messages.create(
        model=REPORT_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    return "".join(block.text for block in response.content if block.type == "text")
