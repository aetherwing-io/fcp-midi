"""Query handlers for read-only operations."""

from __future__ import annotations

from fcp_midi.model.event_log import CheckpointEvent, EventLog
from fcp_midi.model.registry import Registry
from fcp_midi.model.song import Song
from fcp_midi.model.timing import ticks_to_position
from fcp_midi.parser.pitch import parse_pitch
from fcp_midi.parser.position import parse_position
from fcp_midi.server.formatter import (
    format_describe,
    format_events,
    format_map,
    format_piano_roll,
    format_result,
    format_stats,
    format_track_list,
)
from fcp_midi.server.resolvers import OpContext, suggest_track_name


def dispatch_query(q: str, ctx: OpContext) -> str:
    """Route a query string to the appropriate handler."""
    q = q.strip()
    parts = q.split(None, 1)
    command = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""

    if command == "map":
        return format_map(ctx.song)
    elif command == "tracks":
        return format_track_list(ctx.song)
    elif command == "events":
        return _query_events(args, ctx)
    elif command == "describe":
        return _query_describe(args, ctx)
    elif command == "stats":
        return format_stats(ctx.song)
    elif command == "status":
        return _query_status(ctx)
    elif command == "find":
        return _query_find(args, ctx)
    elif command == "piano-roll":
        return _query_piano_roll(args, ctx)
    elif command == "history":
        return _query_history(args, ctx.event_log)
    elif command == "diff":
        return _query_diff(args, ctx.event_log)
    elif command == "instruments":
        return _query_instruments(args, ctx)
    else:
        return f"! Unknown query: {command!r}\n  try: map, tracks, events, describe, stats, find, piano-roll, history, instruments"


def _query_events(args: str, ctx: OpContext) -> str:
    parts = args.strip().split()
    if not parts:
        return "! Missing track name.\n  try: events Piano or events Piano 1.1-4.4"

    track_name = parts[0]

    start_tick = None
    end_tick = None
    if len(parts) > 1:
        range_str = parts[1]
        range_parts = range_str.split("-")
        if len(range_parts) == 2:
            try:
                start_tick = parse_position(
                    range_parts[0], ctx.song.time_signatures, ctx.song.ppqn
                )
                end_tick = parse_position(
                    range_parts[1], ctx.song.time_signatures, ctx.song.ppqn
                )
            except ValueError as e:
                return f"! Invalid range: {e}"

    if track_name in ("*", "all"):
        sections = []
        for t_id in ctx.song.track_order:
            track = ctx.song.tracks.get(t_id)
            if track:
                header = f"--- {track.name} ---"
                body = format_events(track, ctx.song, start_tick, end_tick)
                sections.append(f"{header}\n{body}")
        return "\n".join(sections) if sections else "No tracks."

    track = ctx.song.get_track_by_name(track_name)
    if not track:
        suggestion = suggest_track_name(ctx.song, track_name)
        msg = f"Track '{track_name}' not found"
        if suggestion:
            msg += f"\n  try: {suggestion}"
        return f"! {msg}"

    return format_events(track, ctx.song, start_tick, end_tick)


def _query_describe(args: str, ctx: OpContext) -> str:
    track_name = args.strip()
    if not track_name:
        return "! Missing track name.\n  try: describe Piano"

    track = ctx.song.get_track_by_name(track_name)
    if not track:
        suggestion = suggest_track_name(ctx.song, track_name)
        msg = f"Track '{track_name}' not found"
        if suggestion:
            msg += f"\n  try: {suggestion}"
        return f"! {msg}"

    return format_describe(track, ctx.song)


def _query_status(ctx: OpContext) -> str:
    title = ctx.song.title
    path = ctx.song.file_path or "(unsaved)"
    n_events = ctx.event_log.cursor
    return f"Session: {title}\n  File: {path}\n  Events in log: {n_events}"


def _query_find(args: str, ctx: OpContext) -> str:
    pitch_str = args.strip()
    if not pitch_str:
        return "! Missing pitch.\n  try: find C4"

    try:
        pitch = parse_pitch(pitch_str)
    except ValueError as e:
        return f"! Invalid pitch: {e}"

    notes = ctx.registry.by_pitch(pitch.midi_number)
    if not notes:
        return f"No notes matching {pitch_str}."

    lines = [f"Found {len(notes)} note(s) matching {pitch_str}:"]
    for note in sorted(notes, key=lambda n: n.absolute_tick):
        pos = ticks_to_position(note.absolute_tick, ctx.song.time_signatures, ctx.song.ppqn)
        track = ctx.song.tracks.get(note.track_id)
        track_name = track.name if track else "?"
        lines.append(f"  {pos}  {track_name}  vel:{note.velocity}")

    return "\n".join(lines)


