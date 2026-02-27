"""Symbolic velocity name mappings for musical dynamics."""

from __future__ import annotations

from fcp_midi.errors import ValidationError

VELOCITY_NAMES: dict[str, int] = {
    "ppp": 16,
    "pp": 33,
    "p": 49,
    "mp": 64,
    "mf": 80,
    "f": 96,
    "ff": 112,
    "fff": 127,
}


def parse_velocity(s: str) -> int:
    """Parse a velocity value from a string.

    Accepts:
    - Numeric strings: "80" -> 80
    - Symbolic names: "mf" -> 80, "ff" -> 112

    Raises:
        ValueError: If the string is not a valid velocity.
    """
    stripped = s.strip().lower()

    # Try symbolic lookup first
    if stripped in VELOCITY_NAMES:
        return VELOCITY_NAMES[stripped]

    # Try numeric
    try:
        val = int(stripped)
    except ValueError:
        raise ValidationError(f"Unknown velocity: {s!r}") from None

    if not 0 <= val <= 127:
        raise ValidationError(f"Velocity out of range (0-127): {val}")

    return val
