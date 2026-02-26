"""Compact response formatting for MIDI FCP tool outputs."""

from __future__ import annotations

from fcp_midi.model.song import Song, Track
from fcp_midi.model.timing import ticks_to_position, ticks_to_seconds


def format_result(
    success: bool,
    message: str,
    suggestion: str | None = None,
) -> str:
    """Format a mutation result line.

    Success: ``+ message``
    Error:   ``! message`` with optional ``  try: suggestion``
    """
    if success:
        return f"+ {message}"
    line = f"! {message}"
    if suggestion:
        line += f"\n  try: {suggestion}"
    return line


def format_query(content: str) -> str:
    """Pass-through for query content."""
    return content


def format_track_list(song: Song) -> str:
    """Format a compact track listing."""
    if not song.tracks:
        return "No tracks."
    lines: list[str] = []
    for idx, tid in enumerate(song.track_order, 1):
        track = song.tracks.get(tid)
        if not track:
            continue
        n_notes = len(track.notes)
        n_cc = len(track.control_changes)
        n_pb = len(track.pitch_bends)
        inst = track.instrument or "no instrument"
        flags = ""
        if track.mute:
            flags += " [MUTED]"
        if track.solo:
            flags += " [SOLO]"
        display_ch = track.channel + 1  # 1-indexed for display
        lines.append(
            f"  {idx}. {track.name} (ch:{display_ch}) "
            f"{inst} | {n_notes} notes, {n_cc} cc, {n_pb} bend{flags}"
        )
    header = f"Tracks ({len(lines)}):"
    return "\n".join([header] + lines)


def format_events(
    track: Track,
    song: Song,
    start_tick: int | None = None,
    end_tick: int | None = None,
) -> str:
    """Format events on a track within an optional tick range."""
    lines: list[str] = []

    # Collect and sort notes
    notes = sorted(track.notes.values(), key=lambda n: n.absolute_tick)
    for note in notes:
        if start_tick is not None and note.absolute_tick < start_tick:
            continue
        if end_tick is not None and note.absolute_tick >= end_tick:
            continue
        pos = ticks_to_position(note.absolute_tick, song.time_signatures, song.ppqn)
        pitch_str = f"{note.pitch.name}{note.pitch.accidental}{note.pitch.octave}"
        lines.append(f"  {pos}  {pitch_str:6s} vel:{note.velocity:3d} dur:{note.duration_ticks}")

    # Collect and sort CCs
    ccs = sorted(track.control_changes.values(), key=lambda c: c.absolute_tick)
    for cc in ccs:
        if start_tick is not None and cc.absolute_tick < start_tick:
            continue
        if end_tick is not None and cc.absolute_tick >= end_tick:
            continue
        pos = ticks_to_position(cc.absolute_tick, song.time_signatures, song.ppqn)
        lines.append(f"  {pos}  CC{cc.controller:3d}={cc.value:3d}")

    # Collect and sort pitch bends
    pbs = sorted(track.pitch_bends.values(), key=lambda p: p.absolute_tick)
    for pb in pbs:
        if start_tick is not None and pb.absolute_tick < start_tick:
            continue
        if end_tick is not None and pb.absolute_tick >= end_tick:
            continue
        pos = ticks_to_position(pb.absolute_tick, song.time_signatures, song.ppqn)
        lines.append(f"  {pos}  Bend={pb.value}")

    if not lines:
        return f"No events on {track.name} in range."

    header = f"Events on {track.name}:"
    return "\n".join([header] + lines)


def format_stats(song: Song) -> str:
    """Format song-level statistics."""
    n_tracks = len(song.tracks)
    n_notes = sum(len(t.notes) for t in song.tracks.values())
    n_cc = sum(len(t.control_changes) for t in song.tracks.values())
    n_pb = sum(len(t.pitch_bends) for t in song.tracks.values())
    total_events = n_notes + n_cc + n_pb

    tempo = song.tempo_map[0].bpm if song.tempo_map else 120.0
    ts = song.time_signatures[0] if song.time_signatures else None
    ts_str = f"{ts.numerator}/{ts.denominator}" if ts else "4/4"
    ks = song.key_signatures[0] if song.key_signatures else None
    ks_str = f"{ks.key} {ks.mode}" if ks else "none"

    # Compute duration
    max_tick = 0
    for t in song.tracks.values():
        for n in t.notes.values():
            end = n.absolute_tick + n.duration_ticks
            if end > max_tick:
                max_tick = end

    duration_secs = ticks_to_seconds(max_tick, song.tempo_map, song.ppqn)
    minutes = int(duration_secs) // 60
    seconds = duration_secs - minutes * 60

    # Estimate measures
    if ts:
        tpm = song.ppqn * 4 * ts.numerator // ts.denominator
        measures = max_tick // tpm if tpm else 0
    else:
        measures = max_tick // (song.ppqn * 4)

    lines = [
        f"Song: {song.title}",
        f"  Tempo: {tempo:.0f} BPM",
        f"  Time sig: {ts_str}",
        f"  Key: {ks_str}",
        f"  PPQN: {song.ppqn}",
        f"  Tracks: {n_tracks}",
        f"  Notes: {n_notes}",
        f"  CCs: {n_cc}",
        f"  Pitch bends: {n_pb}",
        f"  Total events: {total_events}",
        f"  Duration: {minutes}:{seconds:05.2f}",
        f"  Measures: {measures}",
    ]
    return "\n".join(lines)


