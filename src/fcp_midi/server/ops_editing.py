"""Op handlers for editing: remove, move, copy, transpose, velocity, quantize,
modify, repeat, crescendo/decrescendo, plus gap detection."""

from __future__ import annotations

import copy

from fcp_midi.model.event_log import NoteAdded, NoteModified, NoteRemoved
from fcp_midi.model.timing import ticks_to_position
from fcp_midi.parser.duration import parse_duration
from fcp_midi.parser.ops import ParsedOp
from fcp_midi.parser.pitch import parse_pitch
from fcp_midi.parser.position import parse_position, _ticks_per_measure
from fcp_midi.lib.velocity_names import parse_velocity
from fcp_midi.server.formatter import format_result
from fcp_midi.server.resolvers import (
    OpContext,
    max_tick,
    pitch_from_midi,
    resolve_selectors,
)


def op_remove(op: ParsedOp, ctx: OpContext) -> str:
    notes = resolve_selectors(op.selectors, ctx.song, ctx.registry, ctx.event_log)
    if isinstance(notes, str):
        return notes
    if not notes:
        return format_result(False, "No notes matched selectors")

    count = 0
    for note in notes:
        removed = ctx.song.remove_note(note.track_id, note.id)
        if removed:
            ctx.event_log.append(NoteRemoved(track_id=note.track_id, note_id=note.id, note_snapshot=copy.copy(note)))
            track = ctx.song.tracks.get(note.track_id)
            track_name = track.name if track else ""
            ctx.registry.remove_note(note, track_name)
            count += 1
    return format_result(True, f"Removed {count} note(s)")


def op_move(op: ParsedOp, ctx: OpContext) -> str:
    notes = resolve_selectors(op.selectors, ctx.song, ctx.registry, ctx.event_log)
    if isinstance(notes, str):
        return notes
    if not notes:
        return format_result(False, "No notes matched selectors")

    to_str = op.params.get("to")
    if not to_str:
        return format_result(False, "Missing to: parameter", "move @track:Piano to:3.1")

    try:
        to_tick = parse_position(
            to_str, ctx.song.time_signatures, ctx.song.ppqn,
            reference_tick=ctx.last_tick, song_end_tick=max_tick(ctx.song),
        )
    except ValueError as e:
        return format_result(False, f"Invalid position: {e}")

    min_tick_val = min(n.absolute_tick for n in notes)
    delta = to_tick - min_tick_val

    for note in notes:
        old_tick = note.absolute_tick
        note.absolute_tick = max(0, note.absolute_tick + delta)
        ctx.event_log.append(NoteModified(
            track_id=note.track_id, note_id=note.id,
            field_name="absolute_tick", old_value=old_tick, new_value=note.absolute_tick,
        ))

    pos = ticks_to_position(to_tick, ctx.song.time_signatures, ctx.song.ppqn)
    return format_result(True, f"Moved {len(notes)} note(s) to {pos}")


def op_copy(op: ParsedOp, ctx: OpContext) -> str:
    notes = resolve_selectors(op.selectors, ctx.song, ctx.registry, ctx.event_log)
    if isinstance(notes, str):
        return notes
    if not notes:
        return format_result(False, "No notes matched selectors")

    to_str = op.params.get("to")
    if not to_str:
        return format_result(False, "Missing to: parameter")

    try:
        to_tick = parse_position(
            to_str, ctx.song.time_signatures, ctx.song.ppqn,
            reference_tick=ctx.last_tick, song_end_tick=max_tick(ctx.song),
        )
    except ValueError as e:
        return format_result(False, f"Invalid position: {e}")

    min_tick_val = min(n.absolute_tick for n in notes)
    delta = to_tick - min_tick_val

    for note in notes:
        new_tick = max(0, note.absolute_tick + delta)
        new_note = ctx.song.add_note(
            note.track_id, note.pitch, new_tick,
            note.duration_ticks, note.velocity, note.channel,
        )
        ctx.event_log.append(NoteAdded(track_id=note.track_id, note_id=new_note.id, note_snapshot=copy.copy(new_note)))
        track = ctx.song.tracks.get(note.track_id)
        track_name = track.name if track else ""
        ctx.registry.add_note(new_note, track_name)

    pos = ticks_to_position(to_tick, ctx.song.time_signatures, ctx.song.ppqn)
    return format_result(True, f"Copied {len(notes)} note(s) to {pos}")


