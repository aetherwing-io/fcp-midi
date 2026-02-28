"""Tracker format — compact sequential step view for MIDI data.

Replaces the ASCII piano-roll with a token-efficient format that only emits
steps containing events, groups simultaneous events per line, and includes
velocity plus duration-in-steps. Supports both output (query) and input
(block-mode import).

Output example::

    [Resolution: 16th]
    [Track: Piano (acoustic-grand-piano) | Range: 1.1-4.4]
    Step 01: [C4_v100_4], [E4_v90_4], [G4_v90_4]
    Step 03: [D5_v80_2]

Token format: ``[PITCH_vVELOCITY_DURATION]`` where DURATION is the integer
number of steps the note sustains. Each note appears once at its start step.

Input uses the exact same syntax for true round-trip fidelity.
"""

from __future__ import annotations

import re
from collections import defaultdict

from fcp_midi.parser.pitch import _MIDI_TO_NOTE


# ---------------------------------------------------------------------------
# Resolution mapping
# ---------------------------------------------------------------------------

_RESOLUTION_MAP: dict[str, int] = {
    "quarter": 4,
    "4n": 4,
    "8th": 2,
    "8n": 2,
    "16th": 1,
    "16n": 1,
    "32nd": 0,  # sentinel — handled specially
    "32n": 0,
}


def _ticks_per_step(resolution: str, ppqn: int) -> int:
    """Convert a resolution name to ticks per grid step."""
    res = resolution.lower()
    if res in ("32nd", "32n"):
        return ppqn // 8
    if res in ("16th", "16n"):
        return ppqn // 4
    if res in ("8th", "8n"):
        return ppqn // 2
    if res in ("quarter", "4n"):
        return ppqn
    raise ValueError(f"Unknown resolution: {resolution!r}")


def _resolution_label(resolution: str) -> str:
    """Human-readable label for the resolution header."""
    res = resolution.lower()
    if res in ("quarter", "4n"):
        return "quarter"
    if res in ("8th", "8n"):
        return "8th"
    if res in ("16th", "16n"):
        return "16th"
    if res in ("32nd", "32n"):
        return "32nd"
    return resolution


# ---------------------------------------------------------------------------
# Pitch helpers
# ---------------------------------------------------------------------------

