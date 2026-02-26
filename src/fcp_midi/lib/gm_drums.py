"""General MIDI Level 1 drum map (channel 10, notes 35-81)."""

from __future__ import annotations

# fmt: off
GM_DRUMS: dict[int, str] = {
    35: "acoustic-bass-drum",
    36: "bass-drum-1",
    37: "side-stick",
    38: "acoustic-snare",
    39: "hand-clap",
    40: "electric-snare",
    41: "low-floor-tom",
    42: "closed-hi-hat",
    43: "high-floor-tom",
    44: "pedal-hi-hat",
    45: "low-tom",
    46: "open-hi-hat",
    47: "low-mid-tom",
    48: "hi-mid-tom",
    49: "crash-cymbal-1",
    50: "high-tom",
    51: "ride-cymbal-1",
    52: "chinese-cymbal",
    53: "ride-bell",
    54: "tambourine",
    55: "splash-cymbal",
    56: "cowbell",
    57: "crash-cymbal-2",
    58: "vibraslap",
    59: "ride-cymbal-2",
    60: "hi-bongo",
    61: "low-bongo",
    62: "mute-hi-conga",
    63: "open-hi-conga",
    64: "low-conga",
    65: "high-timbale",
    66: "low-timbale",
    67: "high-agogo",
    68: "low-agogo",
    69: "cabasa",
    70: "maracas",
    71: "short-whistle",
    72: "long-whistle",
    73: "short-guiro",
    74: "long-guiro",
    75: "claves",
    76: "hi-wood-block",
    77: "low-wood-block",
    78: "mute-cuica",
    79: "open-cuica",
    80: "mute-triangle",
    81: "open-triangle",
}
# fmt: on

# Build reverse lookup: drum name -> note number
_NAME_TO_NOTE: dict[str, int] = {name: note for note, name in GM_DRUMS.items()}

# Common aliases
_ALIASES: dict[str, int] = {
    "kick": 36,
    "snare": 38,
    "hihat": 42,
    "hi-hat": 42,
    "ride": 51,
    "crash": 49,
    "tom": 50,
}


def _normalize(name: str) -> str:
    """Normalize a name for fuzzy matching: lowercase, spaces to hyphens."""
    return name.strip().lower().replace(" ", "-")


def drum_to_note(name: str) -> int | None:
    """Look up a GM drum note number by name.

    Supports:
    - Exact match (case-insensitive, spaces or hyphens)
    - Alias lookup ("kick" -> 36, "snare" -> 38, etc.)
    - Partial substring match (first match in note order)
    """
    normalized = _normalize(name)

    # Exact match
    if normalized in _NAME_TO_NOTE:
        return _NAME_TO_NOTE[normalized]

    # Alias match
    if normalized in _ALIASES:
        return _ALIASES[normalized]

    # Partial match — first drum whose name contains the query
    for note_num in range(35, 82):
        if normalized in GM_DRUMS[note_num]:
            return note_num

    return None


def note_to_drum(note: int) -> str | None:
    """Look up a GM drum name by MIDI note number (35-81)."""
    return GM_DRUMS.get(note)