def _query_piano_roll(args: str, ctx: OpContext) -> str:
    parts = args.strip().split()
    if len(parts) < 2:
        return "! Usage: piano-roll TRACK M.B-M.B\n  try: piano-roll Piano 1.1-8.4"

    track_name = parts[0]
    track = ctx.song.get_track_by_name(track_name)
    if not track:
        suggestion = suggest_track_name(ctx.song, track_name)
        msg = f"Track '{track_name}' not found"
        if suggestion:
            msg += f"\n  try: {suggestion}"
        return f"! {msg}"

    range_str = parts[1]
    range_parts = range_str.split("-")
    if len(range_parts) != 2:
        return "! Invalid range format.\n  try: piano-roll Piano 1.1-8.4"

    try:
        start_tick = parse_position(
            range_parts[0], ctx.song.time_signatures, ctx.song.ppqn
        )
        end_tick = parse_position(
            range_parts[1], ctx.song.time_signatures, ctx.song.ppqn
        )
    except ValueError as e:
        return f"! Invalid range: {e}"

    return format_piano_roll(track, ctx.song, start_tick, end_tick)


def _query_history(args: str, event_log: EventLog) -> str:
    count_str = args.strip()
    try:
        count = int(count_str) if count_str else 5
    except ValueError:
        count = 5

    events = event_log.recent(count)
    if not events:
        return "No events in log."

    lines = [f"Last {len(events)} event(s):"]
    for ev in events:
        lines.append(f"  {ev.type}: {_format_event_summary(ev)}")
    return "\n".join(lines)


def _query_diff(args: str, event_log: EventLog) -> str:
    args = args.strip()
    if args.startswith("checkpoint:"):
        cp_name = args[len("checkpoint:"):]
    else:
        return "! Usage: diff checkpoint:NAME"

    events = event_log.events
    cp_idx = None
    for i, ev in enumerate(events):
        if isinstance(ev, CheckpointEvent) and ev.name == cp_name:
            cp_idx = i
            break

    if cp_idx is None:
        return f"! Checkpoint '{cp_name}' not found."

    post_events = [e for e in events[cp_idx + 1:event_log.cursor]
                   if not isinstance(e, CheckpointEvent)]
    if not post_events:
        return f"No changes since checkpoint '{cp_name}'."

    lines = [f"Changes since checkpoint '{cp_name}' ({len(post_events)}):"]
    for ev in post_events:
        lines.append(f"  {ev.type}: {_format_event_summary(ev)}")
    return "\n".join(lines)


def _format_event_summary(ev: object) -> str:
    """One-line summary of an event for history/diff output."""
    if hasattr(ev, "note_id"):
        track_id = getattr(ev, "track_id", "?")
        note_id = getattr(ev, "note_id", "?")
        return f"track={track_id[:6]} note={note_id[:6]}"
    if hasattr(ev, "track_id"):
        return f"track={getattr(ev, 'track_id', '?')[:6]}"
    if hasattr(ev, "new_bpm"):
        return f"{getattr(ev, 'new_bpm', 0):.0f} BPM"
    if hasattr(ev, "text"):
        return f"'{getattr(ev, 'text', '')}'"
    if hasattr(ev, "new_numerator"):
        return f"{getattr(ev, 'new_numerator')}/{getattr(ev, 'new_denominator')}"
    return ""


def _query_instruments(args: str, ctx: OpContext) -> str:
    """List available instruments, optionally filtered by name substring."""
    if ctx.instrument_registry is None:
        return "! Instrument registry not available."

    filter_str = args.strip().lower() if args.strip() else None
    source_filter = None

    # Support source: prefix filter
    if filter_str and filter_str.startswith("source:"):
        source_filter = filter_str[7:]
        filter_str = None

    specs = ctx.instrument_registry.list_instruments(source=source_filter)
    if filter_str:
        specs = [s for s in specs if filter_str in s.name]

    if not specs:
        return "No instruments found."

    lines = [f"Instruments ({len(specs)}):"]
    for s in specs:
        bank_str = ""
        if s.bank_msb != 0 or s.bank_lsb != 0:
            bank_str = f" bank:{s.bank_msb}.{s.bank_lsb}"
        source_str = f" [{s.source}]" if s.source != "gm" else ""
        lines.append(f"  {s.name}  program:{s.program}{bank_str}{source_str}")
    return "\n".join(lines)
