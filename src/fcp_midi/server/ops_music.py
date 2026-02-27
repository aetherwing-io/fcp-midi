"""Op handlers for music creation: note, chord, track, cc, bend, mute, solo, program."""

from __future__ import annotations

import copy
import re

from fcp_midi.model.event_log import (
    CCAdded,
    NoteAdded,
    PitchBendAdded,
    TrackAdded,
    TrackRemoved,
)
from fcp_midi.model.timing import ticks_to_position
from fcp_midi.parser.chord import parse_chord
from fcp_midi.parser.ops import ParsedOp
from fcp_midi.parser.pitch import parse_pitch
from fcp_midi.lib.cc_names import parse_cc_value
from fcp_midi.server.formatter import format_result
from fcp_midi.server.resolvers import (
    OpContext,
    resolve_bank,
    resolve_channel,
    resolve_duration,
    resolve_instrument,
    resolve_position,
    resolve_track,
    resolve_velocity,
    display_channel,
    max_tick,
)


def op_note(op: ParsedOp, ctx: OpContext) -> str:
    track = resolve_track(ctx.song, op.target)
    if isinstance(track, str):
        return track

    pitch_str = op.params.get("pitch")
    if not pitch_str and "midi" in op.params:
        pitch_str = f"midi:{op.params['midi']}"
    if not pitch_str:
        return format_result(False, "Missing pitch for note")

    try:
        pitch = parse_pitch(pitch_str)
    except ValueError as e:
        return format_result(False, f"Invalid pitch: {e}")

    tick = resolve_position(op.params, ctx.song, ctx.last_tick)
    if isinstance(tick, str):
        return tick

    dur = resolve_duration(op.params, ctx.song)
    if isinstance(dur, str):
        return dur

    vel = resolve_velocity(op.params)
    if isinstance(vel, str):
        return vel

    ch = resolve_channel(op.params)

    note = ctx.song.add_note(track.id, pitch, tick, dur, vel, ch)
    ctx.event_log.append(NoteAdded(track_id=track.id, note_id=note.id, note_snapshot=copy.copy(note)))
    ctx.registry.add_note(note, track.name)
    ctx.last_tick = tick + dur

    dur_str = op.params.get("dur", "quarter")
    pos = ticks_to_position(tick, ctx.song.time_signatures, ctx.song.ppqn)
    return format_result(
        True,
        f"Note {pitch_str} at {pos} on {track.name} (vel:{vel} dur:{dur_str})"
    )


def op_chord(op: ParsedOp, ctx: OpContext) -> str:
    track = resolve_track(ctx.song, op.target)
    if isinstance(track, str):
        return track

    chord_str = op.params.get("chord")
    if not chord_str:
        return format_result(False, "Missing chord symbol")

    try:
        pitches = parse_chord(chord_str)
    except ValueError as e:
        return format_result(False, f"Invalid chord: {e}")

    tick = resolve_position(op.params, ctx.song, ctx.last_tick)
    if isinstance(tick, str):
        return tick

    dur = resolve_duration(op.params, ctx.song)
    if isinstance(dur, str):
        return dur

    vel = resolve_velocity(op.params)
    if isinstance(vel, str):
        return vel

    ch = resolve_channel(op.params)

    for pitch in pitches:
        note = ctx.song.add_note(track.id, pitch, tick, dur, vel, ch)
        ctx.event_log.append(NoteAdded(track_id=track.id, note_id=note.id, note_snapshot=copy.copy(note)))
        ctx.registry.add_note(note, track.name)

    ctx.last_tick = tick + dur

    pos = ticks_to_position(tick, ctx.song.time_signatures, ctx.song.ppqn)
    return format_result(
        True,
        f"Chord {chord_str} ({len(pitches)} notes) at {pos} on {track.name}"
    )


def op_track(op: ParsedOp, ctx: OpContext) -> str:
    sub = op.target  # "add" or "remove"

    if sub == "add":
        name = op.params.get("name")
        if not name:
            return format_result(False, "Missing track name",
                                 "track add MyTrack instrument:acoustic-grand-piano")

        bank = resolve_bank(op.params)
        if isinstance(bank, str):
            return bank
        bank_msb, bank_lsb = bank

        resolved = resolve_instrument(
            op.params, ctx.instrument_registry, bank_msb, bank_lsb,
        )
        if isinstance(resolved, str):
            return resolved

        program = resolved.program
        inst_name = resolved.instrument_name
        is_drum_kit = resolved.is_drum_kit
        bank_msb = resolved.bank_msb
        bank_lsb = resolved.bank_lsb

        if is_drum_kit and program is None:
            program = 0

        ch = resolve_channel(op.params)
        if is_drum_kit and ch is None:
            ch = 9

        track = ctx.song.add_track(
            name=name,
            instrument=inst_name,
            program=program,
            channel=ch,
        )
        track.bank_msb = bank_msb
        track.bank_lsb = bank_lsb
        ctx.event_log.append(TrackAdded(track_id=track.id, track_snapshot=copy.copy(track)))

        inst_display = inst_name or "no instrument"
        disp_ch = display_channel(track.channel)
        return format_result(True, f"Track '{name}' added (ch:{disp_ch}, {inst_display})")

    elif sub == "remove":
        name = op.params.get("name")
        if not name:
            return format_result(False, "Missing track name for remove")

        track = ctx.song.get_track_by_name(name)
        if not track:
            from fcp_midi.server.resolvers import suggest_track_name
            suggestion = suggest_track_name(ctx.song, name)
            return format_result(False, f"Track '{name}' not found", suggestion)

        removed = ctx.song.remove_track(track.id)
        if removed:
            ctx.event_log.append(TrackRemoved(track_id=removed.id, track_snapshot=removed))
            ctx.registry.rebuild(ctx.song)
            return format_result(True, f"Track '{name}' removed")
        return format_result(False, f"Failed to remove track '{name}'")

    else:
        return format_result(False, f"Unknown track sub-command: {sub!r}",
                             "track add NAME or track remove NAME")


