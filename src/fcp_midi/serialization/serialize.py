"""Serialize a Song model to PrettyMIDI and write to a .mid file.

Usage::

    from fcp_midi.serialization.serialize import serialize, song_to_pretty_midi

    serialize(song, "/path/to/output.mid")
    pm = song_to_pretty_midi(song)
"""

from __future__ import annotations

import pretty_midi
from pretty_midi.containers import Text

from fcp_midi.model.song import Song
from fcp_midi.model.timing import ticks_to_seconds


def song_to_pretty_midi(song: Song) -> pretty_midi.PrettyMIDI:
    """Convert a :class:`Song` to a :class:`pretty_midi.PrettyMIDI` object.

    Limitations:
        Only the first tempo in ``song.tempo_map`` is used as the initial
        tempo.  Additional tempo changes are currently not serialized because
        PrettyMIDI does not expose a public API for inserting SetTempo meta
        messages after construction.
    """
    initial_tempo = song.tempo_map[0].bpm if song.tempo_map else 120.0
    pm = pretty_midi.PrettyMIDI(
        initial_tempo=initial_tempo,
        resolution=song.ppqn,
    )

    tempo_map = song.tempo_map
    ppqn = song.ppqn

    # --- Time signatures ---
    for ts in song.time_signatures:
        time_sec = ticks_to_seconds(ts.absolute_tick, tempo_map, ppqn)
        pm.time_signature_changes.append(
            pretty_midi.TimeSignature(ts.numerator, ts.denominator, time_sec)
        )

    # --- Key signatures ---
    for ks in song.key_signatures:
        time_sec = ticks_to_seconds(ks.absolute_tick, tempo_map, ppqn)
        # Normalize key name: handle "Dm" -> "D minor", "Cm" -> "C minor" etc.
        key_name = ks.key
        mode = ks.mode
        if len(key_name) >= 2 and key_name[-1] == 'm' and key_name[-2:] not in ('#m',):
            # "Dm" -> key="D", mode="minor"; but keep "D#m" check safe
            if key_name.endswith('m') and not key_name.endswith('#') and not key_name.endswith('b'):
                key_name = key_name[:-1]
                mode = "minor"
        key_number = pretty_midi.key_name_to_key_number(f"{key_name} {mode}")
        pm.key_signature_changes.append(
            pretty_midi.KeySignature(key_number, time_sec)
        )

    # --- Markers (as text events) ---
    for marker in song.markers:
        time_sec = ticks_to_seconds(marker.absolute_tick, tempo_map, ppqn)
        pm.text_events.append(Text(marker.text, time_sec))

    # --- Tracks / Instruments ---
    for track_id in song.track_order:
        track = song.tracks[track_id]
        is_drum = track.channel == 9
        instrument = pretty_midi.Instrument(
            program=track.program if track.program is not None else 0,
            is_drum=is_drum,
            name=track.name,
        )

        # Notes
        for note in track.notes.values():
            start_sec = ticks_to_seconds(note.absolute_tick, tempo_map, ppqn)
            end_sec = ticks_to_seconds(
                note.absolute_tick + note.duration_ticks, tempo_map, ppqn
            )
            instrument.notes.append(
                pretty_midi.Note(
                    velocity=note.velocity,
                    pitch=note.pitch.midi_number,
                    start=start_sec,
                    end=end_sec,
                )
            )

        # Control changes
        for cc in track.control_changes.values():
            time_sec = ticks_to_seconds(cc.absolute_tick, tempo_map, ppqn)
            instrument.control_changes.append(
                pretty_midi.ControlChange(
                    number=cc.controller,
                    value=cc.value,
                    time=time_sec,
                )
            )

        # Pitch bends
        for pb in track.pitch_bends.values():
            time_sec = ticks_to_seconds(pb.absolute_tick, tempo_map, ppqn)
            instrument.pitch_bends.append(
                pretty_midi.PitchBend(
                    pitch=pb.value,
                    time=time_sec,
                )
            )

        pm.instruments.append(instrument)

    return pm


