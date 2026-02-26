"""General MIDI Level 1 instrument definitions (programs 0-127)."""

from __future__ import annotations

# fmt: off
GM_INSTRUMENTS: dict[int, str] = {
    # Piano
    0: "acoustic-grand-piano",
    1: "bright-acoustic-piano",
    2: "electric-grand-piano",
    3: "honky-tonk-piano",
    4: "electric-piano-1",
    5: "electric-piano-2",
    6: "harpsichord",
    7: "clavinet",
    # Chromatic Percussion
    8: "celesta",
    9: "glockenspiel",
    10: "music-box",
    11: "vibraphone",
    12: "marimba",
    13: "xylophone",
    14: "tubular-bells",
    15: "dulcimer",
    # Organ
    16: "drawbar-organ",
    17: "percussive-organ",
    18: "rock-organ",
    19: "church-organ",
    20: "reed-organ",
    21: "accordion",
    22: "harmonica",
    23: "tango-accordion",
    # Guitar
    24: "acoustic-guitar-nylon",
    25: "acoustic-guitar-steel",
    26: "electric-guitar-jazz",
    27: "electric-guitar-clean",
    28: "electric-guitar-muted",
    29: "overdriven-guitar",
    30: "distortion-guitar",
    31: "guitar-harmonics",
    # Bass
    32: "acoustic-bass",
    33: "electric-bass-finger",
    34: "electric-bass-pick",
    35: "fretless-bass",
    36: "slap-bass-1",
    37: "slap-bass-2",
    38: "synth-bass-1",
    39: "synth-bass-2",
    # Strings
    40: "violin",
    41: "viola",
    42: "cello",
    43: "contrabass",
    44: "tremolo-strings",
    45: "pizzicato-strings",
    46: "orchestral-harp",
    47: "timpani",
    # Ensemble
    48: "string-ensemble-1",
    49: "string-ensemble-2",
    50: "synth-strings-1",
    51: "synth-strings-2",
    52: "choir-aahs",
    53: "voice-oohs",
    54: "synth-choir",
    55: "orchestra-hit",
    # Brass
    56: "trumpet",
    57: "trombone",
    58: "tuba",
    59: "muted-trumpet",
    60: "french-horn",
    61: "brass-section",
    62: "synth-brass-1",
    63: "synth-brass-2",
    # Reed
    64: "soprano-sax",
    65: "alto-sax",
    66: "tenor-sax",
    67: "baritone-sax",
    68: "oboe",
    69: "english-horn",
    70: "bassoon",
    71: "clarinet",
    # Pipe
    72: "piccolo",
    73: "flute",
    74: "recorder",
    75: "pan-flute",
    76: "blown-bottle",
    77: "shakuhachi",
    78: "whistle",
    79: "ocarina",
    # Synth Lead
    80: "lead-1-square",
    81: "lead-2-sawtooth",
    82: "lead-3-calliope",
    83: "lead-4-chiff",
    84: "lead-5-charang",
    85: "lead-6-voice",
    86: "lead-7-fifths",
    87: "lead-8-bass-lead",
    # Synth Pad
    88: "pad-1-new-age",
    89: "pad-2-warm",
    90: "pad-3-polysynth",
    91: "pad-4-choir",
    92: "pad-5-bowed",
    93: "pad-6-metallic",
    94: "pad-7-halo",
    95: "pad-8-sweep",
    # Synth Effects
    96: "fx-1-rain",
    97: "fx-2-soundtrack",
    98: "fx-3-crystal",
    99: "fx-4-atmosphere",
    100: "fx-5-brightness",
    101: "fx-6-goblins",
    102: "fx-7-echoes",
    103: "fx-8-sci-fi",
    # Ethnic
    104: "sitar",
    105: "banjo",
    106: "shamisen",
    107: "koto",
    108: "kalimba",
    109: "bagpipe",
    110: "fiddle",
    111: "shanai",
    # Percussive
    112: "tinkle-bell",
    113: "agogo",
    114: "steel-drums",
    115: "woodblock",
    116: "taiko-drum",
    117: "melodic-tom",
    118: "synth-drum",
    119: "reverse-cymbal",
    # Sound Effects
    120: "guitar-fret-noise",
    121: "breath-noise",
    122: "seashore",
    123: "bird-tweet",
    124: "telephone-ring",
    125: "helicopter",
    126: "applause",
    127: "gunshot",
}
# fmt: on

INSTRUMENT_FAMILIES: dict[str, list[str]] = {
    "Piano": [GM_INSTRUMENTS[i] for i in range(0, 8)],
    "Chromatic Percussion": [GM_INSTRUMENTS[i] for i in range(8, 16)],
    "Organ": [GM_INSTRUMENTS[i] for i in range(16, 24)],
    "Guitar": [GM_INSTRUMENTS[i] for i in range(24, 32)],
    "Bass": [GM_INSTRUMENTS[i] for i in range(32, 40)],
    "Strings": [GM_INSTRUMENTS[i] for i in range(40, 48)],
    "Ensemble": [GM_INSTRUMENTS[i] for i in range(48, 56)],
    "Brass": [GM_INSTRUMENTS[i] for i in range(56, 64)],
    "Reed": [GM_INSTRUMENTS[i] for i in range(64, 72)],
    "Pipe": [GM_INSTRUMENTS[i] for i in range(72, 80)],
    "Synth Lead": [GM_INSTRUMENTS[i] for i in range(80, 88)],
    "Synth Pad": [GM_INSTRUMENTS[i] for i in range(88, 96)],
    "Synth Effects": [GM_INSTRUMENTS[i] for i in range(96, 104)],
    "Ethnic": [GM_INSTRUMENTS[i] for i in range(104, 112)],
    "Percussive": [GM_INSTRUMENTS[i] for i in range(112, 120)],
    "Sound Effects": [GM_INSTRUMENTS[i] for i in range(120, 128)],
}

# Build reverse lookup: instrument name -> program number
_NAME_TO_PROGRAM: dict[str, int] = {name: num for num, name in GM_INSTRUMENTS.items()}

# Common aliases that map to specific instruments
_ALIASES: dict[str, str] = {
    "strings": "string-ensemble-1",
    "standard-kit": "acoustic-grand-piano",  # program 0 (drum kit convention)
}


def _normalize(name: str) -> str:
    """Normalize a name for fuzzy matching: lowercase, spaces to hyphens."""
    return name.strip().lower().replace(" ", "-")


def instrument_to_program(name: str) -> int | None:
    """Look up a GM program number by instrument name.

    Supports:
    - Exact match (case-insensitive, spaces or hyphens)
    - Alias lookup ("strings" -> "string-ensemble-1")
    - Partial substring match (first match in program order)
    """
    normalized = _normalize(name)

    # Exact match
    if normalized in _NAME_TO_PROGRAM:
        return _NAME_TO_PROGRAM[normalized]

    # Alias match
    if normalized in _ALIASES:
        return _NAME_TO_PROGRAM[_ALIASES[normalized]]

    # Partial match — first instrument whose name contains the query
    for program_num in range(128):
        if normalized in GM_INSTRUMENTS[program_num]:
            return program_num

    return None


def program_to_instrument(program: int) -> str | None:
    """Look up a GM instrument name by program number (0-127)."""
    return GM_INSTRUMENTS.get(program)
