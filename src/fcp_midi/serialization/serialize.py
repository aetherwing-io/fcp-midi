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
        key_number = pretty_midi.key_name_to_key_number(f"{ks.key} {ks.mode}")
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
    """Serialize a :class:`Song` to a ``.mid`` file at *path*."""
    pm = song_to_pretty_midi(song)
    pm.write(path)
