# Demo Addresses

Captured **2026-07-12T1940Z**. Ember's output is not deterministic across
runs (NDVI moves under a rolling 60-day window — see LIMITATIONS.md), so
these are timestamped snapshots, not fixed reference values. Each address
has a `.json` (`./ember --json`) and a `.md` (`./ember`, rendered prose)
captured from the same run.

## Coffey Park, Santa Rosa

- **Address:** 800 Hopper Ave, Santa Rosa, CA → matched `800 HOPPER AVE,
  SANTA ROSA, CA, 95403` (38.4796, -122.7352) — on the Hopper Ave boundary
  of the Coffey Park subdivision destroyed in the 2017 Tubbs Fire.
- **Band:** Low (composite 0.0966)
- **fuel_history_caveat:** not triggered
- **partial_failures:** 0
- **Demonstrates:** flat dense WUI that burned in Tubbs — proves Ember
  finds risk without slope, via fuel + WUI density.
- Files: `coffey_park_2026-07-12T1940Z.json`, `coffey_park_2026-07-12T1940Z.md`

## Latigo Canyon, Malibu

- **Address:** 3000 Latigo Canyon Rd, Malibu, CA → matched `3000 LATIGO
  CANYON RD, MALIBU, CA, 90265` (34.0675, -118.7835) — steep Santa Monica
  Mountains chaparral/oak canyon.
- **Band:** Moderate (composite 0.3209)
- **fuel_history_caveat:** not triggered
- **partial_failures:** 0
- **Demonstrates:** steep chaparral — proves the directional uphill-slope
  threat model (worst bearings SW/W, slope multiplier well above baseline).
- Files: `latigo_canyon_2026-07-12T1940Z.json`, `latigo_canyon_2026-07-12T1940Z.md`

## Paradise, Butte County

- **Address:** 6626 Skyway, Paradise, CA 95969 → matched `6626 SKYWAY,
  PARADISE, CA, 95969` (39.7612, -121.6228) — post-2018 Camp Fire, rebuilt
  along Skyway.
- **Band:** Low (composite 0.1809)
- **fuel_history_caveat:** **TRIGGERED** — "This area has a recorded
  wildfire history in the tract-level data, but the current fuel reading
  directly around the property is low..." with `wildfire_annual_frequency
  = 0.0013979252442599456 (FEMA_NRI)` cited inline.
- **partial_failures:** 0
- **Demonstrates:** Low band + caveat firing — proves honest epistemics
  and the finding that FEMA NRI's tract-level frequency does not reflect
  the Camp Fire's actual history (see LIMITATIONS.md's calibration
  investigation).
- Files: `paradise_2026-07-12T1940Z.json`, `paradise_2026-07-12T1940Z.md`

## Big Bear Lake

- **Address:** 40650 Village Dr, Big Bear Lake, CA → matched `40650
  VILLAGE DR, BIG BEAR LAKE, CA, 92315` (34.2407, -116.9153) — San
  Bernardino Mountains resort town, dense conifer forest WUI.
- **Band:** Low (composite 0.1727)
- **fuel_history_caveat:** **TRIGGERED**
- **partial_failures:** 0 at capture time. Earlier development runs (Phase
  2 recalibration investigation) saw 3 `slope_degrees` DEM read failures
  at this exact address; 3 direct API retries immediately before this
  capture came back clean, confirming the failures were transient/
  retryable, not a persistent gap in this location's data. See
  LIMITATIONS.md for the full note — check 4 ("partial_failures surfaced,
  not dropped") is instead verified by a deterministic unit test
  (`tests/test_report.py`) that forces a synthetic partial_failures list
  through the same code path, since a live gap couldn't be reliably
  reproduced on demand.
- **Demonstrates:** the caveat fires on a lake-resort town that reads
  low-fuel inside a wildland tract, not just on Paradise — proves the flag
  is general, not a Paradise special-case.
- Files: `big_bear_lake_2026-07-12T1940Z.json`, `big_bear_lake_2026-07-12T1940Z.md`