def op_transpose(op: ParsedOp, ctx: OpContext) -> str:
    notes = resolve_selectors(op.selectors, ctx.song, ctx.registry, ctx.event_log)
    if isinstance(notes, str):
        return notes
    if not notes:
        return format_result(False, "No notes matched selectors")

    semitones_str = op.target
    if not semitones_str:
        return format_result(False, "Missing semitone count", "transpose @track:Piano +5")

    try:
        semitones = int(semitones_str)
    except ValueError:
        return format_result(False, f"Invalid semitone value: {semitones_str!r}")

    count = 0
    for note in notes:
        new_midi = note.pitch.midi_number + semitones
        if 0 <= new_midi <= 127:
            old_pitch = note.pitch
            note.pitch = pitch_from_midi(new_midi)
            ctx.event_log.append(NoteModified(
                track_id=note.track_id, note_id=note.id,
                field_name="pitch", old_value=old_pitch, new_value=note.pitch,
            ))
            track = ctx.song.tracks.get(note.track_id)
            track_name = track.name if track else ""
            ctx.registry.update_note(note, track_name, "pitch", old_pitch)
            count += 1
    direction = "up" if semitones > 0 else "down"
    return format_result(True, f"Transposed {count} note(s) {direction} {abs(semitones)} semitones")


def op_velocity(op: ParsedOp, ctx: OpContext) -> str:
    notes = resolve_selectors(op.selectors, ctx.song, ctx.registry, ctx.event_log)
    if isinstance(notes, str):
        return notes
    if not notes:
        return format_result(False, "No notes matched selectors")

    delta_str = op.target
    if not delta_str:
        return format_result(False, "Missing velocity delta", "velocity @track:Piano +10")

    try:
        delta = int(delta_str)
    except ValueError:
        return format_result(False, f"Invalid velocity delta: {delta_str!r}")

    for note in notes:
        old_vel = note.velocity
        note.velocity = max(1, min(127, note.velocity + delta))
        ctx.event_log.append(NoteModified(
            track_id=note.track_id, note_id=note.id,
            field_name="velocity", old_value=old_vel, new_value=note.velocity,
        ))

    return format_result(True, f"Adjusted velocity of {len(notes)} note(s) by {delta:+d}")


def op_quantize(op: ParsedOp, ctx: OpContext) -> str:
    notes = resolve_selectors(op.selectors, ctx.song, ctx.registry, ctx.event_log)
    if isinstance(notes, str):
        return notes
    if not notes:
        return format_result(False, "No notes matched selectors")

    grid_str = op.params.get("grid", "quarter")
    try:
        grid_ticks = parse_duration(grid_str, ctx.song.ppqn)
    except ValueError as e:
        return format_result(False, f"Invalid grid: {e}")

    for note in notes:
        old_tick = note.absolute_tick
        note.absolute_tick = round(note.absolute_tick / grid_ticks) * grid_ticks
        if note.absolute_tick != old_tick:
            ctx.event_log.append(NoteModified(
                track_id=note.track_id, note_id=note.id,
                field_name="absolute_tick", old_value=old_tick, new_value=note.absolute_tick,
            ))

    return format_result(True, f"Quantized {len(notes)} note(s) to {grid_str}")


