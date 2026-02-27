"""Op handlers for metadata: tempo, time-sig, key-sig, marker, title."""

from __future__ import annotations

import re

from fcp_midi.model.event_log import (
    KeySignatureChanged,
    MarkerAdded,
    TempoChanged,
    TimeSignatureChanged,
)
from fcp_midi.model.timing import ticks_to_position
from fcp_midi.parser.ops import ParsedOp
from fcp_midi.parser.position import parse_position
from fcp_midi.server.formatter import format_result
from fcp_midi.server.resolvers import OpContext


def op_tempo(op: ParsedOp, ctx: OpContext) -> str:
    bpm_str = op.target
    if not bpm_str:
        return format_result(False, "Missing BPM value", "tempo 120")

    try:
        bpm = float(bpm_str)
    except ValueError:
        return format_result(False, f"Invalid BPM: {bpm_str!r}")

    at_str = op.params.get("at", "1.1")
    try:
        tick = parse_position(at_str, ctx.song.time_signatures, ctx.song.ppqn)
    except ValueError as e:
        return format_result(False, f"Invalid position: {e}")

    old_bpm = ctx.song.tempo_map[0].bpm if ctx.song.tempo_map else 120.0
    ctx.song.add_tempo(bpm, tick)
    ctx.event_log.append(TempoChanged(old_bpm=old_bpm, new_bpm=bpm, absolute_tick=tick))

    pos = ticks_to_position(tick, ctx.song.time_signatures, ctx.song.ppqn)
    return format_result(True, f"Tempo {bpm:.0f} BPM at {pos}")


def op_time_sig(op: ParsedOp, ctx: OpContext) -> str:
    ts_str = op.target
    if not ts_str:
        return format_result(False, "Missing time signature", "time-sig 3/4")

    match = re.match(r"^(\d+)/(\d+)$", ts_str)
    if not match:
        return format_result(False, f"Invalid time signature: {ts_str!r}", "time-sig 3/4")

    num = int(match.group(1))
    denom = int(match.group(2))

    at_str = op.params.get("at", "1.1")
    try:
        tick = parse_position(at_str, ctx.song.time_signatures, ctx.song.ppqn)
    except ValueError as e:
        return format_result(False, f"Invalid position: {e}")

    old_ts = ctx.song.time_signatures[0] if ctx.song.time_signatures else None
    old_num = old_ts.numerator if old_ts else 4
    old_denom = old_ts.denominator if old_ts else 4

    ctx.song.add_time_signature(num, denom, tick)
    ctx.event_log.append(TimeSignatureChanged(
        old_numerator=old_num, old_denominator=old_denom,
        new_numerator=num, new_denominator=denom,
        absolute_tick=tick,
    ))

    return format_result(True, f"Time signature {num}/{denom}")


def op_key_sig(op: ParsedOp, ctx: OpContext) -> str:
    ks_str = op.target
    if not ks_str:
        return format_result(False, "Missing key signature", "key-sig C-major")

    parts = ks_str.replace("-", " ").split()
    key = parts[0] if parts else "C"
    mode = parts[1] if len(parts) > 1 else "major"

    # Handle shorthand: "Dm" -> key="D", mode="minor"
    # But preserve accidentals: "Bb" stays as "Bb" major, "Bbm" -> "Bb" minor
    if len(parts) == 1 and mode == "major":
        # Check if key ends with 'm' (minor shorthand)
        if len(key) >= 2 and key.endswith('m') and key[-2] != '#' and key[-2] != 'b':
            mode = "minor"
            key = key[:-1]
        elif len(key) >= 3 and key.endswith('m') and (key[-3] == '#' or key[-3] == 'b' or key[-2] in ('#', 'b')):
            # e.g. "Bbm", "F#m", "C#m"
            mode = "minor"
            key = key[:-1]

    at_str = op.params.get("at", "1.1")
    try:
        tick = parse_position(at_str, ctx.song.time_signatures, ctx.song.ppqn)
    except ValueError as e:
        return format_result(False, f"Invalid position: {e}")

    old_ks = ctx.song.key_signatures[0] if ctx.song.key_signatures else None
    old_key = old_ks.key if old_ks else "C"
    old_mode = old_ks.mode if old_ks else "major"

    ctx.song.add_key_signature(key, mode, tick)
    ctx.event_log.append(KeySignatureChanged(
        old_key=old_key, old_mode=old_mode,
        new_key=key, new_mode=mode,
        absolute_tick=tick,
    ))

    return format_result(True, f"Key signature {key} {mode}")


def op_marker(op: ParsedOp, ctx: OpContext) -> str:
    text = op.target
    if not text:
        return format_result(False, "Missing marker text", 'marker "Chorus" at:5.1')

    at_str = op.params.get("at", "1.1")
    try:
        tick = parse_position(at_str, ctx.song.time_signatures, ctx.song.ppqn)
    except ValueError as e:
        return format_result(False, f"Invalid position: {e}")

    ctx.song.add_marker(text, tick)
    ctx.event_log.append(MarkerAdded(text=text, absolute_tick=tick))

    pos = ticks_to_position(tick, ctx.song.time_signatures, ctx.song.ppqn)
    return format_result(True, f"Marker '{text}' at {pos}")


def op_title(op: ParsedOp, ctx: OpContext) -> str:
    title = op.target
    if not title:
        return format_result(False, "Missing title", 'title "My Song"')

    ctx.song.title = title
    return format_result(True, f"Title set to '{title}'")