def serialize(song: Song, path: str) -> None:
    """Serialize a :class:`Song` to a ``.mid`` file at *path*.

    If the song has bank select or multiple tempo changes, they are
    injected into the MIDI file via mido post-processing.
    """
    pm = song_to_pretty_midi(song)
    pm.write(path)

    # Inject bank select messages for tracks that have them
    has_bank = any(
        t.bank_msb is not None or t.bank_lsb is not None
        for t in song.tracks.values()
    )
    if has_bank:
        try:
            _inject_bank_select(path, song)
        except Exception:
            pass  # Fallback: file already written without bank select

    # Inject additional tempo changes if the song has more than one
    if len(song.tempo_map) > 1:
        try:
            _inject_tempo_changes(path, song)
        except Exception:
            pass  # Fallback: single-tempo file already written


def _inject_bank_select(path: str, song: Song) -> None:
    """Post-process a MIDI file to add bank select CC messages.

    PrettyMIDI does not support bank select, so we use mido to insert
    CC#0 (Bank MSB) and CC#32 (Bank LSB) at tick 0 before any notes.
    """
    import mido

    mid = mido.MidiFile(path)

    # Build a mapping from track index to bank info.
    # PrettyMIDI writes tracks in song.track_order order, but the first
    # mido track (index 0) is the tempo/meta track for type-1 files.
    track_offset = 1 if mid.type == 1 and len(mid.tracks) > len(song.track_order) else 0

    for i, tid in enumerate(song.track_order):
        track = song.tracks.get(tid)
        if not track:
            continue
        if track.bank_msb is None and track.bank_lsb is None:
            continue

        mido_idx = i + track_offset
        if mido_idx >= len(mid.tracks):
            continue

        mido_track = mid.tracks[mido_idx]

        # Convert to absolute ticks for insertion
        abs_events: list[tuple[int, mido.Message]] = []
        abs_tick = 0
        for msg in mido_track:
            abs_tick += msg.time
            abs_events.append((abs_tick, msg))

        # Insert bank select CCs at tick 0 (before program change)
        new_msgs: list[tuple[int, mido.Message]] = []
        ch = track.channel
        if track.bank_msb is not None:
            new_msgs.append((0, mido.Message(
                "control_change", channel=ch, control=0, value=track.bank_msb, time=0
            )))
        if track.bank_lsb is not None:
            new_msgs.append((0, mido.Message(
                "control_change", channel=ch, control=32, value=track.bank_lsb, time=0
            )))

        # Merge and sort (stable: bank select stays before existing tick-0 events)
        abs_events = new_msgs + abs_events
        abs_events.sort(key=lambda x: x[0])

        # Convert back to delta times
        prev_tick = 0
        new_track = mido.MidiTrack()
        for abs_t, msg in abs_events:
            msg = msg.copy(time=abs_t - prev_tick)
            new_track.append(msg)
            prev_tick = abs_t

        mid.tracks[mido_idx] = new_track

    mid.save(path)


def _inject_tempo_changes(path: str, song: Song) -> None:
    """Post-process a MIDI file to add multiple SetTempo meta messages."""
    import mido

    mid = mido.MidiFile(path)

    # Collect existing set_tempo message ticks to avoid duplicates
    existing_tempo_ticks: set[int] = set()
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == "set_tempo":
                existing_tempo_ticks.add(abs_tick)

    # Build new tempo events (skip the first — already set by PrettyMIDI)
    new_tempos = []
    for tc in song.tempo_map[1:]:
        if tc.absolute_tick not in existing_tempo_ticks:
            new_tempos.append((tc.absolute_tick, tc.bpm))

    if not new_tempos:
        return

    # Insert into the first track (tempo track for type-1 MIDI)
    if not mid.tracks:
        return

    tempo_track = mid.tracks[0]

    # Rebuild the track with new events merged in
    # First, convert to absolute ticks
    abs_events: list[tuple[int, mido.Message]] = []
    abs_tick = 0
    for msg in tempo_track:
        abs_tick += msg.time
        abs_events.append((abs_tick, msg))

    # Add new tempo messages
    for tick, bpm in new_tempos:
        tempo_msg = mido.MetaMessage(
            "set_tempo", tempo=mido.bpm2tempo(bpm), time=0
        )
        abs_events.append((tick, tempo_msg))

    # Sort by absolute tick (stable sort keeps original order for ties)
    abs_events.sort(key=lambda x: x[0])

    # Convert back to delta times
    prev_tick = 0
    new_track = mido.MidiTrack()
    for abs_t, msg in abs_events:
        msg = msg.copy(time=abs_t - prev_tick)
        new_track.append(msg)
        prev_tick = abs_t

    mid.tracks[0] = new_track
    mid.save(path)
