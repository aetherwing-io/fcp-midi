"""MIDI Continuous Controller (CC) name/number mappings."""

from __future__ import annotations

# fmt: off
CC_NAMES: dict[str, int] = {
    "modulation":      1,
    "breath":          2,
    "foot":            4,
    "portamento-time": 5,
    "volume":          7,
    "balance":         8,
    "pan":             10,
    "expression":      11,
    "sustain":         64,
    "portamento":      65,
    "sostenuto":       66,
    "soft-pedal":      67,
    "legato":          68,
    "hold-2":          69,
    "resonance":       71,
    "release-time":    72,
    "attack-time":     73,
    "brightness":      74,
    "reverb":          91,
    "tremolo":         92,
    "chorus":          93,
    "detune":          94,
    "phaser":          95,
    "all-sound-off":   120,
    "reset-all":       121,
    "all-notes-off":   123,
}
# fmt: on

# Build reverse lookup: CC number -> canonical name (first name wins)
_NUMBER_TO_NAME: dict[int, str] = {}
for _name, _num in CC_NAMES.items():
    if _num not in _NUMBER_TO_NAME:
        _NUMBER_TO_NAME[_num] = _name


def _normalize(name: str) -> str:
    """Normalize a CC name: lowercase, spaces to hyphens."""
    return name.strip().lower().replace(" ", "-")


def cc_to_number(name: str) -> int | None:
    """Look up a CC number by name (case-insensitive, spaces or hyphens)."""
    return CC_NAMES.get(_normalize(name))


def number_to_cc(number: int) -> str | None:
    """Look up the canonical CC name by number."""
    return _NUMBER_TO_NAME.get(number)


def parse_cc_value(name: str, value_str: str) -> tuple[int, int]:
    """Parse a CC name and value string into (cc_number, value).

    Handles special cases:
    - "on" -> 127 (for toggle CCs like sustain)
    - "off" -> 0
    - Numeric strings -> int value

    Raises:
        ValueError: If CC name is unknown or value is invalid.
    """
    cc_num = cc_to_number(name)
    if cc_num is None:
        raise ValueError(f"Unknown CC name: {name!r}")

    val_lower = value_str.strip().lower()
    if val_lower == "on":
        return (cc_num, 127)
    if val_lower == "off":
        return (cc_num, 0)

    try:
        val = int(val_lower)
    except ValueError:
        raise ValueError(f"Invalid CC value: {value_str!r}") from None

    if not 0 <= val <= 127:
        raise ValueError(f"CC value out of range (0-127): {val}")

    return (cc_num, val)
