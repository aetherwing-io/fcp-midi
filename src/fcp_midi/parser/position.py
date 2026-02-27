"""Position parser — converts position strings to absolute tick values.

Supports measure.beat, measure.beat.tick, and raw tick formats.
Handles time-signature context for correct measure lengths.
"""

from __future__ import annotations

from typing import Any

from fcp_midi.errors import ValidationError


def parse_position(
    s: str,
    time_sigs: list[Any] | None = None,
    ppqn: int = 480,
    reference_tick: int | None = None,
    song_end_tick: int | None = None,
) -> int:
    """Parse a position string and return an absolute tick.

    Parameters
    ----------
    s : str
        Position specification:

        - ``"M.B"`` — measure.beat (1-based). ``"1.1"`` = tick 0.
        - ``"M.B.T"`` — with tick subdivision. ``"2.1.120"`` = tick 2040.
        - ``"tick:N"`` — raw absolute tick.
        - ``"+DUR"`` — relative: reference_tick + duration.
        - ``"-DUR"`` — relative: reference_tick - duration.
        - ``"end"`` — song end (last note end tick).

    time_sigs : list
        List of ``TimeSignature`` objects (or anything with ``.absolute_tick``,
        ``.numerator``, ``.denominator`` attributes), sorted by tick.
        Defaults to 4/4 if *None* or empty.
    ppqn : int
        Ticks per quarter note (default 480).
    reference_tick : int | None
        Reference tick for relative positions (+DUR / -DUR).
    song_end_tick : int | None
        Song end tick for the ``"end"`` keyword.

    Returns
    -------
    int
        Absolute tick position.

    Raises
    ------
    ValueError
        If the position string cannot be parsed.
    """
    # "end" keyword
    if s == "end":
        if song_end_tick is not None:
            return song_end_tick
        raise ValidationError("'end' requires song context")

    # Relative positions: +DUR or -DUR
    if s.startswith("+") or (s.startswith("-") and not s[1:].isdigit() if len(s) > 1 else False):
        from fcp_midi.parser.duration import parse_duration

        if s.startswith("+"):
            sign = 1
            remainder = s[1:]
        else:
            sign = -1
            remainder = s[1:]

        if reference_tick is None:
            raise ValidationError("Relative position requires reference")

        dur_ticks = parse_duration(remainder, ppqn)
        return max(0, reference_tick + sign * dur_ticks)

    # Raw tick
    if s.startswith("tick:"):
        try:
            return int(s[5:])
        except ValueError:
            raise ValidationError(f"Invalid tick value in '{s}'")

    # M.B or M.B.T
    parts = s.split(".")
    if len(parts) < 2 or len(parts) > 3:
        raise ValidationError(
            f"Invalid position format: '{s}' (expected M.B or M.B.T)"
        )

    try:
        measure = int(parts[0])
        beat = int(parts[1])
        sub_ticks = int(parts[2]) if len(parts) == 3 else 0
    except ValueError:
        raise ValidationError(f"Non-integer component in position: '{s}'")

    if measure < 1:
        raise ValidationError(f"Measure must be >= 1, got {measure}")
    if beat < 1:
        raise ValidationError(f"Beat must be >= 1, got {beat}")

    # Build effective time-signature map
    ts_list = _normalise_time_sigs(time_sigs, ppqn)

    # Walk measures up to the target
    absolute_tick = 0
    current_measure = 1
    ts_idx = 0

    while current_measure < measure:
        # Advance to next applicable time signature if one exists
        while (
            ts_idx + 1 < len(ts_list)
            and ts_list[ts_idx + 1][0] <= absolute_tick
        ):
            ts_idx += 1

        _, numerator, denominator = ts_list[ts_idx]
        ticks_per_measure = _ticks_per_measure(numerator, denominator, ppqn)
        absolute_tick += ticks_per_measure
        current_measure += 1

    # Now add beat offset within the target measure
    # Advance ts_idx if needed
    while (
        ts_idx + 1 < len(ts_list)
        and ts_list[ts_idx + 1][0] <= absolute_tick
    ):
        ts_idx += 1

    _, numerator, denominator = ts_list[ts_idx]
    ticks_per_beat = _ticks_per_beat(denominator, ppqn)

    absolute_tick += (beat - 1) * ticks_per_beat + sub_ticks
    return absolute_tick


def _ticks_per_beat(denominator: int, ppqn: int) -> int:
    """Ticks for one beat given the time-signature denominator."""
    # denominator=4 → quarter note → ppqn ticks
    # denominator=8 → eighth note → ppqn/2 ticks
    # denominator=2 → half note → ppqn*2 ticks
    return ppqn * 4 // denominator


def _ticks_per_measure(numerator: int, denominator: int, ppqn: int) -> int:
    """Ticks for one full measure."""
    return numerator * _ticks_per_beat(denominator, ppqn)


def _normalise_time_sigs(
    time_sigs: list[Any] | None,
    ppqn: int,
) -> list[tuple[int, int, int]]:
    """Return a list of ``(absolute_tick, numerator, denominator)`` tuples.

    Falls back to 4/4 at tick 0 if empty/None.
    """
    if not time_sigs:
        return [(0, 4, 4)]

    result: list[tuple[int, int, int]] = []
    for ts in time_sigs:
        result.append((ts.absolute_tick, ts.numerator, ts.denominator))
    result.sort(key=lambda t: t[0])

    # Ensure there is always an entry at tick 0
    if result[0][0] != 0:
        result.insert(0, (0, 4, 4))

    return result
