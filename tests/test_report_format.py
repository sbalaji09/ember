"""Tests for the display-formatting/assembly layer (report_format.py).

These are deterministic and hit no network — they exercise exactly the
presentation bugs the formatting layer exists to fix: broken Sources
rows, raw-microsecond timestamps, scientific-notation frequencies, and a
duplicated Zone 0/1/2 checklist. Also locks down the "view layer only"
discipline: report_data must come out of every formatting call bit-for-bit
identical to how it went in.
"""

import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import scoring
import report
import report_format

from test_scoring import _synthetic_sample


def _sample_report_data():
    sample = _synthetic_sample()
    scored = scoring.score_property(sample)
    geocode_result = {"lat": sample["geocoded"]["lat"], "lng": sample["geocoded"]["lng"], "matched_address": "TEST ADDRESS, CA"}
    return report.build_report_data("test address", geocode_result, sample, scored)


# --- number/timestamp formatting ---


def test_format_frequency_tiny_value_uses_scientific_notation_with_plain_language_tag():
    result = report_format.format_frequency(7.9999999798e-06)
    assert result == "≈8.0×10⁻⁶ (negligible / effectively zero)"


def test_format_frequency_normal_value_stays_plain_decimal():
    assert report_format.format_frequency(0.0013979252442599456) == "0.0014"
    assert "×10" not in report_format.format_frequency(0.0127)


def test_format_frequency_none_and_zero():
    assert report_format.format_frequency(None) == "—"
    assert report_format.format_frequency(0) == "0 (none recorded)"


def test_format_score_rounds_to_requested_decimals():
    assert report_format.format_score(0.44801937426201444, 3) == "0.448"
    assert report_format.format_score(None, 3) == "—"


def test_format_slope_and_multiplier():
    assert report_format.format_slope(7.193442145983378) == "7.2°"
    assert report_format.format_multiplier(1.6458) == "×1.65"


def test_humanize_timestamp_drops_microseconds_and_offset_noise():
    assert report_format.humanize_timestamp("2026-07-12T19:07:56.785283+00:00") == "2026-07-12 19:07 UTC"


def test_humanize_timestamp_range_same_day_collapses_to_short_range():
    result = report_format.humanize_timestamp_range(
        ["2026-07-12T20:59:10.000000+00:00", "2026-07-12T22:30:45.123456+00:00"]
    )
    assert result == "2026-07-12 20:59–22:30 UTC"


def test_humanize_timestamp_range_single_value():
    result = report_format.humanize_timestamp_range(["2026-07-12T19:07:56.785283+00:00"])
    assert result == "2026-07-12 19:07 UTC"


def test_humanize_timestamp_range_empty():
    assert report_format.humanize_timestamp_range([]) == "—"


# --- sources table: one row per source, not one per citation ---


def _citation(source, source_url, confidence, fetched_at, value="x"):
    return {"status": "ok", "source": source, "source_url": source_url, "confidence": confidence, "fetched_at": fetched_at, "value": value}


def test_sources_table_collapses_multiple_citations_from_same_source_into_one_row():
    # Mirrors the real REGRID case: parcel_address/parcel_area_m2/
    # parcel_boundary_geojson are three separate citations from the same
    # source, fetched a few hundred milliseconds apart.
    report_data = _sample_report_data()
    report_data["header"]["parcel_address"] = _citation(
        "REGRID", "https://app.regrid.com/api/v2/parcels/point", "medium", "2026-07-12T19:07:57.571600+00:00"
    )
    report_data["header"]["parcel_area_m2"] = _citation(
        "REGRID", "https://app.regrid.com/api/v2/parcels/point", "medium", "2026-07-12T19:07:57.571406+00:00"
    )
    report_data["header"]["parcel_boundary_geojson"] = _citation(
        "REGRID", "https://app.regrid.com/api/v2/parcels/point", "high", "2026-07-12T19:07:58.100000+00:00"
    )

    rows = report_format.build_sources_table(report_data)
    sources = [r["source"] for r in rows]
    assert len(sources) == len(set(sources)), f"duplicate source rows: {sources}"

    regrid_rows = [r for r in rows if r["source"] == "REGRID"]
    assert len(regrid_rows) == 1
    # both confidence levels seen, both timestamps collapsed into one range
    assert regrid_rows[0]["confidence_display"] == "high, medium"
    assert regrid_rows[0]["fetched_display"] == "2026-07-12 19:07–19:07 UTC"


