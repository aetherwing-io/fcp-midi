"""Conformance tests for MidiAdapter — verifies it satisfies FcpDomainAdapter protocol."""

from __future__ import annotations

import os
import tempfile

import pytest

from fcp_core import EventLog as CoreEventLog, OpResult
from fcp_core import ParsedOp as GenericParsedOp, parse_op

from fcp_midi.adapter import MidiAdapter
from fcp_midi.model.event_log import NoteAdded
from fcp_midi.model.song import Pitch, Song


@pytest.fixture
def adapter() -> MidiAdapter:
    return MidiAdapter()


@pytest.fixture
def song(adapter: MidiAdapter) -> Song:
    return adapter.create_empty("Test Song", {"tempo": "120", "time-sig": "4/4"})


@pytest.fixture
def song_with_piano(adapter: MidiAdapter, song: Song) -> Song:
    """Song with a Piano track already added."""
    log = CoreEventLog()
    op = parse_op("track add Piano instrument:acoustic-grand-piano")
    assert isinstance(op, GenericParsedOp)
    result = adapter.dispatch_op(op, song, log)
    assert result.success, f"Failed to add track: {result.message}"
    return song


# -----------------------------------------------------------------------
# create_empty
# -----------------------------------------------------------------------

class TestCreateEmpty:
    def test_returns_song(self, adapter: MidiAdapter) -> None:
        song = adapter.create_empty("My Song", {})
        assert isinstance(song, Song)
        assert song.title == "My Song"

    def test_respects_params(self, adapter: MidiAdapter) -> None:
        song = adapter.create_empty("Custom", {
            "tempo": "140",
            "time-sig": "3/4",
            "key": "G-minor",
            "ppqn": "960",
        })
        assert song.tempo_map[0].bpm == 140.0
        assert song.time_signatures[0].numerator == 3
        assert song.time_signatures[0].denominator == 4
        assert song.key_signatures[0].key == "G"
        assert song.key_signatures[0].mode == "minor"
        assert song.ppqn == 960

    def test_defaults(self, adapter: MidiAdapter) -> None:
        song = adapter.create_empty("Default", {})
        assert song.tempo_map[0].bpm == 120.0
        assert song.time_signatures[0].numerator == 4
        assert song.ppqn == 480


# -----------------------------------------------------------------------
# serialize / deserialize round-trip
# -----------------------------------------------------------------------

class TestSerializeRoundTrip:
    def test_round_trip(self, adapter: MidiAdapter, song_with_piano: Song) -> None:
        # Add a note
        log = CoreEventLog()
        op = parse_op("note Piano C4 at:1.1 dur:quarter vel:80")
        assert isinstance(op, GenericParsedOp)
        result = adapter.dispatch_op(op, song_with_piano, log)
        assert result.success

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            path = f.name
        try:
            adapter.serialize(song_with_piano, path)
            loaded = adapter.deserialize(path)
            assert isinstance(loaded, Song)
            assert len(loaded.tracks) == len(song_with_piano.tracks)
            loaded_notes = sum(len(t.notes) for t in loaded.tracks.values())
            assert loaded_notes == 1
        finally:
            os.unlink(path)


# -----------------------------------------------------------------------
# dispatch_op
# -----------------------------------------------------------------------

class TestDispatchOp:
    def test_note_op(self, adapter: MidiAdapter, song_with_piano: Song) -> None:
        log = CoreEventLog()
        op = parse_op("note Piano C4 at:1.1 dur:quarter vel:80")
        assert isinstance(op, GenericParsedOp)
        result = adapter.dispatch_op(op, song_with_piano, log)
        assert result.success
        piano = song_with_piano.get_track_by_name("Piano")
        assert piano is not None
        assert len(piano.notes) == 1

    def test_track_op(self, adapter: MidiAdapter, song: Song) -> None:
        log = CoreEventLog()
        op = parse_op("track add Bass instrument:acoustic-bass")
        assert isinstance(op, GenericParsedOp)
        result = adapter.dispatch_op(op, song, log)
        assert result.success
        assert song.get_track_by_name("Bass") is not None

    def test_chord_op(self, adapter: MidiAdapter, song_with_piano: Song) -> None:
        log = CoreEventLog()
        op = parse_op("chord Piano Cmaj at:1.1 dur:half vel:mf")
        assert isinstance(op, GenericParsedOp)
        result = adapter.dispatch_op(op, song_with_piano, log)
        assert result.success
        piano = song_with_piano.get_track_by_name("Piano")
        assert piano is not None
        assert len(piano.notes) == 3  # C, E, G

    def test_unknown_verb_fails(self, adapter: MidiAdapter, song: Song) -> None:
        log = CoreEventLog()
        op = parse_op("frobnicate something")
        assert isinstance(op, GenericParsedOp)
        result = adapter.dispatch_op(op, song, log)
        assert not result.success


