"""ember "123 Main St, Santa Rosa, CA" """

import argparse
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
for path in (_REPO_ROOT, _SRC_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from geocode import geocode, GeocodeError
from mireye_client import MireyeClient, MireyeConfigError, MireyeRequestError
from sampling import sample_property
from scoring import score_property
from report import build_report_data, render_report


def main():
    parser = argparse.ArgumentParser(prog="ember", description="Per-home wildfire hardening advisor")
    parser.add_argument("address", help='e.g. "123 Main St, Santa Rosa, CA"')
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the raw scored/cited report data as JSON instead of rendering prose with Claude",
    )
    args = parser.parse_args()

    try:
        client = MireyeClient()
    except MireyeConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        geocode_result = geocode(args.address)
    except GeocodeError as exc:
        print(f"Geocoding failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Matched: {geocode_result['matched_address']} "
        f"({geocode_result['lat']}, {geocode_result['lng']})",
        file=sys.stderr,
    )

    try:
        sample = sample_property(client, geocode_result["lat"], geocode_result["lng"])
    except MireyeRequestError as exc:
        print(f"Mireye fetch failed: {exc}", file=sys.stderr)
        sys.exit(1)

    sample["mireye_partial_failures"] = client.all_partial_failures
    if client.all_partial_failures:
        print(
            f"Warning: {len(client.all_partial_failures)} Mireye partial_failures "
            "encountered — see the report's gaps/Sources section.",
            file=sys.stderr,
        )

    scored = score_property(sample)
    report_data = build_report_data(args.address, geocode_result, sample, scored)

    if args.json:
        print(json.dumps(report_data, indent=2, default=str))
        return

    try:
        report_text = render_report(report_data)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(report_text)


if __name__ == "__main__":
    main()
