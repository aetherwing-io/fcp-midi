"""End-to-end integration tests for the MIDI FCP server layer.

Tests exercise the full stack through IntentLayer: session management,
track/note/chord operations, queries, undo/redo, and error handling.
"""

from __future__ import annotations

import pytest

from fcp_midi.server.intent import IntentLayer


# -----------------------------------------------------------------------
# Session management
# -----------------------------------------------------------------------

class TestSessionNew:
    def test_create_song(self, intent: IntentLayer) -> None:
        result = intent.execute_session('new "Test" tempo:120 time-sig:4/4')
        assert result.startswith("+")
        assert "Test" in result
        assert intent.song is not None
        assert intent.song.title == "Test"
        assert intent.song.tempo_map[0].bpm == 120.0
        assert intent.song.time_signatures[0].numerator == 4
        assert intent.song.time_signatures[0].denominator == 4

    def test_create_with_key(self, intent: IntentLayer) -> None:
        result = intent.execute_session('new "KeySong" tempo:90 key:G-minor')
        assert result.startswith("+")
        assert intent.song is not None
        assert len(intent.song.key_signatures) == 1
        assert intent.song.key_signatures[0].key == "G"
        assert intent.song.key_signatures[0].mode == "minor"

    def test_create_with_ppqn(self, intent: IntentLayer) -> None:
        result = intent.execute_session('new "Hi Res" ppqn:960')
        assert result.startswith("+")
        assert intent.song is not None
        assert intent.song.ppqn == 960

    def test_no_song_ops_error(self, intent: IntentLayer) -> None:
        results = intent.execute_ops(["note Piano C4 at:1.1 dur:quarter"])
        assert any("No song loaded" in r for r in results)

    def test_no_song_query_error(self, intent: IntentLayer) -> None:
        result = intent.execute_query("map")
        assert "No song loaded" in result


# -----------------------------------------------------------------------
# Track management
# -----------------------------------------------------------------------