def _pitch_name(midi_number: int) -> str:
    """Convert MIDI number to pitch name like C4, F#3."""
    note_in_oct = midi_number % 12
    octave = (midi_number // 12) - 1
    name, acc = _MIDI_TO_NOTE[note_in_oct]
    return f"{name}{acc}{octave}"


# ---------------------------------------------------------------------------
# Auto-detect resolution
# ---------------------------------------------------------------------------

def auto_detect_resolution(
    notes: list,
    ppqn: int,
) -> str:
    """Pick the coarsest resolution where ALL note start/end ticks align.

    Tries quarter -> 8th -> 16th -> 32nd. Uses ±1 tick tolerance.
    Falls back to 16th if nothing aligns perfectly.

    Parameters
    ----------
    notes : list
        NoteRef objects with .abs_tick and .duration_ticks attributes.
    ppqn : int
        Ticks per quarter note.
    """
    if not notes:
        return "16th"

    candidates = [
        ("quarter", ppqn),
        ("8th", ppqn // 2),
        ("16th", ppqn // 4),
        ("32nd", ppqn // 8),
    ]

    for res_name, tps in candidates:
        if tps <= 0:
            continue
        all_aligned = True
        for n in notes:
            start_rem = n.abs_tick % tps
            end_rem = (n.abs_tick + n.duration_ticks) % tps
            if min(start_rem, tps - start_rem) > 1 or min(end_rem, tps - end_rem) > 1:
                all_aligned = False
                break
        if all_aligned:
            return res_name

    return "16th"


# ---------------------------------------------------------------------------
# Format tracker (output)
# ---------------------------------------------------------------------------

def format_tracker(
    notes: list,
    track_name: str,
    time_sigs: list,
    ppqn: int,
    start_tick: int,
    end_tick: int,
    resolution: str | None = None,
    instrument: str | None = None,
) -> str:
    """Generate tracker-format output from a list of NoteRefs.

    Parameters
    ----------
    notes : list[NoteRef]
        Paired notes with .abs_tick, .duration_ticks, .pitch, .velocity.
    track_name : str
        Track label for the header.
    time_sigs : list
        Time signature objects (used for position display in header).
    ppqn : int
        Ticks per quarter note.
    start_tick : int
        Start of the range (absolute tick).
    end_tick : int
        End of the range (absolute tick).
    resolution : str | None
        Grid resolution. Auto-detected if None.
    instrument : str | None
        GM instrument name to display in the header. Omitted when None.
    """
    from fcp_midi.model.timing import ticks_to_position

    # Filter notes to range
    in_range = [
        n for n in notes
        if n.abs_tick + n.duration_ticks > start_tick and n.abs_tick < end_tick
    ]

    if not in_range:
        return f"No notes on {track_name} in range."

    # Auto-detect resolution if not specified
    if resolution is None:
        resolution = auto_detect_resolution(in_range, ppqn)

    tps = _ticks_per_step(resolution, ppqn)

    # Build events: one token per note at its start step with duration
    # step_events: step_number -> list of event strings
    step_events: dict[int, list[str]] = defaultdict(list)

    for n in sorted(in_range, key=lambda x: (x.abs_tick, x.pitch)):
        # Only emit tokens for notes whose start tick falls within range
        if n.abs_tick < start_tick:
            continue
        on_step = (n.abs_tick - start_tick) // tps
        pitch_str = _pitch_name(n.pitch)
        dur_steps = max(1, round(n.duration_ticks / tps))
        step_events[on_step].append(f"[{pitch_str}_v{n.velocity}_{dur_steps}]")

    if not step_events:
        return f"No notes on {track_name} in range."

    # Build output
    start_pos = ticks_to_position(start_tick, time_sigs, ppqn)
    end_pos = ticks_to_position(end_tick, time_sigs, ppqn)

    track_label = f"{track_name} ({instrument})" if instrument else track_name
    lines: list[str] = [
        f"[Resolution: {_resolution_label(resolution)}]",
        f"[Track: {track_label} | Range: {start_pos}-{end_pos}]",
    ]

    for step_num in sorted(step_events.keys()):
        events = step_events[step_num]
        step_label = f"Step {step_num + 1:02d}"
        lines.append(f"{step_label}: {', '.join(events)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Drum pitch helpers (multi-track)
# ---------------------------------------------------------------------------

# Preferred short aliases for common drum sounds (note number -> alias).
_DRUM_ALIASES: dict[int, str] = {
    36: "kick",
    38: "snare",
    42: "hihat",
    49: "crash",
    51: "ride",
}


def _drum_pitch_name(midi_number: int) -> str:
    """Human-readable drum name for a MIDI note number.

    Priority: short alias > GM drum name > standard pitch name fallback.
    """
    if midi_number in _DRUM_ALIASES:
        return _DRUM_ALIASES[midi_number]
    from fcp_midi.lib.gm_drums import note_to_drum
    gm_name = note_to_drum(midi_number)
    if gm_name is not None:
        return gm_name
    return _pitch_name(midi_number)


# ---------------------------------------------------------------------------
# Format tracker multi-track (output, read-only)
# ---------------------------------------------------------------------------

#: Maximum number of tracks in a combined view.
MAX_COMBINED_TRACKS = 4


def format_tracker_multi(
    track_data: list[tuple[str, list, bool]],
    time_sigs: list,
    ppqn: int,
    start_tick: int,
    end_tick: int,
    resolution: str | None = None,
) -> str:
    """Generate a multi-track combined tracker view.

    This is a read-only output format — no parsing/import counterpart.

    Parameters
    ----------
    track_data : list[(track_name, notes, is_drum)]
        Each entry is a tuple of track name, NoteRef list, and whether the
        track is a drum track (channel 10 / internally channel 9).
    time_sigs : list
        Time signature objects.
    ppqn : int
        Ticks per quarter note.
    start_tick : int
        Start of the range (absolute tick).
    end_tick : int
        End of the range (absolute tick).
    resolution : str | None
        Grid resolution. Auto-detected across all tracks if None.
    """
    from fcp_midi.model.timing import ticks_to_position

    # Enforce track cap
    omitted = 0
    if len(track_data) > MAX_COMBINED_TRACKS:
        omitted = len(track_data) - MAX_COMBINED_TRACKS
        track_data = track_data[:MAX_COMBINED_TRACKS]

    # Collect all notes across tracks (for auto-detect and empty check)
    all_in_range: list = []
    per_track: list[tuple[str, list, bool]] = []  # (name, in_range_notes, is_drum)

    for track_name, notes, is_drum in track_data:
        in_range = [
            n for n in notes
            if n.abs_tick + n.duration_ticks > start_tick and n.abs_tick < end_tick
        ]
        per_track.append((track_name, in_range, is_drum))
        all_in_range.extend(in_range)

    if not all_in_range:
        names = ", ".join(t[0] for t in track_data)
        return f"No notes on [{names}] in range."

    # Auto-detect resolution across ALL tracks combined
    if resolution is None:
        resolution = auto_detect_resolution(all_in_range, ppqn)

    tps = _ticks_per_step(resolution, ppqn)

    # Build step_events: step_number -> {track_name: [token_strings]}
    step_events: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for track_name, in_range, is_drum in per_track:
        for n in sorted(in_range, key=lambda x: (x.abs_tick, x.pitch)):
            if n.abs_tick < start_tick:
                continue
            on_step = (n.abs_tick - start_tick) // tps
            if is_drum:
                pitch_str = _drum_pitch_name(n.pitch)
            else:
                pitch_str = _pitch_name(n.pitch)
            dur_steps = max(1, round(n.duration_ticks / tps))
            step_events[on_step][track_name].append(
                f"{pitch_str}_v{n.velocity}_{dur_steps}"
            )

    if not step_events:
        names = ", ".join(t[0] for t in track_data)
        return f"No notes on [{names}] in range."

    # Build header
    start_pos = ticks_to_position(start_tick, time_sigs, ppqn)
    end_pos = ticks_to_position(end_tick, time_sigs, ppqn)
    track_names = ", ".join(t[0] for t in per_track)

    lines: list[str] = [
        f"[Resolution: {_resolution_label(resolution)}]",
        f"[Tracks: {track_names} | Range: {start_pos}-{end_pos}]",
    ]

    # Preserve track order for consistent output
    track_order = [t[0] for t in per_track]

    for step_num in sorted(step_events.keys()):
        track_tokens = step_events[step_num]
        step_label = f"Step {step_num + 1:02d}"
        parts: list[str] = []
        for tname in track_order:
            if tname in track_tokens:
                tokens = ", ".join(track_tokens[tname])
                parts.append(f"{tname}[{tokens}]")
        lines.append(f"{step_label}: {' '.join(parts)}")

    if omitted:
        lines.append(f"(+{omitted} more tracks omitted)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Parse event token (input)
# ---------------------------------------------------------------------------

_EVENT_RE = re.compile(
    r"^\[([A-G][#b]?-?\d+)_v(\d+)_(\d+)\]$"
)


def parse_event_token(token: str) -> tuple[int, int, int]:
    """Parse ``[C4_v100_4]`` -> ``(midi_number, velocity, duration_steps)``.

    Raises ValueError if the token doesn't match.
    """
    token = token.strip()
    m = _EVENT_RE.match(token)
    if not m:
        raise ValueError(f"Invalid event token: {token!r}")

    pitch_str = m.group(1)
    velocity = int(m.group(2))
    duration_steps = int(m.group(3))

    # Convert pitch string to MIDI number
    from fcp_midi.parser.pitch import parse_pitch
    pitch = parse_pitch(pitch_str)

    return (pitch.midi_number, velocity, duration_steps)


# ---------------------------------------------------------------------------
# Parse step line (input)
# ---------------------------------------------------------------------------

_STEP_RE = re.compile(r"^Step\s+(\d+)\s*:\s*(.+)$", re.IGNORECASE)


def parse_step_line(line: str) -> tuple[int, list[tuple[int, int, int]]]:
    """Parse ``Step 03: [C4_v100_4], [D5_v80_2]``.

    Returns ``(step_number, [(midi, vel, duration_steps), ...])``.
    Step numbers are 1-indexed as displayed.
    """
    line = line.strip()
    m = _STEP_RE.match(line)
    if not m:
        raise ValueError(f"Invalid step line: {line!r}")

    step_num = int(m.group(1))
    tokens_str = m.group(2)

    # Split on comma, parse each token
    events: list[tuple[int, int, int]] = []
    for token in tokens_str.split(","):
        token = token.strip()
        if token:
            events.append(parse_event_token(token))

    return (step_num, events)


# ---------------------------------------------------------------------------
# Convert tracker events to notes
# ---------------------------------------------------------------------------

def pair_tracker_events(
    steps: list[tuple[int, list[tuple[int, int, int]]]],
    start_tick: int,
    ticks_per_step: int,
) -> list[tuple[int, int, int, int]]:
    """Convert duration-in-token step data directly to notes.

    Parameters
    ----------
    steps : list[(step_num, [(midi, vel, duration_steps), ...])]
        Parsed step lines. Step numbers are 1-indexed.
    start_tick : int
        Absolute tick of step 1.
    ticks_per_step : int
        Ticks per grid step.

    Returns
    -------
    list[(pitch, velocity, abs_tick, duration_ticks)]
        Notes ready for model.add_note().
    """
    results: list[tuple[int, int, int, int]] = []

    for step_num, events in steps:
        step_tick = start_tick + (step_num - 1) * ticks_per_step
        for midi_num, vel, dur_steps in events:
            duration_ticks = dur_steps * ticks_per_step
            results.append((midi_num, vel, step_tick, duration_ticks))

    # Sort by tick, then pitch
    results.sort(key=lambda r: (r[2], r[0]))
    return results
