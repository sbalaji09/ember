"""POST /v1/fetch wrapper: auth, retry, coordinate-rounded cache, partial_failures surfacing.

Response shape (confirmed against the live API in the Phase 0/1 spike, not
guessed from memory):

    {
      "lat": float, "lng": float, "fetched_at": "ISO8601",
      "fields": {
        "<name>": {
          "value": ..., "unit": str|None, "source": str, "source_url": str,
          "confidence": "high"|"medium"|"low"|"unknown",
          "fetched_at": "ISO8601", "dataset_vintage": str|None,
          "ttl_seconds": int, "notes": str|None,
          "status": "ok"|"absent"|"failed", "error": str|None, "retryable": bool
        }
      },
      "partial_failures": [{"field": str, "source": str, "error": str, "retryable": bool}]
    }
"""

import os
import time

import requests

import config

RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}


class MireyeConfigError(Exception):
    pass


class MireyeRequestError(Exception):
    pass


class MireyeClient:
    def __init__(self, token=None, base_url=None):
        self.token = token or os.environ.get("MIREYE_TOKEN")
        if not self.token:
            raise MireyeConfigError(
                "MIREYE_TOKEN is not set. Export it before running Ember; "
                "never hardcode it."
            )
        self.base_url = (
            base_url or os.environ.get("MIREYE_BASE_URL", config.MIREYE_BASE_URL_DEFAULT)
        ).rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }
        )
        self._cache = {}
        # Every partial_failures entry seen this run, across all calls, so
        # callers (sampling.py, report.py) can surface a full data-gap log
        # without threading failure lists through every call site.
        self.all_partial_failures = []

    def _cache_key(self, lat, lng, fields, preset):
        precision = config.CACHE_COORD_PRECISION
        rounded_lat = round(lat, precision)
        rounded_lng = round(lng, precision)
        field_key = tuple(sorted(fields)) if fields else None
        return (rounded_lat, rounded_lng, preset, field_key)

    def fetch(self, lat, lng, fields=None, preset=None):
        """POST /v1/fetch. Returns the raw response envelope (dict).

        Caches by rounded coordinate + exact (fields, preset) request shape,
        per the README's cache/dedupe strategy. Every call's
        partial_failures (if any) is also appended to self.all_partial_failures
        tagged with the request's lat/lng so nothing gets silently dropped.
        """
        if not fields and not preset:
            raise ValueError("fetch() requires at least one of fields or preset")

        cache_key = self._cache_key(lat, lng, fields, preset)
        if cache_key in self._cache:
            return self._cache[cache_key]

        body = {"lat": lat, "lng": lng}
        if preset:
            body["preset"] = preset
        if fields:
            body["fields"] = list(fields)

        envelope = self._post_with_retry("/v1/fetch", body)

        for failure in envelope.get("partial_failures", []):
            self.all_partial_failures.append({**failure, "lat": lat, "lng": lng})

        self._cache[cache_key] = envelope
        return envelope

    def _post_with_retry(self, path, body):
        url = f"{self.base_url}{path}"
        last_exc = None
        for attempt in range(config.MIREYE_MAX_RETRIES + 1):
            try:
                resp = self._session.post(
                    url, json=body, timeout=config.MIREYE_TIMEOUT_SECONDS
                )
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < config.MIREYE_MAX_RETRIES:
                    time.sleep(config.MIREYE_RETRY_BACKOFF_SECONDS * (2**attempt))
                    continue
                raise MireyeRequestError(f"Request to {url} failed: {exc}") from exc

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code in RETRYABLE_HTTP_STATUSES and attempt < config.MIREYE_MAX_RETRIES:
                retry_after = resp.headers.get("Retry-After")
                delay = (
                    float(retry_after)
                    if retry_after
                    else config.MIREYE_RETRY_BACKOFF_SECONDS * (2**attempt)
                )
                time.sleep(delay)
                continue

            raise MireyeRequestError(
                f"POST {url} returned HTTP {resp.status_code}: {resp.text[:500]}"
            )

        raise MireyeRequestError(f"POST {url} failed after retries: {last_exc}")