def op_cc(op: ParsedOp, ctx: OpContext) -> str:
    track = resolve_track(ctx.song, op.target)
    if isinstance(track, str):
        return track

    cc_name = op.params.get("cc_name")
    cc_value_str = op.params.get("cc_value")
    if not cc_name or not cc_value_str:
        return format_result(False, "Missing CC name or value",
                             "cc Piano volume 100 at:1.1")

    try:
        cc_num, cc_val = parse_cc_value(cc_name, cc_value_str)
    except ValueError as e:
        return format_result(False, str(e))

    from fcp_midi.parser.position import parse_position as _parse_pos
    at_str = op.params.get("at", "1.1")
    try:
        tick = _parse_pos(at_str, ctx.song.time_signatures, ctx.song.ppqn)
    except ValueError as e:
        return format_result(False, f"Invalid position: {e}")

    ch = resolve_channel(op.params)

    cc = ctx.song.add_cc(track.id, cc_num, cc_val, tick, ch)
    ctx.event_log.append(CCAdded(track_id=track.id, cc_id=cc.id, cc_snapshot=copy.copy(cc)))

    pos = ticks_to_position(tick, ctx.song.time_signatures, ctx.song.ppqn)
    return format_result(True, f"CC {cc_name}={cc_val} at {pos} on {track.name}")


def op_bend(op: ParsedOp, ctx: OpContext) -> str:
    track = resolve_track(ctx.song, op.target)
    if isinstance(track, str):
        return track

    value_str = op.params.get("value", "0")
    if value_str.lower() == "center":
        value = 0
    else:
        try:
            value = int(value_str)
        except ValueError:
            return format_result(False, f"Invalid bend value: {value_str!r}")

    if value < -8192 or value > 8191:
        return format_result(False, f"Bend value out of range (-8192 to 8191): {value}")

    from fcp_midi.parser.position import parse_position as _parse_pos
    at_str = op.params.get("at", "1.1")
    try:
        tick = _parse_pos(at_str, ctx.song.time_signatures, ctx.song.ppqn)
    except ValueError as e:
        return format_result(False, f"Invalid position: {e}")

    ch = resolve_channel(op.params)

    pb = ctx.song.add_pitch_bend(track.id, value, tick, ch)
    ctx.event_log.append(PitchBendAdded(track_id=track.id, pb_id=pb.id, pb_snapshot=copy.copy(pb)))

    pos = ticks_to_position(tick, ctx.song.time_signatures, ctx.song.ppqn)
    return format_result(True, f"Pitch bend={value} at {pos} on {track.name}")


def op_mute(op: ParsedOp, ctx: OpContext) -> str:
    track = resolve_track(ctx.song, op.target)
    if isinstance(track, str):
        return track

    track.mute = not track.mute
    state = "muted" if track.mute else "unmuted"
    return format_result(True, f"Track '{track.name}' {state}")


def op_solo(op: ParsedOp, ctx: OpContext) -> str:
    track = resolve_track(ctx.song, op.target)
    if isinstance(track, str):
        return track

    track.solo = not track.solo
    state = "solo on" if track.solo else "solo off"
    return format_result(True, f"Track '{track.name}' {state}")


def op_program(op: ParsedOp, ctx: OpContext) -> str:
    track = resolve_track(ctx.song, op.target)
    if isinstance(track, str):
        return track

    bank = resolve_bank(op.params)
    if isinstance(bank, str):
        return bank
    bank_msb, bank_lsb = bank

    resolved = resolve_instrument(
        op.params, ctx.instrument_registry, bank_msb, bank_lsb,
    )
    if isinstance(resolved, str):
        return resolved

    if resolved.program is None and resolved.instrument_name is None:
        return format_result(False, "Missing instrument name or program number")

    track.instrument = resolved.instrument_name
    track.program = resolved.program
    if resolved.bank_msb is not None:
        track.bank_msb = resolved.bank_msb
    if resolved.bank_lsb is not None:
        track.bank_lsb = resolved.bank_lsb
    return format_result(True, f"Track '{track.name}' instrument set to {resolved.instrument_name} (program:{resolved.program})")
