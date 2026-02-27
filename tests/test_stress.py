"""Stress tests for scale and performance validation.

All tests are marked @pytest.mark.slow and can be run with:
    pytest tests/test_stress.py -v
"""

from __future__ import annotations

import os
import tempfile

import pytest

from fcp_midi.model.event_log import EventLog, NoteAdded
from fcp_midi.model.registry import Registry
from fcp_midi.model.song import Pitch, Song
from fcp_midi.server.intent import IntentLayer


def _c4() -> Pitch:
    return Pitch(name="C", accidental="", octave=4, midi_number=60)


def _song_with_n_notes(n: int, tracks: int = 1) -> Song:
    """Create a song with *n* notes spread across *tracks* tracks."""
    s = Song.create(title="Stress", tempo=120.0, time_sig=(4, 4))
    track_ids = []
    for i in range(tracks):
        t = s.add_track(f"Track{i}")
        track_ids.append(t.id)

    pitches = [
        Pitch(name="C", accidental="", octave=4, midi_number=60),
        Pitch(name="D", accidental="", octave=4, midi_number=62),
        Pitch(name="E", accidental="", octave=4, midi_number=64),
        Pitch(name="F", accidental="", octave=4, midi_number=65),
        Pitch(name="G", accidental="", octave=4, midi_number=67),
    ]
    for i in range(n):
        tid = track_ids[i % tracks]
        pitch = pitches[i % len(pitches)]
        s.add_note(tid, pitch, absolute_tick=i * 480, duration_ticks=480, velocity=80)
    return s


# -----------------------------------------------------------------------
# Registry scale
# -----------------------------------------------------------------------

@pytest.mark.slow
class TestRegistryScale:
    @pytest.mark.parametrize("n", [100, 500, 1000, 5000])
    def test_rebuild_consistency(self, n: int) -> None:
        """Registry.rebuild produces correct state at various scales."""
        s = _song_with_n_notes(n)
        reg = Registry()
        reg.rebuild(s)

        total = sum(len(reg.by_track(f"Track0")) for _ in [0])
        assert total == n

    @pytest.mark.parametrize("n", [100, 500, 1000, 5000])
    def test_incremental_matches_rebuild(self, n: int) -> None:
        """Incremental build matches rebuild at scale."""
        s = _song_with_n_notes(n)

        inc = Registry()
        for track in s.tracks.values():
            for note in track.notes.values():
                inc.add_note(note, track.name)

        full = Registry()
        full.rebuild(s)

        # Compare all notes
        assert len(inc.by_track("Track0")) == len(full.by_track("Track0"))
        assert set(n.id for n in inc.by_pitch(60)) == set(n.id for n in full.by_pitch(60))


# -----------------------------------------------------------------------
# Many tracks
# -----------------------------------------------------------------------

@pytest.mark.slow
class TestManyTracks:
    @pytest.mark.parametrize("track_count", [10, 25, 50])
    def test_many_tracks(self, track_count: int) -> None:
        """Song with many tracks handles correctly."""
        s = _song_with_n_notes(track_count * 10, tracks=track_count)
        reg = Registry()
        reg.rebuild(s)

        assert len(s.tracks) == track_count
        for i in range(track_count):
            notes = reg.by_track(f"Track{i}")
            assert len(notes) == 10


# -----------------------------------------------------------------------
# Deep undo
# -----------------------------------------------------------------------

@pytest.mark.slow
class TestDeepUndo:
    @pytest.mark.parametrize("depth", [50, 200, 500])
    def test_deep_undo(self, depth: int) -> None:
        """Undo/redo works correctly at depth."""
        s = Song.create(title="Deep", tempo=120.0, time_sig=(4, 4))
        t = s.add_track("Piano")
        log = EventLog()

        for i in range(depth):
            note = s.add_note(t.id, _c4(), absolute_tick=i * 480, duration_ticks=480)
            log.append(NoteAdded(track_id=t.id, note_id=note.id))

        assert log.cursor == depth

        # Undo all
        undone = log.undo(depth)
        assert len(undone) == depth
        assert log.cursor == 0

        # Redo all
        redone = log.redo(depth)
        assert len(redone) == depth
        assert log.cursor == depth


# -----------------------------------------------------------------------
# Serialization round-trip at scale
# -----------------------------------------------------------------------

@pytest.mark.slow
class TestSerializationScale:
    @pytest.mark.parametrize("n", [100, 500])
    def test_round_trip(self, n: int) -> None:
        """Serialize and deserialize preserves note count."""
        s = _song_with_n_notes(n)

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            path = f.name

        try:
            from fcp_midi.serialization.serialize import serialize
            from fcp_midi.serialization.deserialize import deserialize

            serialize(s, path)
            loaded = deserialize(path)

            original_notes = sum(len(t.notes) for t in s.tracks.values())
            loaded_notes = sum(len(t.notes) for t in loaded.tracks.values())
            assert loaded_notes == original_notes
        finally:
            os.unlink(path)

    def test_multi_tempo_round_trip(self) -> None:
        """Multi-tempo song serializes without error."""
        s = Song.create(title="MultiTempo", tempo=120.0, time_sig=(4, 4))
        t = s.add_track("Piano")
        s.add_note(t.id, _c4(), absolute_tick=0, duration_ticks=480)
        s.add_tempo(140.0, 1920)
        s.add_tempo(100.0, 3840)

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            path = f.name

        try:
            from fcp_midi.serialization.serialize import serialize
            serialize(s, path)
            # Verify file is valid by loading with mido
            import mido
            mid = mido.MidiFile(path)
            tempo_msgs = []
            for track in mid.tracks:
                for msg in track:
                    if msg.type == "set_tempo":
                        tempo_msgs.append(msg)
            # Should have at least the initial + 2 additional
            assert len(tempo_msgs) >= 3
        finally:
            os.unlink(path)


# -----------------------------------------------------------------------
# Batch through IntentLayer
# -----------------------------------------------------------------------

@pytest.mark.slow
class TestBatchScale:
    def test_batch_100_notes(self) -> None:
        """Add 100 notes in a single batch through IntentLayer."""
        il = IntentLayer()
        il.execute_session('new "Batch" tempo:120')
        il.execute_ops(["track add Piano instrument:acoustic-grand-piano"])

        ops = []
        for i in range(100):
            measure = i // 4 + 1
            beat = i % 4 + 1
            ops.append(f"note Piano C4 at:{measure}.{beat} dur:quarter vel:80")

        results = il.execute_ops(ops)
        # No errors
        errors = [r for r in results if r.startswith("!")]
        assert len(errors) == 0

        # All notes created
        assert il.song is not None
        piano = il.song.get_track_by_name("Piano")
        assert piano is not None
        assert len(piano.notes) == 100
