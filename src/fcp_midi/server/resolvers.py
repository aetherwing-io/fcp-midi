"""Centralized parameter parsing and resolution helpers.

Provides typed resolution functions that return parsed values or error
strings, plus the ``OpContext`` dataclass shared by all op handlers.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from fcp_midi.lib.instrument_registry import InstrumentRegistry
from fcp_midi.lib.gm_instruments import instrument_to_program, program_to_instrument
from fcp_midi.model.event_log import EventLog
from fcp_midi.model.registry import Registry
from fcp_midi.model.song import Note, Pitch, Song, Track
from fcp_midi.model.timing import ticks_to_position
from fcp_midi.parser.pitch import parse_pitch, _MIDI_TO_NOTE
from fcp_midi.parser.position import parse_position, _ticks_per_beat
from fcp_midi.parser.duration import parse_duration
from fcp_midi.parser.selector import Selector
from fcp_midi.lib.velocity_names import parse_velocity
from fcp_midi.server.formatter import format_result


@dataclass
class InstrumentResolution:
    """Result of resolving an instrument from op params."""
    program: int | None
    instrument_name: str | None
    bank_msb: int | None
    bank_lsb: int | None
    is_drum_kit: bool = False


@dataclass
class OpContext:
    """Shared state passed to every op handler."""
    song: Song
    event_log: EventLog
    registry: Registry
    last_tick: int
    instrument_registry: InstrumentRegistry | None = None


def resolve_bank(params: dict[str, str]) -> tuple[int | None, int | None] | str:
    """Parse ``bank:MSB[.LSB]`` param. Returns (msb, lsb) tuple or error string."""
    bank_str = params.get("bank")
    if not bank_str:
        return (None, None)
    try:
        parts = bank_str.split(".")
        bank_msb = int(parts[0])
        if not (0 <= bank_msb <= 127):
            return format_result(False, "Bank MSB must be 0-127")
        bank_lsb = None
        if len(parts) > 1:
            bank_lsb = int(parts[1])
            if not (0 <= bank_lsb <= 127):
                return format_result(False, "Bank LSB must be 0-127")
        return (bank_msb, bank_lsb)
    except ValueError:
        return format_result(False, f"Invalid bank value: {bank_str!r}")


_DRUM_NAMES = frozenset({"standard-kit", "drum-kit", "drums", "percussion"})


def resolve_instrument(
    params: dict[str, str],
    instrument_registry: InstrumentRegistry | None,
    bank_msb: int | None = None,
    bank_lsb: int | None = None,
) -> InstrumentResolution | str:
    """Resolve instrument from op params (program:N or instrument name).

    Returns InstrumentResolution or error string.
    """
    inst_name = params.get("instrument")
    raw_program = params.get("program")

    if raw_program is not None:
        try:
            program = int(raw_program)
            if not (0 <= program <= 127):
                return format_result(False, "Program must be 0-127")
        except ValueError:
            return format_result(False, f"Invalid program number: {raw_program!r}")
        # Reverse lookup for display name
        if inst_name is None:
            inst_name = program_to_instrument(program)
        return InstrumentResolution(
            program=program,
            instrument_name=inst_name,
            bank_msb=bank_msb,
            bank_lsb=bank_lsb,
        )

    if not inst_name:
        return InstrumentResolution(
            program=None,
            instrument_name=None,
            bank_msb=bank_msb,
            bank_lsb=bank_lsb,
        )

    normalized = inst_name.strip().lower().replace(" ", "-")
    is_drum_kit = normalized in _DRUM_NAMES

    if instrument_registry is not None:
        spec = instrument_registry.resolve(inst_name)
        if spec is not None:
            resolved_bank_msb = bank_msb
            resolved_bank_lsb = bank_lsb
            if resolved_bank_msb is None and spec.bank_msb != 0:
                resolved_bank_msb = spec.bank_msb
            if resolved_bank_lsb is None and spec.bank_lsb != 0:
                resolved_bank_lsb = spec.bank_lsb
            return InstrumentResolution(
                program=spec.program,
                instrument_name=inst_name,
                bank_msb=resolved_bank_msb,
                bank_lsb=resolved_bank_lsb,
                is_drum_kit=is_drum_kit,
            )
        elif not is_drum_kit:
            suggestion = instrument_registry.suggest(inst_name)
            msg = f"Unknown instrument: {inst_name!r}"
            if suggestion:
                msg += f"\n  {suggestion}"
            return format_result(False, msg)
    else:
        program = instrument_to_program(inst_name)
        if program is None and not is_drum_kit:
            return format_result(False, f"Unknown instrument: {inst_name!r}")
        return InstrumentResolution(
            program=program,
            instrument_name=inst_name,
            bank_msb=bank_msb,
            bank_lsb=bank_lsb,
            is_drum_kit=is_drum_kit,
        )

    # Drum kit fallback
    return InstrumentResolution(
        program=0,
        instrument_name=inst_name,
        bank_msb=bank_msb,
        bank_lsb=bank_lsb,
        is_drum_kit=True,
    )


def resolve_channel(params: dict[str, str]) -> int | None:
    """Parse ``ch`` param (1-indexed) to 0-indexed, or None if absent."""
    if "ch" in params:
        return int(params["ch"]) - 1
    return None


def display_channel(ch_0indexed: int) -> int:
    """Convert internal 0-indexed channel to 1-indexed display."""
    return ch_0indexed + 1


def resolve_position(
    params: dict[str, str],
    song: Song,
    last_tick: int,
    key: str = "at",
    default: str = "1.1",
) -> int | str:
    """Parse a position param, returning tick or error string."""
    at_str = params.get(key, default)
    try:
        return parse_position(
            at_str, song.time_signatures, song.ppqn,
            reference_tick=last_tick, song_end_tick=max_tick(song),
        )
    except ValueError as e:
        return format_result(False, f"Invalid position: {e}")


def resolve_duration(
    params: dict[str, str],
    song: Song,
    key: str = "dur",
    default: str = "quarter",
) -> int | str:
    """Parse a duration param, returning ticks or error string."""
    dur_str = params.get(key, default)
    try:
        return parse_duration(dur_str, song.ppqn)
    except ValueError as e:
        return format_result(False, f"Invalid duration: {e}")


def resolve_velocity(
    params: dict[str, str],
    key: str = "vel",
    default: str = "80",
) -> int | str:
    """Parse a velocity param, returning 1-127 or error string."""
    vel_str = params.get(key, default)
    try:
        return parse_velocity(vel_str)
    except ValueError as e:
        return format_result(False, f"Invalid velocity: {e}")


def resolve_pitch(pitch_str: str) -> Pitch | str:
    """Parse a pitch string, returning Pitch or error string."""
    try:
        return parse_pitch(pitch_str)
    except ValueError as e:
        return format_result(False, f"Invalid pitch: {e}")


def resolve_track(song: Song, name: str | None) -> Track | str:
    """Resolve a track name with fuzzy matching, returning Track or error string."""
    if not name:
        return format_result(False, "Missing track name")

    track = song.get_track_by_name(name)
    if track:
        return track

    suggestion = suggest_track_name(song, name)
    return format_result(False, f"Track '{name}' not found", suggestion)


def suggest_track_name(song: Song, name: str) -> str | None:
    """Fuzzy-match a track name and return a suggestion string."""
    if not song.tracks:
        return None

    existing = [t.name for t in song.tracks.values()]
    matches = difflib.get_close_matches(name, existing, n=1, cutoff=0.4)
    if matches:
        return f"Did you mean '{matches[0]}'?"
    return f"Available tracks: {', '.join(existing)}"


def resolve_selectors(
    selectors: list[Selector],
    song: Song,
    registry: Registry,
    event_log: EventLog,
) -> list[Note] | str:
    """Resolve selectors into a list of notes via the registry."""
    if not selectors:
        return format_result(False, "No selectors specified",
                             "Use @track:NAME, @range:M.B-M.B, @pitch:P, @all, etc.")

    # Separate positive and negated selectors
    positive = [s for s in selectors if not s.negated]
    negated = [s for s in selectors if s.negated]

    track_name: str | None = None
    pitch_midi: int | None = None
    range_start: int | None = None
    range_end: int | None = None
    channel: int | None = None
    vel_low: int | None = None
    vel_high: int | None = None
    use_all = False
    use_recent: int | None = None

    for sel in positive:
        if sel.type == "track":
            track_name = sel.value
        elif sel.type == "channel":
            try:
                channel = int(sel.value)
            except ValueError:
                return format_result(False, f"Invalid channel: {sel.value!r}")
        elif sel.type == "range":
            range_parts = sel.value.split("-")
            if len(range_parts) != 2:
                return format_result(False, f"Invalid range: {sel.value!r}", "@range:1.1-4.4")
            try:
                range_start = parse_position(
                    range_parts[0], song.time_signatures, song.ppqn
                )
                range_end = parse_position(
                    range_parts[1], song.time_signatures, song.ppqn
                )
                ts = song.time_signatures[0] if song.time_signatures else None
                denom = ts.denominator if ts else 4
                range_end += _ticks_per_beat(denom, song.ppqn)
            except ValueError as e:
                return format_result(False, f"Invalid range position: {e}")
        elif sel.type == "pitch":
            try:
                p = parse_pitch(sel.value)
                pitch_midi = p.midi_number
            except ValueError as e:
                return format_result(False, f"Invalid pitch: {e}")
        elif sel.type == "velocity":
            vel_parts = sel.value.split("-")
            if len(vel_parts) != 2:
                return format_result(False, f"Invalid velocity range: {sel.value!r}")
            try:
                vel_low = int(vel_parts[0])
                vel_high = int(vel_parts[1])
            except ValueError:
                return format_result(False, f"Invalid velocity values: {sel.value!r}")
        elif sel.type == "all":
            use_all = True
        elif sel.type == "recent":
            use_recent = int(sel.value) if sel.value else 1

    if use_recent is not None:
        events = event_log.recent(use_recent)
        note_ids = set()
        for ev in events:
            if hasattr(ev, "note_id"):
                note_ids.add(ev.note_id)
        notes = []
        for track in song.tracks.values():
            for nid, note in track.notes.items():
                if nid in note_ids:
                    notes.append(note)
        return notes

    if use_all:
        notes = registry.search()
    elif not positive:
        # Only negated selectors: start with all notes
        notes = registry.search()
    else:
        notes = registry.search(
            track=track_name,
            pitch=pitch_midi,
            range_start=range_start,
            range_end=range_end,
            channel=channel,
            vel_low=vel_low,
            vel_high=vel_high,
        )

    # Apply negated selectors: subtract matching notes
    if negated and notes:
        exclude_ids: set[str] = set()
        for sel in negated:
            excluded = _resolve_single_selector(sel, song, registry)
            if isinstance(excluded, str):
                return excluded
            exclude_ids.update(n.id for n in excluded)
        notes = [n for n in notes if n.id not in exclude_ids]

    return notes


def _resolve_single_selector(
    sel: Selector,
    song: Song,
    registry: Registry,
) -> list[Note] | str:
    """Resolve a single selector into a note list (for negation subtraction)."""
    if sel.type == "track":
        return registry.by_track(sel.value)
    elif sel.type == "pitch":
        try:
            p = parse_pitch(sel.value)
            return registry.by_pitch(p.midi_number)
        except ValueError as e:
            return format_result(False, f"Invalid pitch: {e}")
    elif sel.type == "channel":
        try:
            return registry.by_channel(int(sel.value))
        except ValueError:
            return format_result(False, f"Invalid channel: {sel.value!r}")
    elif sel.type == "range":
        range_parts = sel.value.split("-")
        if len(range_parts) != 2:
            return format_result(False, f"Invalid range: {sel.value!r}")
        try:
            start = parse_position(range_parts[0], song.time_signatures, song.ppqn)
            end = parse_position(range_parts[1], song.time_signatures, song.ppqn)
            ts = song.time_signatures[0] if song.time_signatures else None
            denom = ts.denominator if ts else 4
            end += _ticks_per_beat(denom, song.ppqn)
            return registry.by_range(start, end)
        except ValueError as e:
            return format_result(False, f"Invalid range: {e}")
    elif sel.type == "velocity":
        vel_parts = sel.value.split("-")
        if len(vel_parts) != 2:
            return format_result(False, f"Invalid velocity range: {sel.value!r}")
        try:
            return registry.by_velocity_range(int(vel_parts[0]), int(vel_parts[1]))
        except ValueError:
            return format_result(False, f"Invalid velocity: {sel.value!r}")
    return []


def pitch_from_midi(midi_number: int) -> Pitch:
    """Create a Pitch from a raw MIDI number (uses sharps for black keys)."""
    note_in_octave = midi_number % 12
    octave = (midi_number // 12) - 1
    name, accidental = _MIDI_TO_NOTE[note_in_octave]
    return Pitch(
        name=name,
        accidental=accidental,
        octave=octave,
        midi_number=midi_number,
    )


def max_tick(song: Song) -> int:
    """Find the maximum tick (note end) across all tracks."""
    max_t = 0
    for t in song.tracks.values():
        for n in t.notes.values():
            end = n.absolute_tick + n.duration_ticks
            if end > max_t:
                max_t = end
    return max_t
