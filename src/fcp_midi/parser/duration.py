"""Duration parser — converts duration strings to tick counts.

Supports named durations, numeric aliases, dotted/triplet modifiers,
and raw tick values.
"""

from __future__ import annotations


# Base duration names → multiplier relative to a whole note (4 beats)
# At ppqn=480: whole=1920, half=960, quarter=480, etc.
_DURATION_NAMES: dict[str, float] = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "sixteenth": 0.25,
    "32nd": 0.125,
}

# Numeric aliases
_DURATION_ALIASES: dict[str, str] = {
    "1n": "whole",
    "2n": "half",
    "4n": "quarter",
    "8n": "eighth",
    "16n": "sixteenth",
    "32n": "32nd",
}


def parse_duration(s: str, ppqn: int = 480) -> int:
    """Parse a duration string and return absolute tick count.

    Parameters
    ----------
    s : str
        Duration specification. Supported formats:

        - Named: ``"whole"``, ``"half"``, ``"quarter"``, ``"eighth"``,
          ``"sixteenth"``, ``"32nd"``
        - Aliases: ``"1n"``, ``"2n"``, ``"4n"``, ``"8n"``, ``"16n"``, ``"32n"``
        - Modifiers: ``"dotted-quarter"`` (1.5x), ``"triplet-eighth"`` (2/3x)
        - Raw ticks: ``"ticks:360"``

    ppqn : int
        Ticks per quarter note (default 480).

    Returns
    -------
    int
        Duration in ticks.

    Raises
    ------
    ValueError
        If the duration string is not recognised.
    """
    # Raw ticks
    if s.startswith("ticks:"):
        try:
            return int(s[6:])
        except ValueError:
            raise ValueError(f"Invalid tick value in '{s}'")

    # Resolve aliases
    base_name = s
    modifier: str | None = None

    # Check for dotted- or triplet- prefix
    if s.startswith("dotted-"):
        modifier = "dotted"
        base_name = s[7:]
    elif s.startswith("triplet-"):
        modifier = "triplet"
        base_name = s[8:]

    # Resolve alias
    if base_name in _DURATION_ALIASES:
        base_name = _DURATION_ALIASES[base_name]

    multiplier = _DURATION_NAMES.get(base_name)
    if multiplier is None:
        raise ValueError(f"Unknown duration: '{s}'")

    # Base ticks = multiplier * ppqn (since quarter = 1.0 * ppqn)
    ticks = multiplier * ppqn

    # Apply modifier
    if modifier == "dotted":
        ticks *= 1.5
    elif modifier == "triplet":
        ticks *= 2.0 / 3.0

    return int(round(ticks))
