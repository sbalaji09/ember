"""Thin FastAPI backend for the Ember frontend.

Runs the existing pipeline (geocode -> sampling -> mireye_client -> scoring
-> build_report_data -> optional render_report) unchanged and serves it over
one endpoint, plus the static frontend/ directory. No new business logic
lives here — this is wiring, not a second implementation.

MIREYE_TOKEN and ANTHROPIC_API_KEY are read from the server process's
environment only (never accepted from a request) and never appear in any
response body.
"""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
for path in (_REPO_ROOT, _SRC_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from geocode import geocode, GeocodeError
from mireye_client import MireyeClient, MireyeConfigError, MireyeRequestError
from sampling import sample_property
from scoring import score_property
from report import build_report_data, render_report

app = FastAPI(title="Ember")

FRONTEND_DIR = os.path.join(_REPO_ROOT, "frontend")


class AssessRequest(BaseModel):
    address: str


@app.post("/assess")
def assess(req: AssessRequest):
    address = req.address.strip()
    if not address:
        raise HTTPException(status_code=400, detail="address is required")

    try:
        client = MireyeClient()
    except MireyeConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        geocode_result = geocode(address)
    except GeocodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        sample = sample_property(client, geocode_result["lat"], geocode_result["lng"])
    except MireyeRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    sample["mireye_partial_failures"] = client.all_partial_failures
    scored = score_property(sample)
    report_data = build_report_data(address, geocode_result, sample, scored)

    prose = None
    prose_available = False
    prose_error = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            prose = render_report(report_data)
            prose_available = True
        except Exception as exc:  # noqa: BLE001 - surface any render failure to the client, don't hide it
            prose_error = str(exc)
    else:
        prose_error = (
            "ANTHROPIC_API_KEY is not set on the server. Showing the scored data view only; "
            "no LLM prose was generated for this request."
        )

    return {
        "scored_blob": report_data,
        "prose": prose,
        "prose_available": prose_available,
        "prose_error": prose_error,
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok", "mireye_token_set": bool(os.environ.get("MIREYE_TOKEN")),
            "anthropic_key_set": bool(os.environ.get("ANTHROPIC_API_KEY"))}


# Registered after /assess and /healthz so those exact routes win; this
# catch-all serves index.html and the JS/CSS assets for everything else.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