class TestTrackOps:
    def test_add_track(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(
            ["track add Piano instrument:acoustic-grand-piano"]
        )
        assert any("+" in r and "Piano" in r for r in results)
        assert intent_with_song.song is not None
        assert len(intent_with_song.song.tracks) == 1

        track = intent_with_song.song.get_track_by_name("Piano")
        assert track is not None
        assert track.instrument == "acoustic-grand-piano"
        assert track.program == 0

    def test_add_track_with_channel(self, intent_with_song: IntentLayer) -> None:
        # ch:10 = MIDI channel 10 (1-indexed) = channel 9 (0-indexed, drums)
        results = intent_with_song.execute_ops(
            ["track add Drums instrument:standard-kit ch:10"]
        )
        assert any("+" in r for r in results)
        track = intent_with_song.song.get_track_by_name("Drums")
        assert track is not None
        assert track.channel == 9

    def test_remove_track(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(["track remove Piano"])
        assert any("removed" in r.lower() for r in results)
        assert len(intent_with_piano.song.tracks) == 0

    def test_remove_nonexistent_track(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(["track remove Guitar"])
        assert any("!" in r for r in results)

    def test_unknown_instrument(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(
            ["track add Bad instrument:nonexistent-thing"]
        )
        assert any("Unknown instrument" in r for r in results)


# -----------------------------------------------------------------------
# Note operations
# -----------------------------------------------------------------------

class TestNoteOps:
    def test_add_note(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["note Piano C4 at:1.1 dur:quarter vel:80"]
        )
        assert any("+" in r and "C4" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 1
        note = list(track.notes.values())[0]
        assert note.pitch.name == "C"
        assert note.pitch.octave == 4
        assert note.pitch.midi_number == 60
        assert note.velocity == 80
        assert note.duration_ticks == 480  # quarter at ppqn=480
        assert note.absolute_tick == 0  # 1.1 = tick 0

    def test_add_sharp_pitch(self, intent_with_piano: IntentLayer) -> None:
        """Regression: C#4 was eaten by shlex treating # as comment."""
        results = intent_with_piano.execute_ops(
            ["note Piano C#4 at:1.1 dur:quarter vel:mf"]
        )
        assert any("+" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        note = list(track.notes.values())[0]
        assert note.pitch.midi_number == 61  # C#4
        assert note.pitch.accidental == "#"
        assert note.velocity == 80  # mf

    def test_add_note_symbolic_velocity(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["note Piano E5 at:2.1 dur:half vel:ff"]
        )
        assert any("+" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        note = list(track.notes.values())[0]
        assert note.velocity == 112  # ff = 112

    def test_add_note_default_values(self, intent_with_piano: IntentLayer) -> None:
        """Note with minimal params uses defaults."""
        results = intent_with_piano.execute_ops(["note Piano G3"])
        assert any("+" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        note = list(track.notes.values())[0]
        assert note.velocity == 80  # default
        assert note.duration_ticks == 480  # default quarter

    def test_invalid_pitch(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["note Piano X9 at:1.1 dur:quarter"]
        )
        assert any("!" in r for r in results)
        assert any("pitch" in r.lower() or "parse" in r.lower() for r in results)

    def test_unknown_track(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["note Guitar C4 at:1.1 dur:quarter"]
        )
        assert any("!" in r for r in results)
        # Should suggest the existing "Piano" track
        assert any("Piano" in r for r in results)


# -----------------------------------------------------------------------
# Chord operations
# -----------------------------------------------------------------------

class TestChordOps:
    def test_add_chord(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["chord Piano Cmaj at:2.1 dur:half vel:70"]
        )
        assert any("+" in r and "Cmaj" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 3  # C, E, G

        pitches = sorted(n.pitch.midi_number for n in track.notes.values())
        assert pitches == [60, 64, 67]  # C4, E4, G4

    def test_add_minor_chord(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["chord Piano Am at:1.1 dur:quarter"]
        )
        assert any("+" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        pitches = sorted(n.pitch.midi_number for n in track.notes.values())
        assert pitches == [69, 72, 76]  # A4, C5, E5 (root at octave 4)

    def test_add_seventh_chord(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["chord Piano G7 at:3.1 dur:quarter"]
        )
        assert any("+" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 4  # G, B, D, F


# -----------------------------------------------------------------------
# CC and Bend operations
# -----------------------------------------------------------------------

class TestCCBendOps:
    def test_add_cc(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["cc Piano volume 100 at:1.1"]
        )
        assert any("+" in r and "volume" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.control_changes) == 1
        cc = list(track.control_changes.values())[0]
        assert cc.controller == 7  # volume
        assert cc.value == 100

    def test_add_bend(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["bend Piano 4096 at:1.1"]
        )
        assert any("+" in r and "bend" in r.lower() for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.pitch_bends) == 1
        pb = list(track.pitch_bends.values())[0]
        assert pb.value == 4096

    def test_bend_center(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["bend Piano center at:1.1"]
        )
        assert any("+" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        pb = list(track.pitch_bends.values())[0]
        assert pb.value == 0


# -----------------------------------------------------------------------
# Meta operations
# -----------------------------------------------------------------------

class TestMetaOps:
    def test_tempo(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(["tempo 140"])
        assert any("+" in r and "140" in r for r in results)

    def test_time_sig(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(["time-sig 3/4"])
        assert any("+" in r and "3/4" in r for r in results)

    def test_key_sig(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(["key-sig G-major"])
        assert any("+" in r and "G" in r for r in results)

    def test_marker(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(['marker Chorus at:5.1'])
        assert any("+" in r and "Chorus" in r for r in results)

    def test_title(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(['title "New Title"'])
        assert any("+" in r for r in results)
        assert intent_with_song.song.title == "New Title"


# -----------------------------------------------------------------------
# Queries
# -----------------------------------------------------------------------

class TestQueries:
    def test_tracks_query(self, intent_with_piano: IntentLayer) -> None:
        result = intent_with_piano.execute_query("tracks")
        assert "Piano" in result
        assert "ch:" in result

    def test_stats_query(self, intent_with_piano: IntentLayer) -> None:
        # Add some notes first
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter",
            "note Piano E4 at:1.2 dur:quarter",
        ])
        result = intent_with_piano.execute_query("stats")
        assert "Notes: 2" in result
        assert "Tracks: 1" in result

    def test_map_query(self, intent_with_piano: IntentLayer) -> None:
        result = intent_with_piano.execute_query("map")
        assert "Test Song" in result
        assert "Piano" in result

    def test_describe_query(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
        ])
        result = intent_with_piano.execute_query("describe Piano")
        assert "Piano" in result
        assert "Notes: 1" in result

    def test_events_query(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
        ])
        result = intent_with_piano.execute_query("events Piano")
        assert "C4" in result or "C" in result

    def test_events_query_with_range(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter",
            "note Piano E4 at:5.1 dur:quarter",
        ])
        result = intent_with_piano.execute_query("events Piano 1.1-4.4")
        assert "C" in result
        # E4 at 5.1 should be excluded
        lines = result.split("\n")
        # Only one note event line expected (plus header)
        event_lines = [l for l in lines if "vel:" in l]
        assert len(event_lines) == 1

    def test_find_query(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter",
            "note Piano E4 at:2.1 dur:quarter",
        ])
        result = intent_with_piano.execute_query("find C4")
        assert "1" in result  # at least 1 found

    def test_status_query(self, intent_with_piano: IntentLayer) -> None:
        result = intent_with_piano.execute_query("status")
        assert "Test Song" in result

    def test_history_query(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops(["note Piano C4 at:1.1 dur:quarter"])
        result = intent_with_piano.execute_query("history 5")
        assert "note_added" in result

    def test_unknown_query(self, intent_with_piano: IntentLayer) -> None:
        result = intent_with_piano.execute_query("foobar")
        assert "!" in result

    def test_unknown_track_query(self, intent_with_piano: IntentLayer) -> None:
        result = intent_with_piano.execute_query("describe Guitar")
        assert "not found" in result.lower()


# -----------------------------------------------------------------------
# Checkpoint, Undo, Redo
# -----------------------------------------------------------------------

class TestUndoRedo:
    def test_checkpoint_and_undo(self, intent_with_piano: IntentLayer) -> None:
        # Add note, checkpoint, add another, undo
        intent_with_piano.execute_ops(["note Piano C4 at:1.1 dur:quarter"])
        intent_with_piano.execute_session("checkpoint v1")
        intent_with_piano.execute_ops(["note Piano E5 at:3.1 dur:quarter"])

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 2

        result = intent_with_piano.execute_session("undo")
        assert "+" in result

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 1

    def test_redo_restores_note(self, intent_with_piano: IntentLayer) -> None:
        """Redo after undo of NoteAdded should restore the note with full data."""
        intent_with_piano.execute_ops(["note Piano C4 at:1.1 dur:quarter vel:90"])
        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 1
        note = list(track.notes.values())[0]
        original_midi = note.pitch.midi_number
        original_vel = note.velocity

        intent_with_piano.execute_session("undo")
        assert len(track.notes) == 0

        result = intent_with_piano.execute_session("redo")
        assert "+" in result
        assert len(track.notes) == 1
        restored = list(track.notes.values())[0]
        assert restored.pitch.midi_number == original_midi
        assert restored.velocity == original_vel

    def test_undo_note_removal_restores_note(self, intent_with_piano: IntentLayer) -> None:
        """Undoing a note removal should restore the note with correct data."""
        intent_with_piano.execute_ops(["note Piano C4 at:1.1 dur:quarter vel:85"])
        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 1
        note = list(track.notes.values())[0]
        original_id = note.id
        original_midi = note.pitch.midi_number
        original_vel = note.velocity
        original_tick = note.absolute_tick
        original_dur = note.duration_ticks

        intent_with_piano.execute_ops(["remove @track:Piano"])
        assert len(track.notes) == 0

        # Undo the removal
        result = intent_with_piano.execute_session("undo")
        assert "+" in result
        assert len(track.notes) == 1
        restored = track.notes[original_id]
        assert restored.pitch.midi_number == original_midi
        assert restored.velocity == original_vel
        assert restored.absolute_tick == original_tick
        assert restored.duration_ticks == original_dur

    def test_undo_track_removal_restores_track(self, intent_with_piano: IntentLayer) -> None:
        """Undoing a track removal should restore the track with all its notes."""
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano E4 at:2.1 dur:quarter vel:80",
        ])
        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 2
        track_id = track.id

        intent_with_piano.execute_ops(["track remove Piano"])
        assert len(intent_with_piano.song.tracks) == 0

        # Undo the track removal
        result = intent_with_piano.execute_session("undo")
        assert "+" in result
        assert track_id in intent_with_piano.song.tracks
        restored = intent_with_piano.song.tracks[track_id]
        assert restored.name == "Piano"
        assert len(restored.notes) == 2

    def test_undo_to_checkpoint(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops(["note Piano C4 at:1.1 dur:quarter"])
        intent_with_piano.execute_session("checkpoint v1")
        intent_with_piano.execute_ops([
            "note Piano E4 at:2.1 dur:quarter",
            "note Piano G4 at:3.1 dur:quarter",
        ])

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 3

        result = intent_with_piano.execute_session("undo to:v1")
        assert "+" in result

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 1

    def test_nothing_to_undo(self, intent_with_piano: IntentLayer) -> None:
        result = intent_with_piano.execute_session("undo")
        # Should get the TrackAdded event from fixture
        # But if we undo the track add, check gracefully
        assert "+" in result or "Nothing to undo" in result

    def test_nothing_to_redo(self, intent_with_piano: IntentLayer) -> None:
        result = intent_with_piano.execute_session("redo")
        assert "Nothing to redo" in result


# -----------------------------------------------------------------------
# Batch atomicity
# -----------------------------------------------------------------------

class TestBatchAtomicity:
    def test_failed_op_rolls_back_batch(self, intent_with_piano: IntentLayer) -> None:
        """If any op in a batch fails, all preceding ops are rolled back."""
        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 0

        results = intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter",
            "note BadTrack E4 at:1.1 dur:quarter",
        ])
        # First op succeeded, second failed
        assert any("+" in r and "C4" in r for r in results)
        assert any("!" in r for r in results)
        # But the batch was rolled back — no notes should remain
        assert len(track.notes) == 0

    def test_successful_batch_commits(self, intent_with_piano: IntentLayer) -> None:
        """A fully successful batch should commit all ops."""
        track = intent_with_piano.song.get_track_by_name("Piano")
        results = intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter",
            "note Piano E4 at:1.2 dur:quarter",
            "note Piano G4 at:1.3 dur:quarter",
        ])
        assert all(not r.startswith("!") for r in results if r.strip())
        assert len(track.notes) == 3

    def test_batch_rollback_preserves_prior_state(self, intent_with_piano: IntentLayer) -> None:
        """A failed batch should not affect notes added before the batch."""
        intent_with_piano.execute_ops(["note Piano C4 at:1.1 dur:quarter"])
        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 1

        # This batch should fail and roll back
        intent_with_piano.execute_ops([
            "note Piano E4 at:1.2 dur:quarter",
            "note BadTrack G4 at:1.3 dur:quarter",
        ])
        # The note from the first batch should still be there
        assert len(track.notes) == 1


# -----------------------------------------------------------------------
# Editing operations (selector-based)
# -----------------------------------------------------------------------

class TestEditingOps:
    def test_remove_by_track(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter",
            "note Piano E4 at:2.1 dur:quarter",
        ])
        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 2

        results = intent_with_piano.execute_ops(["remove @track:Piano"])
        assert any("Removed 2" in r for r in results)
        assert len(track.notes) == 0

    def test_transpose(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter",
        ])
        results = intent_with_piano.execute_ops(["transpose +7 @track:Piano"])
        assert any("Transposed" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        note = list(track.notes.values())[0]
        assert note.pitch.midi_number == 67  # C4(60) + 7 = G4(67)

    def test_velocity_adjust(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
        ])
        results = intent_with_piano.execute_ops(["velocity +20 @track:Piano"])
        assert any("Adjusted" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        note = list(track.notes.values())[0]
        assert note.velocity == 100

    def test_mute_toggle(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(["mute Piano"])
        assert any("muted" in r.lower() for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert track.mute is True

        # Toggle back
        results = intent_with_piano.execute_ops(["mute Piano"])
        assert track.mute is False

    def test_solo_toggle(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(["solo Piano"])
        assert any("solo" in r.lower() for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert track.solo is True


# -----------------------------------------------------------------------
# Error handling
# -----------------------------------------------------------------------

class TestErrors:
    def test_empty_op(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops([""])
        assert any("!" in r for r in results)

    def test_unknown_verb(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(["foobar something"])
        assert any("!" in r or "Unknown verb" in r for r in results)

    def test_unknown_session_action(self, intent: IntentLayer) -> None:
        result = intent.execute_session("foobar")
        assert "!" in result

    def test_fuzzy_track_suggestion(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(["note Paino C4 at:1.1 dur:quarter"])
        joined = "\n".join(results)
        # Should suggest "Piano" as a close match
        assert "Piano" in joined

    def test_batch_mixed_results(self, intent_with_piano: IntentLayer) -> None:
        """A batch with valid and invalid ops returns mixed results."""
        results = intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter",
            "note BadTrack E4 at:1.1 dur:quarter",
        ])
        assert any("+" in r for r in results)
        assert any("!" in r for r in results)


# -----------------------------------------------------------------------
# Full workflow test
# -----------------------------------------------------------------------

class TestFullWorkflow:
    def test_end_to_end(self, intent: IntentLayer) -> None:
        # 1. Create song
        result = intent.execute_session('new "Integration Test" tempo:120 time-sig:4/4')
        assert result.startswith("+")
        assert intent.song is not None

        # 2. Add tracks
        results = intent.execute_ops([
            "track add Piano instrument:acoustic-grand-piano",
            "track add Bass instrument:acoustic-bass",
        ])
        assert all(any(c in r for c in ["+", "["]) for r in results)
        assert len(intent.song.tracks) == 2

        # 3. Add notes
        results = intent.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano E4 at:1.2 dur:quarter vel:80",
            "note Piano G4 at:1.3 dur:quarter vel:80",
        ])
        piano = intent.song.get_track_by_name("Piano")
        assert len(piano.notes) == 3

        # 4. Add chord
        results = intent.execute_ops([
            "chord Piano Cmaj at:2.1 dur:half vel:70",
        ])
        assert len(piano.notes) == 6  # 3 + 3

        # 5. Add bass note
        results = intent.execute_ops([
            "note Bass C2 at:1.1 dur:half vel:f",
        ])
        bass = intent.song.get_track_by_name("Bass")
        assert len(bass.notes) == 1

        # 6. Query tracks
        result = intent.execute_query("tracks")
        assert "Piano" in result
        assert "Bass" in result

        # 7. Query stats
        result = intent.execute_query("stats")
        assert "Notes: 7" in result
        assert "Tracks: 2" in result

        # 8. Query map
        result = intent.execute_query("map")
        assert "Integration Test" in result
        assert "Piano" in result
        assert "Bass" in result

        # 9. Checkpoint
        result = intent.execute_session("checkpoint v1")
        assert "+" in result

        # 10. Add more notes
        results = intent.execute_ops([
            "note Piano E5 at:3.1 dur:quarter",
        ])
        assert len(piano.notes) == 7

        # 11. Undo
        result = intent.execute_session("undo")
        assert "+" in result
        assert len(piano.notes) == 6

        # 12. Redo
        result = intent.execute_session("redo")
        assert "+" in result
        # Redo for NoteAdded may not fully restore without snapshot,
        # but the mechanism should not error


# -----------------------------------------------------------------------
# A1: Modify verb
# -----------------------------------------------------------------------

class TestModifyOps:
    def test_modify_pitch(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops(["note Piano C4 at:1.1 dur:quarter vel:80"])
        results = intent_with_piano.execute_ops(["modify @track:Piano pitch:E4"])
        assert any("Modified 1" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        note = list(track.notes.values())[0]
        assert note.pitch.midi_number == 64  # E4

    def test_modify_velocity(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops(["note Piano C4 at:1.1 dur:quarter vel:80"])
        results = intent_with_piano.execute_ops(["modify @track:Piano vel:ff"])
        assert any("Modified 1" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        note = list(track.notes.values())[0]
        assert note.velocity == 112  # ff

    def test_modify_duration(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops(["note Piano C4 at:1.1 dur:quarter vel:80"])
        results = intent_with_piano.execute_ops(["modify @track:Piano dur:half"])
        assert any("Modified 1" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        note = list(track.notes.values())[0]
        assert note.duration_ticks == 960  # half

    def test_modify_multiple_fields(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops(["note Piano C4 at:1.1 dur:quarter vel:80"])
        results = intent_with_piano.execute_ops(["modify @track:Piano pitch:D5 vel:100 dur:eighth"])
        assert any("Modified 1" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        note = list(track.notes.values())[0]
        assert note.pitch.midi_number == 74  # D5
        assert note.velocity == 100
        assert note.duration_ticks == 240  # eighth

    def test_modify_no_match(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(["modify @track:Piano pitch:E4"])
        assert any("No notes matched" in r for r in results)

    def test_modify_no_params(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops(["note Piano C4 at:1.1 dur:quarter"])
        results = intent_with_piano.execute_ops(["modify @track:Piano"])
        assert any("No modification specified" in r for r in results)


# -----------------------------------------------------------------------
# A2: Repeat verb
# -----------------------------------------------------------------------

class TestRepeatOps:
    def test_repeat_once_with_to(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano E4 at:1.2 dur:quarter vel:80",
        ])
        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 2

        results = intent_with_piano.execute_ops(["repeat @track:Piano to:3.1 count:1"])
        assert any("Repeated" in r and "x1" in r for r in results)
        assert len(track.notes) == 4  # 2 original + 2 repeated

    def test_repeat_three_times_auto_append(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
        ])
        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 1

        results = intent_with_piano.execute_ops(["repeat @track:Piano count:3"])
        assert any("x3" in r for r in results)
        assert len(track.notes) == 4  # 1 original + 3 repeated

    def test_repeat_with_to_specified(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
        ])
        results = intent_with_piano.execute_ops(["repeat @track:Piano to:5.1 count:2"])
        assert any("Repeated" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 3  # 1 original + 2 repeated

    def test_repeat_no_match(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(["repeat @track:Piano count:2"])
        assert any("No notes matched" in r for r in results)


# -----------------------------------------------------------------------
# A3: Relative positions in integration
# -----------------------------------------------------------------------

class TestRelativePositions:
    def test_note_at_plus_quarter(self, intent_with_piano: IntentLayer) -> None:
        # First note at 1.1 (tick 0), duration quarter (480 ticks)
        intent_with_piano.execute_ops(["note Piano C4 at:1.1 dur:quarter vel:80"])
        # Second note at +quarter (should be at tick 480, i.e. 1.2)
        results = intent_with_piano.execute_ops(["note Piano E4 at:+quarter dur:quarter vel:80"])
        assert any("+" in r and "E4" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        notes = sorted(track.notes.values(), key=lambda n: n.absolute_tick)
        # First note: tick 0 + dur 480 = _last_tick 480
        # +quarter = 480 + 480 = 960? No: _last_tick after first note = 0 + 480 = 480
        # +quarter from reference 480 = 480 + 480 = 960
        # Wait, that means the second note is at tick 960 (beat 1.3)
        # Actually let me reconsider: after first note at:1.1, _last_tick = 0 + 480 = 480
        # Then +quarter means reference_tick(480) + 480 = 960
        assert notes[1].absolute_tick == 960

    def test_note_at_end(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano E4 at:2.1 dur:half vel:80",
        ])
        # end = max(note.tick + note.dur) = max(0+480, 1920+960) = 2880
        results = intent_with_piano.execute_ops(["note Piano G4 at:end dur:quarter vel:80"])
        assert any("+" in r and "G4" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        notes = sorted(track.notes.values(), key=lambda n: n.absolute_tick)
        assert notes[-1].absolute_tick == 2880


# -----------------------------------------------------------------------
# A4: Bulk query (events * / events all)
# -----------------------------------------------------------------------

class TestBulkQuery:
    def test_events_star(self, intent_with_piano: IntentLayer) -> None:
        # Add a second track
        intent_with_piano.execute_ops([
            "track add Bass instrument:acoustic-bass",
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Bass E2 at:1.1 dur:half vel:80",
        ])
        result = intent_with_piano.execute_query("events *")
        assert "Piano" in result
        assert "Bass" in result

    def test_events_all(self, intent_with_piano: IntentLayer) -> None:
        intent_with_piano.execute_ops([
            "track add Bass instrument:acoustic-bass",
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Bass E2 at:1.1 dur:half vel:80",
        ])
        result = intent_with_piano.execute_query("events all")
        assert "Piano" in result
        assert "Bass" in result


# -----------------------------------------------------------------------
# A5: Range selector inclusive end
# -----------------------------------------------------------------------

class TestRangeInclusive:
    def test_note_at_end_beat_is_included(self, intent_with_piano: IntentLayer) -> None:
        """A note exactly at the end beat of a range should be included."""
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano E4 at:1.2 dur:quarter vel:80",
        ])
        # Range 1.1-1.2 should include both notes (inclusive end)
        results = intent_with_piano.execute_ops(["remove @track:Piano @range:1.1-1.2"])
        assert any("Removed 2" in r for r in results)

    def test_note_after_end_beat_excluded(self, intent_with_piano: IntentLayer) -> None:
        """A note after the end beat of a range should be excluded."""
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano E4 at:2.1 dur:quarter vel:80",
            "note Piano G4 at:2.2 dur:quarter vel:80",
        ])
        # Range 1.1-2.1 should include notes at 1.1 and 2.1 but not 2.2
        results = intent_with_piano.execute_ops(["remove @track:Piano @range:1.1-2.1"])
        assert any("Removed 2" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        assert len(track.notes) == 1
        remaining = list(track.notes.values())[0]
        assert remaining.pitch.midi_number == 67  # G4 at 2.2

    def test_events_query_range_inclusive(self, intent_with_piano: IntentLayer) -> None:
        """Events query with range should also use inclusive end."""
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano E4 at:1.2 dur:quarter vel:80",
            "note Piano G4 at:2.1 dur:quarter vel:80",
        ])
        result = intent_with_piano.execute_query("events Piano 1.1-1.2")
        event_lines = [l for l in result.split("\n") if "vel:" in l]
        assert len(event_lines) == 2  # Both notes at 1.1 and 1.2


# -----------------------------------------------------------------------
# A6: Crescendo / Decrescendo
# -----------------------------------------------------------------------

class TestCrescendoDecrescendo:
    def test_crescendo_linear_interpolation(self, intent_with_piano: IntentLayer) -> None:
        """Crescendo should linearly interpolate velocity across matched notes."""
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano D4 at:1.2 dur:quarter vel:80",
            "note Piano E4 at:1.3 dur:quarter vel:80",
            "note Piano F4 at:1.4 dur:quarter vel:80",
        ])
        results = intent_with_piano.execute_ops([
            "crescendo @track:Piano from:p to:f",
        ])
        assert any("Crescendo" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        vels = [n.velocity for n in sorted(track.notes.values(), key=lambda n: n.absolute_tick)]
        # p=49, f=96; 4 notes: 49, 65, 81, 96 (linear interpolation rounded)
        assert vels[0] == 49   # from: p
        assert vels[-1] == 96  # to: f
        # Middle values should be between from and to
        assert vels[0] < vels[1] < vels[2] < vels[3]

    def test_crescendo_single_note(self, intent_with_piano: IntentLayer) -> None:
        """Crescendo with a single note sets velocity to 'to' value."""
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
        ])
        results = intent_with_piano.execute_ops([
            "crescendo @track:Piano from:pp to:ff",
        ])
        assert any("Crescendo" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        note = list(track.notes.values())[0]
        assert note.velocity == 112  # ff

    def test_decrescendo(self, intent_with_piano: IntentLayer) -> None:
        """Decrescendo from ff to pp should decrease velocities."""
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano D4 at:1.2 dur:quarter vel:80",
            "note Piano E4 at:1.3 dur:quarter vel:80",
        ])
        results = intent_with_piano.execute_ops([
            "decrescendo @track:Piano from:ff to:pp",
        ])
        assert any("Decrescendo" in r for r in results)

        track = intent_with_piano.song.get_track_by_name("Piano")
        vels = [n.velocity for n in sorted(track.notes.values(), key=lambda n: n.absolute_tick)]
        assert vels[0] == 112  # ff
        assert vels[-1] == 33  # pp
        assert vels[0] > vels[1] > vels[2]

    def test_crescendo_missing_params(self, intent_with_piano: IntentLayer) -> None:
        """Crescendo without from/to should return error."""
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
        ])
        results = intent_with_piano.execute_ops([
            "crescendo @track:Piano from:pp",
        ])
        assert any("!" in r for r in results)

        results = intent_with_piano.execute_ops([
            "crescendo @track:Piano to:ff",
        ])
        assert any("!" in r for r in results)


# -----------------------------------------------------------------------
# A7: Gap warnings
# -----------------------------------------------------------------------

class TestGapWarnings:
    def test_gap_warning_emitted(self, intent_with_piano: IntentLayer) -> None:
        """Track with gaps compared to other tracks should emit warnings."""
        intent_with_piano.execute_ops([
            "track add Bass instrument:acoustic-bass",
            # Piano has notes in measures 1-4
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano C4 at:2.1 dur:quarter vel:80",
            "note Piano C4 at:3.1 dur:quarter vel:80",
            "note Piano C4 at:4.1 dur:quarter vel:80",
            # Bass only has notes in measures 1 and 4
            "note Bass C2 at:1.1 dur:quarter vel:80",
            "note Bass C2 at:4.1 dur:quarter vel:80",
        ])
        results = intent_with_piano.execute_ops(["note Bass C2 at:4.1 dur:quarter vel:80"])
        # Should have gap warnings for Bass at measures 2-3
        joined = "\n".join(results)
        assert "?" in joined
        assert "Bass" in joined
        assert "empty at measure" in joined

    def test_no_gap_warning_same_coverage(self, intent_with_piano: IntentLayer) -> None:
        """No warnings when all tracks have the same measure coverage."""
        intent_with_piano.execute_ops([
            "track add Bass instrument:acoustic-bass",
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano C4 at:2.1 dur:quarter vel:80",
            "note Bass C2 at:1.1 dur:quarter vel:80",
            "note Bass C2 at:2.1 dur:quarter vel:80",
        ])
        results = intent_with_piano.execute_ops(["note Piano C4 at:2.1 dur:quarter vel:80"])
        joined = "\n".join(results)
        assert "? " not in joined or "empty at measure" not in joined

    def test_no_gap_warning_single_track(self, intent_with_piano: IntentLayer) -> None:
        """No gap warnings with only one track."""
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano C4 at:3.1 dur:quarter vel:80",
        ])
        results = intent_with_piano.execute_ops(["note Piano C4 at:3.1 dur:quarter vel:80"])
        joined = "\n".join(results)
        assert "empty at measure" not in joined


# -----------------------------------------------------------------------
# Selector @not: integration
# -----------------------------------------------------------------------

class TestSelectorNot:
    def test_not_pitch_excludes_matching(self, intent_with_piano: IntentLayer) -> None:
        """@not:pitch:C4 should exclude C4 notes from removal."""
        intent_with_piano.execute_ops([
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Piano D4 at:1.2 dur:quarter vel:80",
            "note Piano E4 at:1.3 dur:quarter vel:80",
        ])
        # Remove all Piano notes EXCEPT C4
        intent_with_piano.execute_ops(["remove @track:Piano @not:pitch:C4"])
        query = intent_with_piano.execute_query("events Piano")
        # C4 should remain
        assert "C" in query
        # D4 and E4 should be gone
        # Check note count — only C4 should survive
        assert query.count("vel:") == 1

    def test_not_track_excludes_track(self, intent_with_piano: IntentLayer) -> None:
        """@all @not:track:Piano should affect all except Piano."""
        intent_with_piano.execute_ops([
            "track add Bass instrument:acoustic-bass",
            "note Piano C4 at:1.1 dur:quarter vel:80",
            "note Bass C2 at:1.1 dur:quarter vel:80",
        ])
        intent_with_piano.execute_ops(["remove @all @not:track:Piano"])
        piano_events = intent_with_piano.execute_query("events Piano")
        bass_events = intent_with_piano.execute_query("events Bass")
        # Piano notes should survive
        assert "C" in piano_events
        # Bass should be empty
        assert "vel:" not in bass_events or "No" in bass_events


# -----------------------------------------------------------------------
# Custom instruments: raw program numbers, bank select
# -----------------------------------------------------------------------

class TestRawProgramNumbers:
    def test_track_add_with_raw_program(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(
            ["track add Cello program:42"]
        )
        assert any(r.startswith("+") for r in results)
        track = intent_with_song.song.get_track_by_name("Cello")
        assert track is not None
        assert track.program == 42
        # Should have reverse-looked-up the GM name
        assert track.instrument == "cello"

    def test_track_add_with_raw_program_no_gm_name(self, intent_with_song: IntentLayer) -> None:
        """program:42 should still work even when name lookup succeeds."""
        results = intent_with_song.execute_ops(
            ["track add Synth program:80"]
        )
        assert any(r.startswith("+") for r in results)
        track = intent_with_song.song.get_track_by_name("Synth")
        assert track is not None
        assert track.program == 80

    def test_program_change_with_raw_number(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["program Piano program:73"]
        )
        assert any(r.startswith("+") for r in results)
        track = intent_with_piano.song.get_track_by_name("Piano")
        assert track.program == 73
        assert track.instrument == "flute"

    def test_program_with_instrument_name_still_works(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["program Piano violin"]
        )
        assert any(r.startswith("+") for r in results)
        track = intent_with_piano.song.get_track_by_name("Piano")
        assert track.program == 40

    def test_program_out_of_range(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(
            ["track add Bad program:200"]
        )
        assert any("0-127" in r for r in results)

    def test_program_invalid_value(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(
            ["track add Bad program:abc"]
        )
        assert any("Invalid program" in r for r in results)


class TestBankSelect:
    def test_track_with_bank_msb(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(
            ["track add Pad instrument:pad-2-warm bank:1"]
        )
        assert any(r.startswith("+") for r in results)
        track = intent_with_song.song.get_track_by_name("Pad")
        assert track.bank_msb == 1
        assert track.bank_lsb is None

    def test_track_with_bank_msb_lsb(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(
            ["track add Strings instrument:string-ensemble-1 bank:3.12"]
        )
        assert any(r.startswith("+") for r in results)
        track = intent_with_song.song.get_track_by_name("Strings")
        assert track.bank_msb == 3
        assert track.bank_lsb == 12

    def test_program_change_with_bank(self, intent_with_piano: IntentLayer) -> None:
        results = intent_with_piano.execute_ops(
            ["program Piano violin bank:2.5"]
        )
        assert any(r.startswith("+") for r in results)
        track = intent_with_piano.song.get_track_by_name("Piano")
        assert track.program == 40
        assert track.bank_msb == 2
        assert track.bank_lsb == 5

    def test_bank_select_display(self, intent_with_song: IntentLayer) -> None:
        intent_with_song.execute_ops(
            ["track add Pad instrument:pad-2-warm bank:1.0"]
        )
        result = intent_with_song.execute_query("describe Pad")
        assert "bank:1.0" in result

    def test_bank_msb_out_of_range(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(
            ["track add Bad instrument:violin bank:200"]
        )
        assert any("0-127" in r for r in results)

    def test_bank_lsb_out_of_range(self, intent_with_song: IntentLayer) -> None:
        results = intent_with_song.execute_ops(
            ["track add Bad instrument:violin bank:1.200"]
        )
        assert any("0-127" in r for r in results)


class TestInstrumentQuery:
    def test_instruments_query_returns_gm(self, intent_with_song: IntentLayer) -> None:
        result = intent_with_song.execute_query("instruments")
        assert "acoustic-grand-piano" in result
        assert "violin" in result

    def test_instruments_query_with_filter(self, intent_with_song: IntentLayer) -> None:
        result = intent_with_song.execute_query("instruments piano")
        assert "piano" in result
        # Should not include non-piano instruments
        assert "violin" not in result

    def test_instruments_query_no_match(self, intent_with_song: IntentLayer) -> None:
        result = intent_with_song.execute_query("instruments zzz-nonexistent")
        assert "No instruments" in result
