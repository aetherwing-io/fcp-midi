"""Tests for Song <-> PrettyMIDI <-> .mid serialization round-trips."""

from __future__ import annotations

import os
import tempfile

import pytest

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
from fcp_midi.serialization.serialize import serialize, song_to_pretty_midi
from fcp_midi.serialization.deserialize import deserialize, pretty_midi_to_song


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TICK_TOLERANCE = 2  # ticks of rounding tolerance for float conversion


def _make_pitch(midi_number: int) -> Pitch:
    """Build a Pitch from a MIDI number (sharp spelling)."""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    raw = names[midi_number % 12]
    octave = (midi_number // 12) - 1
    if "#" in raw:
        return Pitch(name=raw[0], accidental="#", octave=octave, midi_number=midi_number)
    return Pitch(name=raw, accidental="", octave=octave, midi_number=midi_number)


def _build_test_song() -> Song:
    """Create a Song with multiple tracks, notes, CCs, pitch bends, markers."""
    song = Song.create(
        title="Test Song",
        tempo=120.0,
        time_sig=(4, 4),
        key="C major",
        ppqn=480,
    )

    # Piano track
    piano = song.add_track("Piano", instrument="acoustic-grand-piano", program=0, channel=0)
    song.add_note(piano.id, _make_pitch(60), absolute_tick=0, duration_ticks=480, velocity=100)
    song.add_note(piano.id, _make_pitch(64), absolute_tick=480, duration_ticks=480, velocity=90)
    song.add_note(piano.id, _make_pitch(67), absolute_tick=960, duration_ticks=480, velocity=80)
    song.add_cc(piano.id, controller=7, value=100, absolute_tick=0)  # volume
    song.add_cc(piano.id, controller=10, value=64, absolute_tick=0)  # pan
    song.add_pitch_bend(piano.id, value=0, absolute_tick=0)
    song.add_pitch_bend(piano.id, value=4096, absolute_tick=240)

    # Bass track
    bass = song.add_track("Bass", instrument="acoustic-bass", program=32, channel=1)
    song.add_note(bass.id, _make_pitch(36), absolute_tick=0, duration_ticks=960, velocity=90)
    song.add_note(bass.id, _make_pitch(43), absolute_tick=960, duration_ticks=960, velocity=85)

    # Marker
    song.add_marker("Intro", absolute_tick=0)
    song.add_marker("Chorus", absolute_tick=1920)

    return song


# ---------------------------------------------------------------------------
# Test: serialize produces a valid .mid file
# ---------------------------------------------------------------------------

class TestSerialize:
    def test_serialize_creates_nonempty_file(self, tmp_path):
        song = _build_test_song()
        path = str(tmp_path / "output.mid")
        serialize(song, path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    def test_song_to_pretty_midi_instruments(self):
        song = _build_test_song()
        pm = song_to_pretty_midi(song)
        assert len(pm.instruments) == 2
        assert pm.instruments[0].name == "Piano"
        assert pm.instruments[0].program == 0
        assert pm.instruments[1].name == "Bass"
        assert pm.instruments[1].program == 32

    def test_song_to_pretty_midi_notes(self):
        song = _build_test_song()
        pm = song_to_pretty_midi(song)
        piano_inst = pm.instruments[0]
        assert len(piano_inst.notes) == 3
        pitches = sorted(n.pitch for n in piano_inst.notes)
        assert pitches == [60, 64, 67]

    def test_song_to_pretty_midi_control_changes(self):
        song = _build_test_song()
        pm = song_to_pretty_midi(song)
        piano_inst = pm.instruments[0]
        assert len(piano_inst.control_changes) == 2
        cc_numbers = sorted(cc.number for cc in piano_inst.control_changes)
        assert cc_numbers == [7, 10]

    def test_song_to_pretty_midi_pitch_bends(self):
        song = _build_test_song()
        pm = song_to_pretty_midi(song)
        piano_inst = pm.instruments[0]
        assert len(piano_inst.pitch_bends) == 2

    def test_song_to_pretty_midi_time_signature(self):
        song = _build_test_song()
        pm = song_to_pretty_midi(song)
        assert len(pm.time_signature_changes) == 1
        ts = pm.time_signature_changes[0]
        assert ts.numerator == 4
        assert ts.denominator == 4

    def test_song_to_pretty_midi_key_signature(self):
        song = _build_test_song()
        pm = song_to_pretty_midi(song)
        assert len(pm.key_signature_changes) == 1

    def test_song_to_pretty_midi_markers(self):
        song = _build_test_song()
        pm = song_to_pretty_midi(song)
        assert len(pm.text_events) == 2
        texts = sorted(te.text for te in pm.text_events)
        assert texts == ["Chorus", "Intro"]

    def test_song_to_pretty_midi_tempo(self):
        song = _build_test_song()
        pm = song_to_pretty_midi(song)
        times, tempi = pm.get_tempo_changes()
        assert len(tempi) >= 1
        assert abs(tempi[0] - 120.0) < 0.01


# ---------------------------------------------------------------------------
# Test: deserialize reads a .mid file back
# ---------------------------------------------------------------------------

class TestDeserialize:
    def test_deserialize_preserves_file_path(self, tmp_path):
        song = _build_test_song()
        path = str(tmp_path / "test.mid")
        serialize(song, path)
        loaded = deserialize(path)
        assert loaded.file_path == path

    def test_deserialize_track_count(self, tmp_path):
        song = _build_test_song()
        path = str(tmp_path / "test.mid")
        serialize(song, path)
        loaded = deserialize(path)
        assert len(loaded.tracks) == 2

    def test_deserialize_tempo(self, tmp_path):
        song = _build_test_song()
        path = str(tmp_path / "test.mid")
        serialize(song, path)
        loaded = deserialize(path)
        assert len(loaded.tempo_map) >= 1
        assert abs(loaded.tempo_map[0].bpm - 120.0) < 0.01

    def test_deserialize_ppqn(self, tmp_path):
        song = _build_test_song()
        path = str(tmp_path / "test.mid")
        serialize(song, path)
        loaded = deserialize(path)
        assert loaded.ppqn == 480


# ---------------------------------------------------------------------------
# Test: full round-trip fidelity
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def _round_trip(self, song: Song) -> Song:
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            path = f.name
        try:
            serialize(song, path)
            return deserialize(path)
        finally:
            os.unlink(path)

    def test_note_pitches_survive(self):
        song = _build_test_song()
        loaded = self._round_trip(song)
        # Gather all MIDI note numbers from the original and loaded songs.
        orig_pitches = set()
        for t in song.tracks.values():
            for n in t.notes.values():
                orig_pitches.add(n.pitch.midi_number)
        loaded_pitches = set()
        for t in loaded.tracks.values():
            for n in t.notes.values():
                loaded_pitches.add(n.pitch.midi_number)
        assert orig_pitches == loaded_pitches

    def test_note_velocities_survive(self):
        song = _build_test_song()
        loaded = self._round_trip(song)
        orig_vels = sorted(
            n.velocity for t in song.tracks.values() for n in t.notes.values()
        )
        loaded_vels = sorted(
            n.velocity for t in loaded.tracks.values() for n in t.notes.values()
        )
        assert orig_vels == loaded_vels

    def test_note_timing_approximate(self):
        """Note start ticks should be within TICK_TOLERANCE of originals."""
        song = _build_test_song()
        loaded = self._round_trip(song)

        orig_ticks = sorted(
            n.absolute_tick for t in song.tracks.values() for n in t.notes.values()
        )
        loaded_ticks = sorted(
            n.absolute_tick for t in loaded.tracks.values() for n in t.notes.values()
        )
        assert len(orig_ticks) == len(loaded_ticks)
        for orig, got in zip(orig_ticks, loaded_ticks):
            assert abs(orig - got) <= TICK_TOLERANCE, (
                f"Tick mismatch: orig={orig}, got={got}"
            )

    def test_note_durations_approximate(self):
        """Note durations should be within TICK_TOLERANCE of originals."""
        song = _build_test_song()
        loaded = self._round_trip(song)

        orig_durs = sorted(
            n.duration_ticks for t in song.tracks.values() for n in t.notes.values()
        )
        loaded_durs = sorted(
            n.duration_ticks for t in loaded.tracks.values() for n in t.notes.values()
        )
        assert len(orig_durs) == len(loaded_durs)
        for orig, got in zip(orig_durs, loaded_durs):
            assert abs(orig - got) <= TICK_TOLERANCE, (
                f"Duration mismatch: orig={orig}, got={got}"
            )

    def test_track_names_survive(self):
        song = _build_test_song()
        loaded = self._round_trip(song)
        orig_names = sorted(t.name for t in song.tracks.values())
        loaded_names = sorted(t.name for t in loaded.tracks.values())
        assert orig_names == loaded_names

    def test_track_programs_survive(self):
        song = _build_test_song()
        loaded = self._round_trip(song)
        orig_programs = sorted(t.program or 0 for t in song.tracks.values())
        loaded_programs = sorted(t.program or 0 for t in loaded.tracks.values())
        assert orig_programs == loaded_programs

    def test_control_changes_survive(self):
        song = _build_test_song()
        loaded = self._round_trip(song)
        orig_ccs = sorted(
            (cc.controller, cc.value)
            for t in song.tracks.values()
            for cc in t.control_changes.values()
        )
        loaded_ccs = sorted(
            (cc.controller, cc.value)
            for t in loaded.tracks.values()
            for cc in t.control_changes.values()
        )
        assert orig_ccs == loaded_ccs

    def test_pitch_bends_survive(self):
        song = _build_test_song()
        loaded = self._round_trip(song)
        orig_pbs = sorted(
            pb.value for t in song.tracks.values() for pb in t.pitch_bends.values()
        )
        loaded_pbs = sorted(
            pb.value for t in loaded.tracks.values() for pb in t.pitch_bends.values()
        )
        assert orig_pbs == loaded_pbs

    def test_time_signature_survives(self):
        song = _build_test_song()
        loaded = self._round_trip(song)
        assert len(loaded.time_signatures) >= 1
        ts = loaded.time_signatures[0]
        assert ts.numerator == 4
        assert ts.denominator == 4

    def test_key_signature_survives(self):
        song = _build_test_song()
        loaded = self._round_trip(song)
        assert len(loaded.key_signatures) >= 1
        ks = loaded.key_signatures[0]
        assert ks.key == "C"
        assert ks.mode == "major"

    def test_markers_survive(self):
        song = _build_test_song()
        loaded = self._round_trip(song)
        orig_texts = sorted(m.text for m in song.markers)
        loaded_texts = sorted(m.text for m in loaded.markers)
        assert orig_texts == loaded_texts

    def test_tempo_survives(self):
        song = _build_test_song()
        loaded = self._round_trip(song)
        assert len(loaded.tempo_map) >= 1
        assert abs(loaded.tempo_map[0].bpm - 120.0) < 0.01


# ---------------------------------------------------------------------------
# Test: empty song
# ---------------------------------------------------------------------------

class TestEmptySong:
    def test_empty_song_serializes(self, tmp_path):
        song = Song.create(title="Empty")
        path = str(tmp_path / "empty.mid")
        serialize(song, path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    def test_empty_song_round_trips(self, tmp_path):
        song = Song.create(title="Empty")
        path = str(tmp_path / "empty.mid")
        serialize(song, path)
        loaded = deserialize(path)
        assert loaded.ppqn == song.ppqn
        assert len(loaded.tracks) == 0


# ---------------------------------------------------------------------------
# Test: drums (channel 9)
# ---------------------------------------------------------------------------

class TestDrums:
    def test_drum_track_round_trip(self, tmp_path):
        song = Song.create(title="Drums Test", tempo=120.0)
        drums = song.add_track("Drums", program=0, channel=9)
        # Kick on MIDI 36, snare on 38, hi-hat on 42
        song.add_note(drums.id, _make_pitch(36), absolute_tick=0, duration_ticks=120, velocity=100)
        song.add_note(drums.id, _make_pitch(38), absolute_tick=480, duration_ticks=120, velocity=95)
        song.add_note(drums.id, _make_pitch(42), absolute_tick=0, duration_ticks=60, velocity=80)
        song.add_note(drums.id, _make_pitch(42), absolute_tick=240, duration_ticks=60, velocity=75)

        path = str(tmp_path / "drums.mid")
        serialize(song, path)
        loaded = deserialize(path)

        assert len(loaded.tracks) == 1
        drum_track = list(loaded.tracks.values())[0]
        assert drum_track.channel == 9
        assert len(drum_track.notes) == 4
        loaded_pitches = sorted(n.pitch.midi_number for n in drum_track.notes.values())
        assert loaded_pitches == [36, 38, 42, 42]

    def test_drum_instrument_is_drum_flag(self, tmp_path):
        song = Song.create(title="Drums Flag", tempo=120.0)
        drums = song.add_track("Kit", program=0, channel=9)
        song.add_note(drums.id, _make_pitch(36), absolute_tick=0, duration_ticks=120, velocity=100)

        pm = song_to_pretty_midi(song)
        assert pm.instruments[0].is_drum is True


# ---------------------------------------------------------------------------
# Test: key signatures
# ---------------------------------------------------------------------------

class TestKeySignatures:
    @pytest.mark.parametrize("key,mode", [
        ("C", "major"),
        ("G", "major"),
        ("D", "minor"),
        ("Bb", "major"),
        ("F#", "minor"),
    ])
    def test_key_signature_round_trip(self, key, mode, tmp_path):
        song = Song.create(title="Key Test", key=f"{key} {mode}")
        # Need at least one instrument for pretty_midi to write properly
        t = song.add_track("Lead", program=0, channel=0)
        song.add_note(t.id, _make_pitch(60), absolute_tick=0, duration_ticks=480, velocity=80)

        path = str(tmp_path / "key.mid")
        serialize(song, path)
        loaded = deserialize(path)

        assert len(loaded.key_signatures) >= 1
        ks = loaded.key_signatures[0]
        assert ks.key == key
        assert ks.mode == mode


# ---------------------------------------------------------------------------
# Test: different time signatures
# ---------------------------------------------------------------------------

class TestTimeSignatures:
    @pytest.mark.parametrize("num,den", [
        (3, 4),
        (6, 8),
        (5, 4),
        (7, 8),
    ])
    def test_time_signature_round_trip(self, num, den, tmp_path):
        song = Song.create(title="TS Test", time_sig=(num, den))
        t = song.add_track("Lead", program=0, channel=0)
        song.add_note(t.id, _make_pitch(60), absolute_tick=0, duration_ticks=480, velocity=80)

        path = str(tmp_path / "ts.mid")
        serialize(song, path)
        loaded = deserialize(path)

        assert len(loaded.time_signatures) >= 1
        ts = loaded.time_signatures[0]
        assert ts.numerator == num
        assert ts.denominator == den


# ---------------------------------------------------------------------------
# Test: different tempos
# ---------------------------------------------------------------------------

class TestTempo:
    @pytest.mark.parametrize("bpm", [60.0, 90.0, 140.0, 200.0])
    def test_tempo_round_trip(self, bpm, tmp_path):
        song = Song.create(title="Tempo Test", tempo=bpm)
        t = song.add_track("Lead", program=0, channel=0)
        song.add_note(t.id, _make_pitch(60), absolute_tick=0, duration_ticks=480, velocity=80)

        path = str(tmp_path / "tempo.mid")
        serialize(song, path)
        loaded = deserialize(path)

        assert len(loaded.tempo_map) >= 1
        assert abs(loaded.tempo_map[0].bpm - bpm) < 0.01


# ---------------------------------------------------------------------------
# Test: pitch computation from MIDI number
# ---------------------------------------------------------------------------

class TestPitchConversion:
    def test_middle_c(self):
        from fcp_midi.serialization.deserialize import _midi_number_to_pitch
        p = _midi_number_to_pitch(60)
        assert p.name == "C"
        assert p.accidental == ""
        assert p.octave == 4
        assert p.midi_number == 60

    def test_concert_a(self):
        from fcp_midi.serialization.deserialize import _midi_number_to_pitch
        p = _midi_number_to_pitch(69)
        assert p.name == "A"
        assert p.accidental == ""
        assert p.octave == 4
        assert p.midi_number == 69

    def test_f_sharp_3(self):
        from fcp_midi.serialization.deserialize import _midi_number_to_pitch
        p = _midi_number_to_pitch(54)
        assert p.name == "F"
        assert p.accidental == "#"
        assert p.octave == 3
        assert p.midi_number == 54

    @pytest.mark.parametrize("midi_num", range(0, 128))
    def test_all_midi_numbers_valid(self, midi_num):
        from fcp_midi.serialization.deserialize import _midi_number_to_pitch
        p = _midi_number_to_pitch(midi_num)
        assert p.midi_number == midi_num
        assert p.name in ["C", "D", "E", "F", "G", "A", "B"]
        assert p.accidental in ["", "#"]
