"""Static CAL FIRE defensible-space zone checklist. Not derived from Mireye
data — this is generic guidance, cited to CAL FIRE, that report.py maps onto
the directional threat findings from scoring.py.

Zone 0 status: AB 3074 / PRC 4291 ember-resistant-zone rules were still
being phased in as of this writing. Verify current effective status against
CAL FIRE before treating Zone 0 as a hard legal requirement in any given
jurisdiction — report.py surfaces this caveat every time Zone 0 is shown.
"""

SOURCE = "CAL FIRE Defensible Space (PRC 4291 / AB 3074)"
SOURCE_URL = "https://www.fire.ca.gov/dspace"

ZONE_0_STATUS_CAVEAT = (
    "Zone 0 (ember-resistant zone) comes from AB 3074 and PRC 4291. As of this "
    "report, statewide effective/enforcement dates were still being phased in. "
    "Verify current Zone 0 regulatory status for this property's jurisdiction "
    "against CAL FIRE before treating it as a compliance deadline."
)

ZONES = {
    "Zone 0": {
        "range": "0-5 ft from structures, decks, and attachments",
        "actions": [
            "Remove all combustible mulch, vegetation, and stored items within 5 ft of the structure.",
            "Use hardscape (gravel, pavers, concrete) instead of bark mulch or plants immediately against the house.",
            "Clear dead leaves and needles from roofs, gutters, and under decks.",
            "Do not stack firewood or store propane/fuel within this zone.",
        ],
    },
    "Zone 1": {
        "range": "5-30 ft from structures",
        "actions": [
            "Space tree canopies at least 10 ft apart; remove ladder fuels (shrubs under trees).",
            "Keep grass mowed to under 4 inches.",
            "Remove dead or dying vegetation and dispose of plant debris.",
            "Prune tree branches up 6-10 ft from the ground.",
        ],
    },
    "Zone 2": {
        "range": "30-100 ft from structures",
        "actions": [
            "Create horizontal and vertical spacing between shrubs and trees to break up continuous fuel.",
            "Remove fallen leaves, needles, and dead branches regularly.",
            "Reduce density of flammable brush, especially on slopes facing the structure.",
            "Maintain fire breaks along property lines shared with wildland vegetation.",
        ],
    },
}

STRUCTURE_HARDENING_NOTE = (
    "Roof, vent, eave, and siding hardening guidance below is generic CAL FIRE "
    "prescriptive advice, not an observation of this structure. Mireye provides "
    "building height, footprint, and class through Overture, but does not "
    "observe roof material, vent type, or siding — do not imply this structure "
    "was inspected."
)

STRUCTURE_HARDENING_ACTIONS = [
    "Class A fire-rated roofing, with no gaps or damaged sections.",
    "1/8-inch ember- and flame-resistant mesh screens on all attic, foundation, and soffit vents.",
    "Enclosed eaves; avoid open-eave construction where possible.",
    "Dual-pane or tempered glass windows to resist radiant heat cracking.",
    "Non-combustible or ignition-resistant siding within 6 inches of grade.",
]