def op_modify(op: ParsedOp, ctx: OpContext) -> str:
    notes = resolve_selectors(op.selectors, ctx.song, ctx.registry, ctx.event_log)
    if isinstance(notes, str):
        return notes
    if not notes:
        return format_result(False, "No notes matched selectors")

    mod_keys = {"pitch", "vel", "dur", "at", "ch"}
    has_mod = any(k in op.params for k in mod_keys)
    if not has_mod:
        return format_result(False, "No modification specified")

    count = 0
    for note in notes:
        modified = False

        if "pitch" in op.params:
            try:
                new_pitch = parse_pitch(op.params["pitch"])
            except ValueError as e:
                return format_result(False, f"Invalid pitch: {e}")
            old_pitch = note.pitch
            note.pitch = new_pitch
            ctx.event_log.append(NoteModified(
                track_id=note.track_id, note_id=note.id,
                field_name="pitch", old_value=old_pitch, new_value=new_pitch,
            ))
            modified = True

        if "vel" in op.params:
            try:
                new_vel = parse_velocity(op.params["vel"])
            except ValueError as e:
                return format_result(False, f"Invalid velocity: {e}")
            old_vel = note.velocity
            note.velocity = new_vel
            ctx.event_log.append(NoteModified(
                track_id=note.track_id, note_id=note.id,
                field_name="velocity", old_value=old_vel, new_value=new_vel,
            ))
            modified = True

        if "dur" in op.params:
            try:
                new_dur = parse_duration(op.params["dur"], ctx.song.ppqn)
            except ValueError as e:
                return format_result(False, f"Invalid duration: {e}")
            old_dur = note.duration_ticks
            note.duration_ticks = new_dur
            ctx.event_log.append(NoteModified(
                track_id=note.track_id, note_id=note.id,
                field_name="duration_ticks", old_value=old_dur, new_value=new_dur,
            ))
            modified = True

        if "at" in op.params:
            try:
                new_tick = parse_position(
                    op.params["at"], ctx.song.time_signatures, ctx.song.ppqn,
                    reference_tick=ctx.last_tick, song_end_tick=max_tick(ctx.song),
                )
            except ValueError as e:
                return format_result(False, f"Invalid position: {e}")
            old_tick = note.absolute_tick
            note.absolute_tick = new_tick
            ctx.event_log.append(NoteModified(
                track_id=note.track_id, note_id=note.id,
                field_name="absolute_tick", old_value=old_tick, new_value=new_tick,
            ))
            modified = True

        if "ch" in op.params:
            new_ch = int(op.params["ch"]) - 1
            old_ch = note.channel
            note.channel = new_ch
            ctx.event_log.append(NoteModified(
                track_id=note.track_id, note_id=note.id,
                field_name="channel", old_value=old_ch, new_value=new_ch,
            ))
            modified = True

        if modified:
            count += 1

    need_reindex = any(k in op.params for k in ("pitch", "ch"))
    if need_reindex:
        ctx.registry.rebuild(ctx.song)
    return format_result(True, f"Modified {count} note(s)")


def op_repeat(op: ParsedOp, ctx: OpContext) -> str:
    notes = resolve_selectors(op.selectors, ctx.song, ctx.registry, ctx.event_log)
    if isinstance(notes, str):
        return notes
    if not notes:
        return format_result(False, "No notes matched selectors")

    count_str = op.params.get("count", "1")
    try:
        count = int(count_str)
    except ValueError:
        return format_result(False, f"Invalid count: {count_str!r}")

    min_tick_val = min(n.absolute_tick for n in notes)
    max_end = max(n.absolute_tick + n.duration_ticks for n in notes)
    span = max_end - min_tick_val

    to_str = op.params.get("to")
    if to_str:
        try:
            start_tick = parse_position(
                to_str, ctx.song.time_signatures, ctx.song.ppqn,
                reference_tick=ctx.last_tick, song_end_tick=max_tick(ctx.song),
            )
        except ValueError as e:
            return format_result(False, f"Invalid position: {e}")
    else:
        start_tick = max_end

    base_offset = start_tick - min_tick_val
    added = 0
    for i in range(count):
        current_offset = base_offset + i * span
        for note in notes:
            new_tick = note.absolute_tick + current_offset
            new_note = ctx.song.add_note(
                note.track_id, note.pitch, new_tick,
                note.duration_ticks, note.velocity, note.channel,
            )
            ctx.event_log.append(NoteAdded(track_id=note.track_id, note_id=new_note.id, note_snapshot=copy.copy(new_note)))
            track = ctx.song.tracks.get(note.track_id)
            track_name = track.name if track else ""
            ctx.registry.add_note(new_note, track_name)
            added += 1
    return format_result(True, f"Repeated {len(notes)} note(s) x{count} ({added} added)")


