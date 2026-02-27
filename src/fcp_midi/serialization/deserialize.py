"""Deserialize a .mid file into a Song model via PrettyMIDI.

Usage::

    from fcp_midi.serialization.deserialize import deserialize, pretty_midi_to_song

    song = deserialize("/path/to/file.mid")
    song = pretty_midi_to_song(pm)
"""

from __future__ import annotations

import uuid

import pretty_midi

from fcp_midi.model.song import (
    ControlChange,
    KeySignature,
    Marker,
    Note,
    Pitch,
    PitchBend,
    Song,
    TempoChange,
    TimeSignature,
    Track,
)
from fcp_midi.model.timing import seconds_to_ticks
from fcp_midi.lib.gm_instruments import program_to_instrument


# Note name lookup table indexed by (midi_number % 12).
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Names that are "sharp" variants (have an accidental).
_ACCIDENTAL_MAP: dict[str, tuple[str, str]] = {
    "C": ("C", ""),
    "C#": ("C", "#"),
    "D": ("D", ""),
    "D#": ("D", "#"),
    "E": ("E", ""),
    "F": ("F", ""),
    "F#": ("F", "#"),
    "G": ("G", ""),
    "G#": ("G", "#"),
    "A": ("A", ""),
    "A#": ("A", "#"),
    "B": ("B", ""),
}


def _id() -> str:
    return uuid.uuid4().hex[:8]


def _midi_number_to_pitch(midi_number: int) -> Pitch:
    """Convert a MIDI note number (0-127) to a :class:`Pitch`."""
    note_index = midi_number % 12
    octave = (midi_number // 12) - 1
    raw_name = _NOTE_NAMES[note_index]
    name, accidental = _ACCIDENTAL_MAP[raw_name]
    return Pitch(
        name=name,
        accidental=accidental,
        octave=octave,
        midi_number=midi_number,
    )


def _parse_key_name(key_name: str) -> tuple[str, str]:
    """Parse a pretty_midi key name like ``'C Major'`` or ``'F# minor'``.

    Returns ``(key, mode)`` where key is e.g. ``'C'``, ``'F#'``, ``'Bb'``
    and mode is ``'major'`` or ``'minor'``.
    """
    # pretty_midi returns names like "C Major", "Db Major", "F# minor"
    parts = key_name.split()
    key = parts[0] if parts else "C"
    mode = parts[1].lower() if len(parts) > 1 else "major"
    return key, mode


def pretty_midi_to_song(pm: pretty_midi.PrettyMIDI) -> Song:
    """Convert a :class:`pretty_midi.PrettyMIDI` object to a :class:`Song`."""
    ppqn = pm.resolution

    # --- Tempo map ---
    tempo_times, tempo_bpms = pm.get_tempo_changes()
    tempo_map: list[TempoChange] = []
    for t, bpm in zip(tempo_times, tempo_bpms):
        tick = seconds_to_ticks(
            float(t),
            tempo_map if tempo_map else [TempoChange(absolute_tick=0, bpm=float(bpm))],
            ppqn,
        )
        # For the very first tempo, tick should be 0.
        if not tempo_map:
            tick = 0
        tempo_map.append(TempoChange(absolute_tick=tick, bpm=float(bpm)))

    if not tempo_map:
        tempo_map = [TempoChange(absolute_tick=0, bpm=120.0)]

    # --- Time signatures ---
    time_signatures: list[TimeSignature] = []
    for ts in pm.time_signature_changes:
        tick = seconds_to_ticks(ts.time, tempo_map, ppqn)
        time_signatures.append(
            TimeSignature(
                absolute_tick=tick,
                numerator=ts.numerator,
                denominator=ts.denominator,
            )
        )

    # --- Key signatures ---
    key_signatures: list[KeySignature] = []
    for ks in pm.key_signature_changes:
        tick = seconds_to_ticks(ks.time, tempo_map, ppqn)
        key_name = pretty_midi.key_number_to_key_name(ks.key_number)
        key, mode = _parse_key_name(key_name)
        key_signatures.append(
            KeySignature(absolute_tick=tick, key=key, mode=mode)
        )

    # --- Markers (text events) ---
    markers: list[Marker] = []
    for te in pm.text_events:
        tick = seconds_to_ticks(te.time, tempo_map, ppqn)
        markers.append(Marker(absolute_tick=tick, text=te.text))

    # --- Tracks ---
    song = Song(
        id=_id(),
        title="Imported",
        ppqn=ppqn,
        tempo_map=tempo_map,
        time_signatures=time_signatures,
        key_signatures=key_signatures,
        markers=markers,
    )

    # Channel assignment: drum instruments get channel 9, others get
    # auto-assigned channels (skipping 9).
    next_channel = 0

    for inst in pm.instruments:
        if inst.is_drum:
            channel = 9
        else:
            # Skip channel 9 for non-drum tracks.
            if next_channel == 9:
                next_channel = 10
            channel = next_channel
            next_channel += 1
            if next_channel > 15:
                next_channel = 0  # wrap around (unlikely for most files)

        track_id = _id()
        instrument_name = program_to_instrument(inst.program)
        track = Track(
            id=track_id,
            name=inst.name or instrument_name or f"Track {len(song.tracks) + 1}",
            channel=channel,
            instrument=instrument_name,
            program=inst.program,
        )

        # Detect bank select CCs (earliest CC#0 and CC#32)
        for cc in inst.control_changes:
            if cc.number == 0 and track.bank_msb is None:
                track.bank_msb = cc.value
            elif cc.number == 32 and track.bank_lsb is None:
                track.bank_lsb = cc.value

        # Notes
        for n in inst.notes:
            nid = _id()
            start_tick = seconds_to_ticks(n.start, tempo_map, ppqn)
            end_tick = seconds_to_ticks(n.end, tempo_map, ppqn)
            duration_ticks = max(1, end_tick - start_tick)
            pitch = _midi_number_to_pitch(n.pitch)
            note = Note(
                id=nid,
                track_id=track_id,
                pitch=pitch,
                absolute_tick=start_tick,
                duration_ticks=duration_ticks,
                velocity=n.velocity,
                channel=channel,
            )
            track.notes[nid] = note

        # Control changes
        for cc in inst.control_changes:
            cid = _id()
            tick = seconds_to_ticks(cc.time, tempo_map, ppqn)
            control_change = ControlChange(
                id=cid,
                track_id=track_id,
                absolute_tick=tick,
                controller=cc.number,
                value=cc.value,
                channel=channel,
            )
            track.control_changes[cid] = control_change

        # Pitch bends
        for pb in inst.pitch_bends:
            pid = _id()
            tick = seconds_to_ticks(pb.time, tempo_map, ppqn)
            pitch_bend = PitchBend(
                id=pid,
                track_id=track_id,
                absolute_tick=tick,
                value=pb.pitch,
                channel=channel,
            )
            track.pitch_bends[pid] = pitch_bend

        song.tracks[track_id] = track
        song.track_order.append(track_id)

    return song


def deserialize(path: str) -> Song:
    """Load a ``.mid`` file and return a :class:`Song`."""
    pm = pretty_midi.PrettyMIDI(path)
    song = pretty_midi_to_song(pm)
    song.file_path = path
    return song
