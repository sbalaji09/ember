"""Deterministic tests for report.py's data-assembly path (build_report_data).

render_report() itself calls the live Anthropic API and has no automated
coverage (see LIMITATIONS.md) — it was verified manually against a live key.
These tests instead lock down the layer immediately upstream: the JSON blob
that gets handed to Claude. If a partial_failures entry or a data gap were
ever silently dropped before reaching that blob, the LLM would have no way
to surface it, no matter how well-worded the system prompt is. That's the
failure mode these tests exist to catch.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import config
import scoring
import report

from test_scoring import _synthetic_sample


def test_partial_failures_survive_into_report_data():
    sample = _synthetic_sample()
    synthetic_failures = [
        {
            "field": "slope_degrees",
            "source": "USGS_3DEP_COG",
            "error": "DEM read failed: Read failed. See previous exception for details.",
            "retryable": True,
            "lat": 34.2391,
            "lng": -116.9127,
        },
        {
            "field": "slope_degrees",
            "source": "USGS_3DEP_COG",
            "error": "DEM read failed: Read failed. See previous exception for details.",
            "retryable": True,
            "lat": 34.2375,
            "lng": -116.9185,
        },
    ]
    sample["mireye_partial_failures"] = synthetic_failures

    scored = scoring.score_property(sample)
    geocode_result = {"lat": sample["geocoded"]["lat"], "lng": sample["geocoded"]["lng"], "matched_address": "TEST ADDRESS"}
    report_data = report.build_report_data("test address", geocode_result, sample, scored)

    # Not dropped: the exact list survives, unfiltered, into report_data.
    assert report_data["mireye_partial_failures"] == synthetic_failures

    # Not silently summarized away: the field name and error text that would
    # let a reader (or the LLM) actually name the gap are both present in the
    # JSON payload that gets sent to the model.
    serialized = json.dumps(report_data, indent=2, default=str)
    assert "slope_degrees" in serialized
    assert "DEM read failed" in serialized
    assert "USGS_3DEP_COG" in serialized


def test_no_partial_failures_renders_as_empty_not_missing():
    sample = _synthetic_sample()
    sample["mireye_partial_failures"] = []

    scored = scoring.score_property(sample)
    geocode_result = {"lat": sample["geocoded"]["lat"], "lng": sample["geocoded"]["lng"], "matched_address": "TEST ADDRESS"}
    report_data = report.build_report_data("test address", geocode_result, sample, scored)

    # The key must exist (so the system prompt's "state explicitly" rule has
    # something to check), it just happens to be empty — never absent.
    assert "mireye_partial_failures" in report_data
    assert report_data["mireye_partial_failures"] == []


def test_scoring_gaps_also_survive_into_report_data():
    # A ring point with every fuel/terrain field missing produces gaps in
    # scoring.py; confirm those gaps reach report_data unfiltered too.
    sample = _synthetic_sample()
    sample["centroid_envelope"]["fields"]["aspect_degrees"]["status"] = "failed"
    sample["centroid_envelope"]["fields"]["aspect_degrees"]["value"] = None

    scored = scoring.score_property(sample)
    geocode_result = {"lat": sample["geocoded"]["lat"], "lng": sample["geocoded"]["lng"], "matched_address": "TEST ADDRESS"}
    report_data = report.build_report_data("test address", geocode_result, sample, scored)

    gap_fields = {g["field"] for g in report_data["gaps"]}
    assert "aspect_degrees" in gap_fields