def format_describe(track: Track, song: Song) -> str:
    """Format detailed track information."""
    n_notes = len(track.notes)
    inst = track.instrument or "none"
    prog = track.program if track.program is not None else "none"

    lines = [
        f"Track: {track.name}",
        f"  Channel: {track.channel + 1}",
        f"  Instrument: {inst} (program:{prog})",
        f"  Notes: {n_notes}",
        f"  CCs: {len(track.control_changes)}",
        f"  Pitch bends: {len(track.pitch_bends)}",
        f"  Muted: {track.mute}",
        f"  Solo: {track.solo}",
    ]

    # Pitch range
    if track.notes:
        notes_sorted = sorted(track.notes.values(), key=lambda n: n.pitch.midi_number)
        low = notes_sorted[0].pitch
        high = notes_sorted[-1].pitch
        lines.append(
            f"  Pitch range: {low.name}{low.accidental}{low.octave} - "
            f"{high.name}{high.accidental}{high.octave}"
        )

    # Velocity range
    if track.notes:
        vels = [n.velocity for n in track.notes.values()]
        lines.append(f"  Velocity range: {min(vels)}-{max(vels)}")

    # Time span
    if track.notes:
        notes_by_time = sorted(track.notes.values(), key=lambda n: n.absolute_tick)
        first_pos = ticks_to_position(
            notes_by_time[0].absolute_tick, song.time_signatures, song.ppqn
        )
        last_end = max(n.absolute_tick + n.duration_ticks for n in track.notes.values())
        last_pos = ticks_to_position(last_end, song.time_signatures, song.ppqn)
        lines.append(f"  Time span: {first_pos} - {last_pos}")

    return "\n".join(lines)


def format_piano_roll(
    track: Track,
    song: Song,
    start_tick: int,
    end_tick: int,
) -> str:
    """Format an ASCII piano-roll visualization.

    Shows a grid with pitches on the Y-axis and beats on the X-axis.
    Each character represents one beat subdivision.
    """
    notes = sorted(track.notes.values(), key=lambda n: n.absolute_tick)
    in_range = [
        n for n in notes
        if n.absolute_tick + n.duration_ticks > start_tick and n.absolute_tick < end_tick
    ]

    if not in_range:
        return f"No notes on {track.name} in range."

    # Determine pitch range
    midi_low = min(n.pitch.midi_number for n in in_range)
    midi_high = max(n.pitch.midi_number for n in in_range)

    # Expand range slightly for readability
    midi_low = max(0, midi_low - 1)
    midi_high = min(127, midi_high + 1)

    # Quantize to beat-level columns
    ts = song.time_signatures[0] if song.time_signatures else None
    denom = ts.denominator if ts else 4
    beat_ticks = song.ppqn * 4 // denom

    n_cols = max(1, (end_tick - start_tick) // beat_ticks)
    # Cap columns for readability
    if n_cols > 64:
        n_cols = 64
        beat_ticks = (end_tick - start_tick) // n_cols

    # Build grid
    rows = midi_high - midi_low + 1
    grid: list[list[str]] = [["." for _ in range(n_cols)] for _ in range(rows)]

    for note in in_range:
        row = midi_high - note.pitch.midi_number
        col_start = max(0, (note.absolute_tick - start_tick) // beat_ticks)
        note_end = note.absolute_tick + note.duration_ticks
        col_end = min(n_cols, (note_end - start_tick + beat_ticks - 1) // beat_ticks)
        for c in range(int(col_start), int(col_end)):
            if 0 <= c < n_cols:
                grid[row][c] = "#"

    # Render with pitch labels
    from fcp_midi.parser.pitch import _MIDI_TO_NOTE

    lines: list[str] = []
    for row_idx in range(rows):
        midi_num = midi_high - row_idx
        note_in_oct = midi_num % 12
        octave = (midi_num // 12) - 1
        name, acc = _MIDI_TO_NOTE[note_in_oct]
        label = f"{name}{acc}{octave}".ljust(5)
        lines.append(f"{label}|{''.join(grid[row_idx])}|")

    start_pos = ticks_to_position(start_tick, song.time_signatures, song.ppqn)
    end_pos = ticks_to_position(end_tick, song.time_signatures, song.ppqn)
    header = f"Piano roll: {track.name} ({start_pos} - {end_pos})"
    return "\n".join([header] + lines)


def format_map(song: Song) -> str:
    """Format a song overview / map."""
    lines: list[str] = []
    lines.append(f"Song: {song.title}")

    tempo = song.tempo_map[0].bpm if song.tempo_map else 120.0
    ts = song.time_signatures[0] if song.time_signatures else None
    ts_str = f"{ts.numerator}/{ts.denominator}" if ts else "4/4"
    ks = song.key_signatures[0] if song.key_signatures else None
    ks_str = f"{ks.key} {ks.mode}" if ks else ""

    meta_parts = [f"tempo:{tempo:.0f}", ts_str]
    if ks_str:
        meta_parts.append(ks_str)
    meta_parts.append(f"ppqn:{song.ppqn}")
    lines.append(f"  {' | '.join(meta_parts)}")

    if song.markers:
        markers_str = ", ".join(
            f"{m.text}@{ticks_to_position(m.absolute_tick, song.time_signatures, song.ppqn)}"
            for m in sorted(song.markers, key=lambda m: m.absolute_tick)
        )
        lines.append(f"  Markers: {markers_str}")

    # Track summaries
    if song.tracks:
        lines.append(f"  Tracks ({len(song.tracks)}):")
        for idx, tid in enumerate(song.track_order, 1):
            track = song.tracks.get(tid)
            if not track:
                continue
            n_notes = len(track.notes)
            inst = track.instrument or "---"
            flags = ""
            if track.mute:
                flags += " [M]"
            if track.solo:
                flags += " [S]"
            display_ch = track.channel + 1  # 1-indexed for display
            lines.append(f"    {idx}. {track.name} ch:{display_ch} {inst} ({n_notes} notes){flags}")
    else:
        lines.append("  No tracks.")

    lines.append(f"  {song.get_digest()}")
    return "\n".join(lines)
