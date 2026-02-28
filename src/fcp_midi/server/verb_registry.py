"""Structured verb registry — single source of truth for all op verbs.

Uses ``VerbSpec`` and ``VerbRegistry`` from fcp_core. Verb definitions
are domain-specific to MIDI FCP.
"""

from __future__ import annotations

from fcp_core import VerbRegistry, VerbSpec  # noqa: F401


# -----------------------------------------------------------------------
# Verb definitions
# -----------------------------------------------------------------------

VERBS: list[VerbSpec] = [
    # Music creation
    VerbSpec(
        verb="note",
        syntax="note TRACK PITCH at:POS dur:DUR [vel:V] [ch:N]",
        category="music",
        params=["at", "dur", "vel", "ch"],
        description="Add a single note.",
    ),
    VerbSpec(
        verb="chord",
        syntax="chord TRACK SYMBOL at:POS dur:DUR [vel:V] [ch:N]",
        category="music",
        params=["at", "dur", "vel", "ch"],
        description="Add a chord (multiple notes).",
    ),
    VerbSpec(
        verb="track",
        syntax="track add|remove NAME [instrument:INST] [program:N] [ch:N] [bank:MSB[.LSB]]",
        category="music",
        params=["instrument", "program", "ch", "bank"],
        description="Add or remove a track.",
    ),
    VerbSpec(
        verb="cc",
        syntax="cc TRACK CC_NAME VALUE at:POS [ch:N]",
        category="music",
        params=["at", "ch"],
        description="Add a continuous controller event.",
    ),
    VerbSpec(
        verb="bend",
        syntax="bend TRACK VALUE at:POS [ch:N]",
        category="music",
        params=["at", "ch"],
        description="Add a pitch bend event.",
    ),
    VerbSpec(
        verb="mute",
        syntax="mute TRACK",
        category="state",
        description="Toggle track mute.",
    ),
    VerbSpec(
        verb="solo",
        syntax="solo TRACK",
        category="state",
        description="Toggle track solo.",
    ),
    VerbSpec(
        verb="program",
        syntax="program TRACK INSTRUMENT|program:N [at:POS] [bank:MSB[.LSB]]",
        category="state",
        params=["at", "bank"],
        description="Change track instrument.",
    ),

    # Meta
    VerbSpec(
        verb="tempo",
        syntax="tempo BPM [at:POS]",
        category="meta",
        params=["at"],
        description="Set tempo.",
    ),
    VerbSpec(
        verb="time-sig",
        syntax="time-sig N/D [at:POS]",
        category="meta",
        params=["at"],
        description="Set time signature.",
    ),
    VerbSpec(
        verb="key-sig",
        syntax="key-sig KEY-MODE [at:POS]",
        category="meta",
        params=["at"],
        description="Set key signature.",
    ),
    VerbSpec(
        verb="marker",
        syntax="marker TEXT at:POS",
        category="meta",
        params=["at"],
        description="Add a text marker.",
    ),
    VerbSpec(
        verb="title",
        syntax="title TEXT",
        category="meta",
        description="Set song title.",
    ),

    # Editing (selector-based)
    VerbSpec(
        verb="remove",
        syntax="remove SELECTORS",
        category="editing",
        description="Remove notes matching selectors.",
    ),
    VerbSpec(
        verb="move",
        syntax="move SELECTORS to:POS",
        category="editing",
        params=["to"],
        description="Move notes to a new position.",
    ),
    VerbSpec(
        verb="copy",
        syntax="copy SELECTORS to:POS",
        category="editing",
        params=["to"],
        description="Copy notes to a new position.",
    ),
    VerbSpec(
        verb="transpose",
        syntax="transpose SELECTORS SEMITONES",
        category="editing",
        description="Transpose notes by semitones.",
    ),
    VerbSpec(
        verb="velocity",
        syntax="velocity SELECTORS DELTA",
        category="editing",
        description="Adjust note velocities.",
    ),
    VerbSpec(
        verb="quantize",
        syntax="quantize SELECTORS grid:DUR",
        category="editing",
        params=["grid"],
        description="Quantize notes to a grid.",
    ),
    VerbSpec(
        verb="modify",
        syntax="modify SELECTORS [pitch:P] [vel:V] [dur:D] [at:POS] [ch:N]",
        category="editing",
        params=["pitch", "vel", "dur", "at", "ch"],
        description="Modify note properties in place.",
    ),
    VerbSpec(
        verb="repeat",
        syntax="repeat SELECTORS [to:POS] count:N",
        category="editing",
        params=["to", "count"],
        description="Repeat a note pattern.",
    ),
    VerbSpec(
        verb="crescendo",
        syntax="crescendo SELECTORS from:VEL to:VEL",
        category="editing",
        params=["from", "to"],
        description="Apply gradual velocity increase.",
    ),
    VerbSpec(
        verb="decrescendo",
        syntax="decrescendo SELECTORS from:VEL to:VEL",
        category="editing",
        params=["from", "to"],
        description="Apply gradual velocity decrease.",
    ),

    # Block import
    VerbSpec(
        verb="tracker",
        syntax="tracker TRACK import at:POS [res:RES] ... tracker end",
        category="music",
        params=["at", "res"],
        description="Import notes from tracker step format (block mode).",
    ),
]


# Quick lookup by verb name
VERB_MAP: dict[str, VerbSpec] = {v.verb: v for v in VERBS}