def op_crescendo(op: ParsedOp, ctx: OpContext) -> str:
    notes = resolve_selectors(op.selectors, ctx.song, ctx.registry, ctx.event_log)
    if isinstance(notes, str):
        return notes
    if not notes:
        return format_result(False, "No notes matched selectors")

    from_str = op.params.get("from")
    to_str = op.params.get("to")
    if not from_str or not to_str:
        return format_result(
            False, "Missing from: and/or to: parameter",
            f"{op.verb} @track:NAME @range:M.B-M.B from:mp to:ff",
        )

    try:
        from_vel = parse_velocity(from_str)
    except ValueError as e:
        return format_result(False, f"Invalid from velocity: {e}")

    try:
        to_vel = parse_velocity(to_str)
    except ValueError as e:
        return format_result(False, f"Invalid to velocity: {e}")

    sorted_notes = sorted(notes, key=lambda n: n.absolute_tick)
    n = len(sorted_notes)

    for i, note in enumerate(sorted_notes):
        old_vel = note.velocity
        if n == 1:
            new_vel = to_vel
        else:
            new_vel = round(from_vel + (to_vel - from_vel) * i / (n - 1))
        new_vel = max(1, min(127, new_vel))
        note.velocity = new_vel
        ctx.event_log.append(NoteModified(
            track_id=note.track_id, note_id=note.id,
            field_name="velocity", old_value=old_vel, new_value=new_vel,
        ))

    return format_result(
        True,
        f"{op.verb.capitalize()} applied to {n} note(s) ({from_str} -> {to_str})",
    )


def detect_gaps(song: "Song") -> list[str]:  # noqa: F821
    """Detect empty measures on tracks that have content elsewhere."""
    from fcp_midi.model.song import Song as _Song  # avoid circular

    if not song.tracks:
        return []

    tracks_with_notes = [t for t in song.tracks.values() if t.notes]
    if len(tracks_with_notes) < 2:
        return []

    ts = song.time_signatures[0] if song.time_signatures else None
    num = ts.numerator if ts else 4
    denom = ts.denominator if ts else 4
    tpm = _ticks_per_measure(num, denom, song.ppqn)
    if tpm == 0:
        return []

    max_tick_val = 0
    for track in tracks_with_notes:
        for note in track.notes.values():
            end = note.absolute_tick + note.duration_ticks
            if end > max_tick_val:
                max_tick_val = end

    total_measures = (max_tick_val + tpm - 1) // tpm
    if total_measures <= 0:
        return []

    global_occupied: set[int] = set()
    track_occupied: dict[str, set[int]] = {}

    for track in tracks_with_notes:
        occupied: set[int] = set()
        for note in track.notes.values():
            measure = note.absolute_tick // tpm + 1
            occupied.add(measure)
        track_occupied[track.name] = occupied
        global_occupied |= occupied

    warnings: list[str] = []
    for track in tracks_with_notes:
        missing = sorted(global_occupied - track_occupied[track.name])
        if not missing:
            continue
        ranges: list[str] = []
        start = missing[0]
        end = missing[0]
        for m in missing[1:]:
            if m == end + 1:
                end = m
            else:
                ranges.append(f"{start}-{end}" if start != end else str(start))
                start = m
                end = m
        ranges.append(f"{start}-{end}" if start != end else str(start))

        for r in ranges:
            warnings.append(f"? {track.name}: empty at measure {r}")

    return warnings
