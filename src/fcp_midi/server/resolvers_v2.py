"""NoteIndex-based selector resolution for v2 (mido-native) architecture.

Replaces the simplified _resolve_selectors_v2 from ops_editing_v2.py with
proper NoteIndex-powered resolution. Supports all selector types:
  @track:NAME, @pitch:P, @range:M.B-M.B, @channel:N,
  @velocity:LO-HI, @all, @recent:N, and negation via @not:type:value.
"""

from __future__ import annotations

from fcp_midi.model.midi_model import NoteIndex, NoteRef
from fcp_midi.parser.pitch import parse_pitch
from fcp_midi.parser.position import parse_position, _ticks_per_beat
from fcp_midi.parser.selector import Selector
from fcp_midi.server.formatter import format_result
from fcp_midi.server.ops_context_v2 import MidiOpContext, get_time_sigs


def resolve_notes_v2(
    selectors: list[Selector],
    ctx: MidiOpContext,
) -> list[NoteRef] | str:
    """Resolve selectors into NoteRefs using the NoteIndex.

    Returns a list of NoteRefs matching the selectors, or an error string.
    """
    if not selectors:
        return format_result(
            False,
            "No selectors specified",
            "Use @track:NAME, @range:M.B-M.B, @pitch:P, @all, etc.",
        )

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

    time_sigs = get_time_sigs(ctx.model)
    ppqn = ctx.model.ppqn
    idx = ctx.note_index

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
                return format_result(
                    False, f"Invalid range: {sel.value!r}", "@range:1.1-4.4"
                )
            try:
                range_start = parse_position(range_parts[0], time_sigs, ppqn)
                range_end = parse_position(range_parts[1], time_sigs, ppqn)
                ts = time_sigs[0] if time_sigs else None
                denom = ts.denominator if ts else 4
                range_end += _ticks_per_beat(denom, ppqn)
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
                return format_result(
                    False, f"Invalid velocity range: {sel.value!r}"
                )
            try:
                vel_low = int(vel_parts[0])
                vel_high = int(vel_parts[1])
            except ValueError:
                return format_result(
                    False, f"Invalid velocity values: {sel.value!r}"
                )
        elif sel.type == "all":
            use_all = True
        elif sel.type == "recent":
            use_recent = int(sel.value) if sel.value else 1

    # @recent: return the last N notes by absolute tick
    if use_recent is not None:
        all_notes = sorted(idx.all, key=lambda n: n.abs_tick, reverse=True)
        return all_notes[:use_recent]

    # Pick starting set via the most specific NoteIndex lookup
    if use_all or (not positive and negated):
        notes = list(idx.all)
    elif track_name:
        ref = ctx.model.get_track(track_name)
        if not ref:
            return format_result(False, f"Track '{track_name}' not found")
        notes = list(idx.by_track.get(track_name, []))
    elif pitch_midi is not None:
        notes = list(idx.by_pitch.get(pitch_midi, []))
    elif channel is not None:
        notes = list(idx.by_channel.get(channel, []))
    else:
        notes = list(idx.all)

    # Apply remaining positive filters
    if track_name and not use_all:
        # Already filtered by track as primary lookup — skip
        pass
    elif track_name:
        notes = [n for n in notes if n.track_name == track_name]

    if pitch_midi is not None and track_name:
        # track was primary, still need pitch filter
        notes = [n for n in notes if n.pitch == pitch_midi]
    elif pitch_midi is not None:
        # pitch was primary — skip
        pass

    if channel is not None and (track_name or pitch_midi is not None):
        # channel wasn't primary, filter it
        notes = [n for n in notes if n.channel == channel]

    if range_start is not None and range_end is not None:
        notes = [n for n in notes if range_start <= n.abs_tick < range_end]

    if vel_low is not None and vel_high is not None:
        notes = [n for n in notes if vel_low <= n.velocity <= vel_high]

    # Apply negated selectors
    if negated and notes:
        for sel in negated:
            result = _apply_negation(sel, notes, time_sigs, ppqn)
            if isinstance(result, str):
                return result
            notes = result

    return notes


def _apply_negation(
    sel: Selector,
    notes: list[NoteRef],
    time_sigs: list,
    ppqn: int,
) -> list[NoteRef] | str:
    """Subtract notes matching a single negated selector."""
    if sel.type == "track":
        return [n for n in notes if n.track_name != sel.value]
    elif sel.type == "pitch":
        try:
            p = parse_pitch(sel.value)
            return [n for n in notes if n.pitch != p.midi_number]
        except ValueError as e:
            return format_result(False, f"Invalid pitch: {e}")
    elif sel.type == "channel":
        try:
            ch = int(sel.value)
            return [n for n in notes if n.channel != ch]
        except ValueError:
            return format_result(False, f"Invalid channel: {sel.value!r}")
    elif sel.type == "range":
        range_parts = sel.value.split("-")
        if len(range_parts) != 2:
            return format_result(False, f"Invalid range: {sel.value!r}")
        try:
            start = parse_position(range_parts[0], time_sigs, ppqn)
            end = parse_position(range_parts[1], time_sigs, ppqn)
            ts = time_sigs[0] if time_sigs else None
            denom = ts.denominator if ts else 4
            end += _ticks_per_beat(denom, ppqn)
            return [n for n in notes if not (start <= n.abs_tick < end)]
        except ValueError as e:
            return format_result(False, f"Invalid range: {e}")
    elif sel.type == "velocity":
        vel_parts = sel.value.split("-")
        if len(vel_parts) != 2:
            return format_result(False, f"Invalid velocity range: {sel.value!r}")
        try:
            lo = int(vel_parts[0])
            hi = int(vel_parts[1])
            return [n for n in notes if not (lo <= n.velocity <= hi)]
        except ValueError:
            return format_result(False, f"Invalid velocity: {sel.value!r}")
    return notes