# -----------------------------------------------------------------------
# dispatch_query
# -----------------------------------------------------------------------

class TestDispatchQuery:
    def test_tracks_query(self, adapter: MidiAdapter, song_with_piano: Song) -> None:
        result = adapter.dispatch_query("tracks", song_with_piano)
        assert "Piano" in result

    def test_map_query(self, adapter: MidiAdapter, song_with_piano: Song) -> None:
        result = adapter.dispatch_query("map", song_with_piano)
        assert "Test Song" in result

    def test_stats_query(self, adapter: MidiAdapter, song_with_piano: Song) -> None:
        result = adapter.dispatch_query("stats", song_with_piano)
        assert "Tracks: 1" in result


# -----------------------------------------------------------------------
# reverse_event / replay_event
# -----------------------------------------------------------------------

class TestReverseReplay:
    def test_reverse_note(self, adapter: MidiAdapter, song_with_piano: Song) -> None:
        log = CoreEventLog()
        op = parse_op("note Piano C4 at:1.1 dur:quarter vel:80")
        assert isinstance(op, GenericParsedOp)
        result = adapter.dispatch_op(op, song_with_piano, log)
        assert result.success

        piano = song_with_piano.get_track_by_name("Piano")
        assert piano is not None
        assert len(piano.notes) == 1

        # Get the event from the log and reverse it
        events = log.recent(1)
        assert len(events) == 1
        adapter.reverse_event(events[0], song_with_piano)
        assert len(piano.notes) == 0

    def test_replay_note(self, adapter: MidiAdapter, song_with_piano: Song) -> None:
        log = CoreEventLog()
        op = parse_op("note Piano C4 at:1.1 dur:quarter vel:80")
        assert isinstance(op, GenericParsedOp)
        result = adapter.dispatch_op(op, song_with_piano, log)
        assert result.success

        piano = song_with_piano.get_track_by_name("Piano")
        assert piano is not None
        assert len(piano.notes) == 1

        # Undo, then replay
        events = log.undo(1)
        for ev in events:
            adapter.reverse_event(ev, song_with_piano)
        assert len(piano.notes) == 0

        replayed = log.redo(1)
        for ev in replayed:
            adapter.replay_event(ev, song_with_piano)
        assert len(piano.notes) == 1


# -----------------------------------------------------------------------
# get_digest
# -----------------------------------------------------------------------

class TestGetDigest:
    def test_digest_format(self, adapter: MidiAdapter, song: Song) -> None:
        digest = adapter.get_digest(song)
        assert digest.startswith("[")
        assert digest.endswith("]")
        assert "0t" in digest  # 0 tracks
        assert "tempo:120" in digest

    def test_digest_with_tracks(self, adapter: MidiAdapter, song_with_piano: Song) -> None:
        digest = adapter.get_digest(song_with_piano)
        assert "1t" in digest  # 1 track


# -----------------------------------------------------------------------
# rebuild_indices
# -----------------------------------------------------------------------

class TestRebuildIndices:
    def test_rebuild_after_manual_add(self, adapter: MidiAdapter, song_with_piano: Song) -> None:
        piano = song_with_piano.get_track_by_name("Piano")
        assert piano is not None
        pitch = Pitch(name="C", accidental="", octave=4, midi_number=60)
        song_with_piano.add_note(piano.id, pitch, absolute_tick=0, duration_ticks=480)

        adapter.rebuild_indices(song_with_piano)
        notes = adapter.registry.by_pitch(60)
        assert len(notes) == 1