def test_sources_table_timestamps_are_humanized_not_raw_iso():
    report_data = _sample_report_data()
    rows = report_format.build_sources_table(report_data)
    for row in rows:
        fetched = row["fetched_display"]
        assert "." not in fetched  # no microseconds
        assert "+00:00" not in fetched  # no raw UTC offset noise


# --- action plan: single checklist, not one per priority direction ---


def test_action_plan_zone_checklist_appears_exactly_once():
    import cal_fire_zones

    report_data = _sample_report_data()
    md = report_format.render_report_markdown(report_data, narrative=None)

    # The checklist HEADING for each zone appears once as a markdown bold
    # line ("**Zone 0 (0-5 ft ...)**"), not once per priority direction.
    # (cal_fire_zones.ZONE_0_STATUS_CAVEAT separately also happens to start
    # with the words "Zone 0" as prose, which is expected and fine — this
    # checks the actual checklist heading/content, not that substring.)
    zone_0_heading = f"**Zone 0 ({cal_fire_zones.ZONES['Zone 0']['range']})**"
    assert md.count(zone_0_heading) == 1

    # A specific action line from the checklist must also appear exactly
    # once — this is the concrete "printed in full twice" bug from the
    # report: with two top-threat directions, the old LLM-authored version
    # repeated every action bullet under each direction's heading.
    sample_action = cal_fire_zones.ZONES["Zone 0"]["actions"][0]
    assert md.count(sample_action) == 1

    assert "Focus first on" in md


# --- band badge marker ---


def test_render_includes_band_marker_matching_computed_band():
    report_data = _sample_report_data()
    md = report_format.render_report_markdown(report_data, narrative=None)
    assert f"!BAND[{report_data['overall']['band']}]" in md


# --- narrative fallback: missing/empty narrative doesn't crash or silently vanish ---


def test_render_with_no_narrative_shows_explicit_fallback_not_blank():
    report_data = _sample_report_data()
    md = report_format.render_report_markdown(report_data, narrative=None)
    assert "unavailable for this report" in md


def test_render_with_narrative_uses_provided_text_verbatim():
    report_data = _sample_report_data()
    narrative = {"summary": "SUMMARY TEXT", "terrain": "TERRAIN TEXT", "fuel": "FUEL TEXT"}
    md = report_format.render_report_markdown(report_data, narrative)
    assert "SUMMARY TEXT" in md
    assert "TERRAIN TEXT" in md
    assert "FUEL TEXT" in md


# --- discipline: formatting never mutates or loses precision from report_data ---


def test_formatting_layer_does_not_mutate_report_data():
    report_data = _sample_report_data()
    before = copy.deepcopy(report_data)

    report_format.build_driver_rows(report_data)
    report_format.build_bearing_rows(report_data)
    report_format.build_sources_table(report_data)
    report_format.build_priority_line(report_data)
    report_format.build_narrative_input(report_data)
    report_format.render_report_markdown(report_data, narrative={"summary": "x", "terrain": "y", "fuel": "z"})

    assert report_data == before


def test_json_dump_of_report_data_retains_full_precision_after_formatting_layer_runs():
    """The whole point of a VIEW-layer formatter: ./ember --json must be
    byte-for-byte unaffected by anything report_format.py does."""
    report_data = _sample_report_data()
    before_json = json.dumps(report_data, indent=2, default=str, sort_keys=True)

    report_format.render_report_markdown(report_data, narrative={"summary": "x", "terrain": "y", "fuel": "z"})

    after_json = json.dumps(report_data, indent=2, default=str, sort_keys=True)
    assert before_json == after_json
    # spot-check full precision survived (not rounded to the display's 4 decimals)
    assert "0.01" in before_json  # synthetic fixture's wildfire_annual_frequency raw value


def test_narrative_section_parsing():
    text = "===SUMMARY===\nfoo\n===TERRAIN===\nbar\n===FUEL===\nbaz"
    sections = report._parse_narrative_sections(text)
    assert sections == {"summary": "foo", "terrain": "bar", "fuel": "baz"}


def test_narrative_section_parsing_handles_garbage_gracefully():
    sections = report._parse_narrative_sections("not the expected format at all")
    assert sections == {"summary": "", "terrain": "", "fuel": ""}
