"""NTRIP caster sourcetable proxy.

Fetches the plain-text sourcetable from the FUNDCORSRD NTRIP caster and
parses out the ``STR;`` (station) lines into a simple list of dicts the
frontend map can consume directly, without exposing the caster to the
browser.

A short in-memory cache absorbs repeated requests (e.g. a map polling this
endpoint every few seconds) without hammering the caster on every request,
and falls back to the last known-good station list (flagged as stale) if a
live fetch fails.
"""
import logging
import time
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Address of the live NTRIP caster sourcetable. Hardcoded for now; could be
# moved to an environment variable (e.g. NTRIP_CASTER_URL) in a later
# hardening pass so it can be changed without a code deploy.
NTRIP_URL = "http://190.166.228.161:2103"

# How long a successful fetch stays "fresh" before we try the caster again.
CACHE_TTL_SECONDS = 45

# Module-level in-memory cache of the last known stations. Lives for the
# lifetime of the process/worker; there is no cross-process/shared cache.
_cache = {
    "stations": [],      # list[dict]: last known-good stations list
    "fetched_at": None,  # float (time.time()) of the last successful fetch, or None
    "updated_at": None,  # ISO 8601 string of the last successful fetch, or None
    "stale": True,        # whether "stations" reflects a successful recent fetch
}


def _parse_sourcetable(text):
    """Parse raw NTRIP sourcetable text into a list of station dicts.

    Only lines beginning with the literal marker ``STR;`` are station
    entries; everything else (``CAS;``, ``NET;``, ``ENDSOURCETABLE``, blank
    lines, etc.) is ignored. Per the standard NTRIP sourcetable format,
    after splitting a STR line on ``;``:

        index 0  -> literal "STR" marker
        index 1  -> mount point / station name
        index 2  -> location / city
        index 9  -> latitude
        index 10 -> longitude

    Malformed lines (too few fields, non-numeric lat/lon) are silently
    skipped rather than raising, so one bad line doesn't take down the
    whole sourcetable.
    """
    stations = []
    for line in text.splitlines():
        if not line.startswith("STR;"):
            continue

        fields = line.split(";")
        if len(fields) < 11:
            continue

        try:
            lat = float(fields[9])
            lon = float(fields[10])
        except (ValueError, IndexError):
            continue

        stations.append({
            "name": fields[1],
            "location": fields[2],
            "lat": lat,
            "lon": lon,
        })

    return stations


def get_stations():
    """Return the current NTRIP station list, using a short-lived cache.

    Returns a dict: ``{"stations": [...], "stale": bool, "updated_at": str|None}``.

    - If the cache is still fresh (within CACHE_TTL_SECONDS) and non-empty,
      it is returned immediately with ``stale=False``.
    - Otherwise a live fetch against NTRIP_URL is attempted. On success the
      cache is refreshed and returned with ``stale=False``.
    - If the fetch or parse fails for any reason (network error, timeout,
      empty result), a warning is logged and whatever is in the cache
      (possibly an empty list, if nothing has ever succeeded) is returned
      with ``stale=True``.
    """
    now = time.time()

    if (
        _cache["fetched_at"] is not None
        and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS
        and _cache["stations"]
    ):
        return {
            "stations": _cache["stations"],
            "stale": False,
            "updated_at": _cache["updated_at"],
        }

    try:
        request = urllib.request.Request(
            NTRIP_URL,
            headers={"User-Agent": "FUNDCORSRD-stations-proxy/1.0"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read()

        text = raw.decode("utf-8", errors="replace")
        stations = _parse_sourcetable(text)

        if not stations:
            raise ValueError("NTRIP sourcetable returned no STR; entries")

        _cache["stations"] = stations
        _cache["fetched_at"] = now
        _cache["updated_at"] = datetime.now(timezone.utc).isoformat()
        _cache["stale"] = False

        return {
            "stations": _cache["stations"],
            "stale": False,
            "updated_at": _cache["updated_at"],
        }
    except Exception as exc:  # noqa: BLE001 - any fetch/parse failure should degrade to cache
        logger.warning(
            "Failed to fetch/parse NTRIP sourcetable from %s: %s", NTRIP_URL, exc
        )
        _cache["stale"] = True
        return {
            "stations": _cache["stations"],
            "stale": True,
            "updated_at": _cache["updated_at"],
        }
