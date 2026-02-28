"""Tests for MidiModel — mido-native MIDI model."""

from __future__ import annotations

import os
import tempfile

import mido
import pytest

from fcp_midi.model.midi_model import (
    MidiModel,
    NoteIndex,
    NoteRef,
    TrackRef,
    absolute_to_delta,
    delta_to_absolute,
    insert_message_at_tick,
    pair_notes,
    remove_message_at_index,
    _extract_track_metadata,
)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestMidiModelConstruction:
    def test_empty_model_defaults(self):
        m = MidiModel()
        assert m.title == "Untitled"
        assert m.ppqn == 480
        assert len(m.file.tracks) == 1  # conductor only
        assert len(m.tracks) == 0
        assert len(m.track_order) == 0

    def test_custom_params(self):
        m = MidiModel(
            title="My Song",
            ppqn=960,
            tempo=140.0,
            time_sig=(3, 4),
            key="D",
        )
        assert m.title == "My Song"
        assert m.ppqn == 960
        conductor = m.file.tracks[0]

        # Check conductor messages
        types = [msg.type for msg in conductor]
        assert "track_name" in types
        assert "set_tempo" in types
        assert "time_signature" in types
        assert "key_signature" in types
        assert "end_of_track" in types

        # Verify tempo
        for msg in conductor:
            if msg.type == "set_tempo":
                assert abs(mido.tempo2bpm(msg.tempo) - 140.0) < 0.1
            elif msg.type == "time_signature":
                assert msg.numerator == 3
                assert msg.denominator == 4
            elif msg.type == "key_signature":
                assert msg.key == "D"

    def test_no_key_signature(self):
        m = MidiModel(title="No Key")
        conductor = m.file.tracks[0]
        types = [msg.type for msg in conductor]
        assert "key_signature" not in types


# ---------------------------------------------------------------------------
# Track CRUD
# ---------------------------------------------------------------------------

class TestTrackCRUD:
    def test_add_track(self):
        m = MidiModel()
        label = m.add_track("Piano", program=0)
        assert label == "Piano"
        assert "Piano" in m.tracks
        assert m.track_order == ["Piano"]
        assert len(m.file.tracks) == 2  # conductor + Piano

    def test_add_track_with_bank_select(self):
        m = MidiModel()
        m.add_track("Strings", program=48, bank_msb=1, bank_lsb=2)
        ref = m.tracks["Strings"]
        assert ref.program == 48
        assert ref.bank_msb == 1
        assert ref.bank_lsb == 2

        # Verify mido messages include bank select CCs
        msgs = list(ref.track)
        cc_msgs = [msg for msg in msgs if msg.type == "control_change"]
        assert len(cc_msgs) == 2
        assert cc_msgs[0].control == 0 and cc_msgs[0].value == 1
        assert cc_msgs[1].control == 32 and cc_msgs[1].value == 2

    def test_add_track_explicit_channel(self):
        m = MidiModel()
        m.add_track("Drums", channel=9, program=0)
        assert m.tracks["Drums"].channel == 9

    def test_add_duplicate_track_raises(self):
        m = MidiModel()
        m.add_track("Piano")
        with pytest.raises(ValueError, match="already exists"):
            m.add_track("Piano")

    def test_remove_track(self):
        m = MidiModel()
        m.add_track("Piano")
        m.add_track("Bass")
        removed = m.remove_track("Piano")
        assert removed is not None
        assert removed.name == "Piano"
        assert "Piano" not in m.tracks
        assert "Piano" not in m.track_order
        assert len(m.file.tracks) == 2  # conductor + Bass

    def test_remove_nonexistent_track(self):
        m = MidiModel()
        assert m.remove_track("Ghost") is None

    def test_get_track(self):
        m = MidiModel()
        m.add_track("Piano")
        ref = m.get_track("Piano")
        assert ref is not None
        assert ref.name == "Piano"
        assert m.get_track("Nonexistent") is None


# ---------------------------------------------------------------------------
# Channel auto-assignment
# ---------------------------------------------------------------------------

class TestChannelAutoAssignment:
    def test_first_track_gets_channel_0(self):
        m = MidiModel()
        m.add_track("First")
        assert m.tracks["First"].channel == 0

    def test_skip_channel_9(self):
        m = MidiModel()
        # Fill channels 0-8
        for i in range(9):
            m.add_track(f"Track{i}")
        # Next should be 10 (skipping 9)
        m.add_track("Track9")
        assert m.tracks["Track9"].channel == 10

    def test_all_channels_used(self):
        m = MidiModel()
        # Fill all 15 usable channels
        channels_order = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15]
        for i, _ch in enumerate(channels_order):
            m.add_track(f"T{i}")
        # 16th track should fall back to 0
        m.add_track("Overflow")
        assert m.tracks["Overflow"].channel == 0

    def test_explicit_channel_not_auto_assigned(self):
        m = MidiModel()
        m.add_track("Drums", channel=9)
        # Channel 9 used explicitly; auto should still start at 0
        m.add_track("Piano")
        assert m.tracks["Piano"].channel == 0


# ---------------------------------------------------------------------------
# Save / Load round-trip
# ---------------------------------------------------------------------------

class TestSaveLoad:
    def test_round_trip(self):
        m = MidiModel(title="Round Trip", tempo=100.0, time_sig=(6, 8), key="G")
        m.add_track("Piano", program=0)
        m.add_track("Bass", program=32, channel=1)

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            path = f.name
        try:
            m.save(path)
            loaded = MidiModel.load(path)

            assert loaded.title == "Round Trip"
            assert loaded.ppqn == 480
            assert len(loaded.tracks) == 2
            assert "Piano" in loaded.tracks
            assert "Bass" in loaded.tracks
            assert loaded.tracks["Piano"].program == 0
            assert loaded.tracks["Bass"].program == 32
            assert loaded.tracks["Bass"].channel == 1
            assert loaded.track_order == ["Piano", "Bass"]
        finally:
            os.unlink(path)

    def test_save_load_with_notes(self):
        m = MidiModel(title="Notes Test")
        m.add_track("Lead", program=80)
        ref = m.tracks["Lead"]
        ch = ref.channel

        # Add some notes via mido directly
        insert_message_at_tick(
            ref.track,
            mido.Message("note_on", channel=ch, note=60, velocity=100),
            0,
        )
        insert_message_at_tick(
            ref.track,
            mido.Message("note_off", channel=ch, note=60, velocity=0),
            480,
        )

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            path = f.name
        try:
            m.save(path)
            loaded = MidiModel.load(path)
            assert "Lead" in loaded.tracks
            # Check note_on is present
            lead = loaded.tracks["Lead"]
            note_ons = [
                msg for msg in lead.track
                if msg.type == "note_on" and msg.velocity > 0
            ]
            assert len(note_ons) == 1
            assert note_ons[0].note == 60
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Snapshot / Restore
# ---------------------------------------------------------------------------

class TestSnapshotRestore:
    def test_snapshot_restore_roundtrip(self):
        m = MidiModel(title="Snap", tempo=90.0)
        m.add_track("Guitar", program=25)

        snap = m.snapshot()
        assert isinstance(snap, bytes)
        assert len(snap) > 0

        # Mutate the model
        m.add_track("Drums", channel=9, program=0)
        assert len(m.tracks) == 2

        # Restore
        m.restore(snap)
        assert len(m.tracks) == 1
        assert "Guitar" in m.tracks
        assert "Drums" not in m.tracks
        assert m.title == "Snap"

    def test_restore_preserves_ppqn(self):
        m = MidiModel(ppqn=960)
        snap = m.snapshot()
        m2 = MidiModel(ppqn=480)
        m2.restore(snap)
        assert m2.ppqn == 960


# ---------------------------------------------------------------------------
# Absolute <-> Delta tick conversion
# ---------------------------------------------------------------------------

class TestTickConversion:
    def test_absolute_to_delta(self):
        msgs = [
            (0, mido.Message("note_on", note=60, velocity=100)),
            (480, mido.Message("note_off", note=60, velocity=0)),
            (480, mido.Message("note_on", note=64, velocity=100)),
            (960, mido.Message("note_off", note=64, velocity=0)),
        ]
        result = absolute_to_delta(msgs)
        assert [m.time for m in result] == [0, 480, 0, 480]

    def test_absolute_to_delta_unsorted_input(self):
        msgs = [
            (960, mido.Message("note_off", note=64, velocity=0)),
            (0, mido.Message("note_on", note=60, velocity=100)),
            (480, mido.Message("note_off", note=60, velocity=0)),
        ]
        result = absolute_to_delta(msgs)
        assert [m.time for m in result] == [0, 480, 480]

    def test_delta_to_absolute(self):
        track = mido.MidiTrack()
        track.append(mido.Message("note_on", note=60, velocity=100, time=0))
        track.append(mido.Message("note_off", note=60, velocity=0, time=480))
        track.append(mido.Message("note_on", note=64, velocity=100, time=0))
        track.append(
            mido.Message("note_off", note=64, velocity=0, time=480)
        )

        result = delta_to_absolute(track)
        abs_ticks = [t for t, _ in result]
        assert abs_ticks == [0, 480, 480, 960]

    def test_roundtrip_absolute_delta(self):
        original = [
            (0, mido.Message("note_on", note=60, velocity=100)),
            (100, mido.Message("note_on", note=64, velocity=80)),
            (480, mido.Message("note_off", note=60, velocity=0)),
            (580, mido.Message("note_off", note=64, velocity=0)),
        ]
        delta_msgs = absolute_to_delta(original)
        track = mido.MidiTrack()
        track.extend(delta_msgs)

        recovered = delta_to_absolute(track)
        for (orig_tick, orig_msg), (rec_tick, rec_msg) in zip(
            original, recovered
        ):
            assert orig_tick == rec_tick
            assert orig_msg.note == rec_msg.note


# ---------------------------------------------------------------------------
# Insert / Remove message at tick
# ---------------------------------------------------------------------------

class TestInsertRemoveMessage:
    def _make_track_with_notes(self) -> mido.MidiTrack:
        """Track: note_on@0, note_off@480, end_of_track@480."""
        track = mido.MidiTrack()
        track.append(
            mido.Message("note_on", note=60, velocity=100, time=0)
        )
        track.append(
            mido.Message("note_off", note=60, velocity=0, time=480)
        )
        track.append(mido.MetaMessage("end_of_track", time=0))
        return track

    def test_insert_at_beginning(self):
        track = self._make_track_with_notes()
        insert_message_at_tick(
            track,
            mido.Message("note_on", note=64, velocity=80),
            0,
        )
        # Should be inserted at the beginning
        abs_ticks = [t for t, _ in delta_to_absolute(track)]
        notes = [
            (t, m.note)
            for t, m in delta_to_absolute(track)
            if m.type == "note_on"
        ]
        assert (0, 64) in notes
        assert (0, 60) in notes

    def test_insert_in_middle(self):
        track = self._make_track_with_notes()
        insert_message_at_tick(
            track,
            mido.Message("note_on", note=64, velocity=80),
            240,
        )
        pairs = delta_to_absolute(track)
        note_ons = [
            (t, m.note) for t, m in pairs if m.type == "note_on"
        ]
        assert (0, 60) in note_ons
        assert (240, 64) in note_ons

    def test_insert_at_end(self):
        track = self._make_track_with_notes()
        insert_message_at_tick(
            track,
            mido.Message("note_on", note=64, velocity=80),
            960,
        )
        pairs = delta_to_absolute(track)
        note_ons = [
            (t, m.note) for t, m in pairs if m.type == "note_on"
        ]
        assert (960, 64) in note_ons
        # end_of_track should still be last
        assert pairs[-1][1].type == "end_of_track"

    def test_remove_message(self):
        track = self._make_track_with_notes()
        # Remove note_on at index 0
        remove_message_at_index(track, 0)
        assert len(track) == 2  # note_off + end_of_track
        # The note_off should now have time = 480 (absorbed the 0 delta)
        assert track[0].time == 480

    def test_remove_preserves_timing(self):
        track = mido.MidiTrack()
        track.append(
            mido.Message("note_on", note=60, velocity=100, time=0)
        )
        track.append(
            mido.Message("note_on", note=64, velocity=80, time=240)
        )
        track.append(
            mido.Message("note_off", note=60, velocity=0, time=240)
        )
        track.append(mido.MetaMessage("end_of_track", time=0))

        # Remove middle note_on (index 1, delta=240)
        remove_message_at_index(track, 1)
        # note_off should now be at absolute tick 480 (0 + 240 + 240)
        pairs = delta_to_absolute(track)
        note_offs = [
            (t, m) for t, m in pairs if m.type == "note_off"
        ]
        assert note_offs[0][0] == 480

    def test_remove_out_of_range(self):
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("end_of_track", time=0))
        with pytest.raises(IndexError):
            remove_message_at_index(track, 5)


# ---------------------------------------------------------------------------
# Track metadata extraction
# ---------------------------------------------------------------------------

class TestTrackMetadataExtraction:
    def test_extract_basic(self):
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name="Violin", time=0))
        track.append(
            mido.Message("program_change", channel=3, program=40, time=0)
        )
        track.append(mido.MetaMessage("end_of_track", time=0))

        meta = _extract_track_metadata(track)
        assert meta["name"] == "Violin"
        assert meta["channel"] == 3
        assert meta["program"] == 40

    def test_extract_with_bank_select(self):
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name="Synth", time=0))
        track.append(
            mido.Message(
                "control_change", channel=5, control=0, value=10, time=0
            )
        )
        track.append(
            mido.Message(
                "control_change", channel=5, control=32, value=3, time=0
            )
        )
        track.append(
            mido.Message("program_change", channel=5, program=81, time=0)
        )
        track.append(mido.MetaMessage("end_of_track", time=0))

        meta = _extract_track_metadata(track)
        assert meta["bank_msb"] == 10
        assert meta["bank_lsb"] == 3
        assert meta["program"] == 81
        assert meta["channel"] == 5

    def test_extract_empty_track(self):
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("end_of_track", time=0))
        meta = _extract_track_metadata(track)
        assert meta["name"] == ""
        assert meta["program"] == 0


# ---------------------------------------------------------------------------
# Rebuild index
# ---------------------------------------------------------------------------

class TestRebuildIndex:
    def test_rebuild_from_loaded_file(self):
        m = MidiModel(title="Rebuild Test")
        m.add_track("Piano", program=0, channel=0)
        m.add_track("Bass", program=32, channel=1)

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            path = f.name
        try:
            m.save(path)

            # Load raw and rebuild
            m2 = MidiModel.__new__(MidiModel)
            m2.file = mido.MidiFile(filename=path)
            m2.tracks = {}
            m2.track_order = []
            m2.title = "Untitled"
            m2.rebuild_index()

            assert m2.title == "Rebuild Test"
            assert len(m2.tracks) == 2
            assert "Piano" in m2.tracks
            assert "Bass" in m2.tracks
        finally:
            os.unlink(path)

    def test_rebuild_handles_unnamed_tracks(self):
        m = MidiModel()
        # Manually add a track without a name
        track = mido.MidiTrack()
        track.append(
            mido.Message("program_change", channel=0, program=10, time=0)
        )
        track.append(mido.MetaMessage("end_of_track", time=0))
        m.file.tracks.append(track)

        m.rebuild_index()
        assert len(m.tracks) == 1
        # Should have a fallback name
        label = m.track_order[0]
        assert label.startswith("Track")


# ---------------------------------------------------------------------------
# Digest
# ---------------------------------------------------------------------------

class TestDigest:
    def test_empty_digest(self):
        m = MidiModel(title="Test", tempo=120.0, time_sig=(4, 4))
        digest = m.get_digest()
        assert "0t" in digest
        assert "0n" in digest
        assert "tempo:120" in digest
        assert "4/4" in digest

    def test_digest_with_tracks(self):
        m = MidiModel(title="Test", key="Am")
        m.add_track("Piano", program=0)
        digest = m.get_digest()
        assert "1t" in digest
        assert "Am" in digest

    def test_digest_with_notes(self):
        m = MidiModel()
        m.add_track("Lead", program=80)
        ref = m.tracks["Lead"]
        # Add a note
        insert_message_at_tick(
            ref.track,
            mido.Message("note_on", channel=ref.channel, note=60, velocity=100),
            0,
        )
        insert_message_at_tick(
            ref.track,
            mido.Message("note_off", channel=ref.channel, note=60, velocity=0),
            480,
        )
        digest = m.get_digest()
        assert "1n" in digest


# ---------------------------------------------------------------------------
# Note addition
# ---------------------------------------------------------------------------

class TestAddNote:
    def test_add_single_note(self):
        m = MidiModel()
        m.add_track("Piano", program=0)
        nr = m.add_note("Piano", pitch=60, abs_tick=0, duration_ticks=480)
        assert nr.pitch == 60
        assert nr.abs_tick == 0
        assert nr.duration_ticks == 480
        assert nr.velocity == 80  # default
        assert nr.channel == 0
        assert nr.track_name == "Piano"

        # Verify the messages are actually in the track
        ref = m.tracks["Piano"]
        note_ons = [
            msg for msg in ref.track
            if msg.type == "note_on" and msg.velocity > 0
        ]
        note_offs = [
            msg for msg in ref.track if msg.type == "note_off"
        ]
        assert len(note_ons) == 1
        assert len(note_offs) == 1
        assert note_ons[0].note == 60
        assert note_offs[0].note == 60

    def test_add_note_custom_velocity_and_channel(self):
        m = MidiModel()
        m.add_track("Lead", program=80)
        nr = m.add_note(
            "Lead", pitch=72, abs_tick=960, duration_ticks=240,
            velocity=120, channel=5,
        )
        assert nr.velocity == 120
        assert nr.channel == 5

    def test_add_multiple_notes_ordering(self):
        m = MidiModel()
        m.add_track("Piano", program=0)
        m.add_note("Piano", pitch=60, abs_tick=0, duration_ticks=480)
        m.add_note("Piano", pitch=64, abs_tick=480, duration_ticks=480)
        m.add_note("Piano", pitch=67, abs_tick=960, duration_ticks=480)

        notes = m.get_notes("Piano")
        assert len(notes) == 3
        assert [n.pitch for n in notes] == [60, 64, 67]
        assert [n.abs_tick for n in notes] == [0, 480, 960]

    def test_add_chord(self):
        """Multiple notes at the same tick."""
        m = MidiModel()
        m.add_track("Piano", program=0)
        m.add_note("Piano", pitch=60, abs_tick=0, duration_ticks=480)
        m.add_note("Piano", pitch=64, abs_tick=0, duration_ticks=480)
        m.add_note("Piano", pitch=67, abs_tick=0, duration_ticks=480)

        notes = m.get_notes("Piano")
        assert len(notes) == 3
        assert all(n.abs_tick == 0 for n in notes)
        pitches = {n.pitch for n in notes}
        assert pitches == {60, 64, 67}

    def test_add_note_nonexistent_track_raises(self):
        m = MidiModel()
        with pytest.raises(KeyError, match="not found"):
            m.add_note("Ghost", pitch=60, abs_tick=0, duration_ticks=480)


# ---------------------------------------------------------------------------
# Note removal
# ---------------------------------------------------------------------------

class TestRemoveNote:
    def test_remove_note_at(self):
        m = MidiModel()
        m.add_track("Piano", program=0)
        m.add_note("Piano", pitch=60, abs_tick=0, duration_ticks=480)
        m.add_note("Piano", pitch=64, abs_tick=480, duration_ticks=480)

        removed = m.remove_note_at("Piano", pitch=60, abs_tick=0)
        assert removed is not None
        assert removed.pitch == 60

        notes = m.get_notes("Piano")
        assert len(notes) == 1
        assert notes[0].pitch == 64
        assert notes[0].abs_tick == 480

    def test_remove_note_via_noteref(self):
        m = MidiModel()
        m.add_track("Piano", program=0)
        nr = m.add_note("Piano", pitch=60, abs_tick=0, duration_ticks=480)

        removed = m.remove_note("Piano", nr)
        assert removed is not None
        assert m.get_notes("Piano") == []

    def test_remove_preserves_other_notes_timing(self):
        m = MidiModel()
        m.add_track("Piano", program=0)
        m.add_note("Piano", pitch=60, abs_tick=0, duration_ticks=480)
        m.add_note("Piano", pitch=64, abs_tick=480, duration_ticks=480)
        m.add_note("Piano", pitch=67, abs_tick=960, duration_ticks=480)

        m.remove_note_at("Piano", pitch=64, abs_tick=480)
        notes = m.get_notes("Piano")
        assert len(notes) == 2
        assert notes[0].pitch == 60
        assert notes[0].abs_tick == 0
        assert notes[1].pitch == 67
        assert notes[1].abs_tick == 960

    def test_remove_nonexistent_note(self):
        m = MidiModel()
        m.add_track("Piano", program=0)
        m.add_note("Piano", pitch=60, abs_tick=0, duration_ticks=480)

        removed = m.remove_note_at("Piano", pitch=72, abs_tick=0)
        assert removed is None
        assert len(m.get_notes("Piano")) == 1

    def test_remove_from_chord(self):
        m = MidiModel()
        m.add_track("Piano", program=0)
        m.add_note("Piano", pitch=60, abs_tick=0, duration_ticks=480)
        m.add_note("Piano", pitch=64, abs_tick=0, duration_ticks=480)
        m.add_note("Piano", pitch=67, abs_tick=0, duration_ticks=480)

        m.remove_note_at("Piano", pitch=64, abs_tick=0)
        notes = m.get_notes("Piano")
        assert len(notes) == 2
        pitches = {n.pitch for n in notes}
        assert pitches == {60, 67}


# ---------------------------------------------------------------------------
# Note querying (get_notes)
# ---------------------------------------------------------------------------

class TestGetNotes:
    def test_get_notes_single_track(self):
        m = MidiModel()
        m.add_track("Piano", program=0)
        m.add_note("Piano", pitch=60, abs_tick=0, duration_ticks=480)
        m.add_note("Piano", pitch=64, abs_tick=480, duration_ticks=240)

        notes = m.get_notes("Piano")
        assert len(notes) == 2
        assert notes[0].duration_ticks == 480
        assert notes[1].duration_ticks == 240

    def test_get_notes_all_tracks(self):
        m = MidiModel()
        m.add_track("Piano", program=0)
        m.add_track("Bass", program=32)
        m.add_note("Piano", pitch=60, abs_tick=0, duration_ticks=480)
        m.add_note("Bass", pitch=36, abs_tick=0, duration_ticks=960)

        notes = m.get_notes()
        assert len(notes) == 2
        track_names = {n.track_name for n in notes}
        assert track_names == {"Piano", "Bass"}

    def test_get_notes_nonexistent_track_raises(self):
        m = MidiModel()
        with pytest.raises(KeyError, match="not found"):
            m.get_notes("Ghost")

    def test_get_notes_empty_track(self):
        m = MidiModel()
        m.add_track("Piano", program=0)
        assert m.get_notes("Piano") == []


# ---------------------------------------------------------------------------
# Note pairing (pair_notes utility)
# ---------------------------------------------------------------------------

class TestPairNotes:
    def test_simple_pair(self):
        track = mido.MidiTrack()
        track.append(mido.Message("note_on", note=60, velocity=100, time=0))
        track.append(mido.Message("note_off", note=60, velocity=0, time=480))
        track.append(mido.MetaMessage("end_of_track", time=0))

        notes = pair_notes(track, track_name="test")
        assert len(notes) == 1
        assert notes[0].pitch == 60
        assert notes[0].abs_tick == 0
        assert notes[0].duration_ticks == 480

    def test_overlapping_same_pitch(self):
        """Two notes of the same pitch, overlapping — FIFO pairing."""
        track = mido.MidiTrack()
        # First note_on at tick 0
        track.append(mido.Message("note_on", note=60, velocity=100, time=0))
        # Second note_on at tick 240
        track.append(mido.Message("note_on", note=60, velocity=80, time=240))
        # First note_off at tick 480
        track.append(mido.Message("note_off", note=60, velocity=0, time=240))
        # Second note_off at tick=720
        track.append(mido.Message("note_off", note=60, velocity=0, time=240))
        track.append(mido.MetaMessage("end_of_track", time=0))

        notes = pair_notes(track, track_name="test")
        assert len(notes) == 2
        # FIFO: first note_on pairs with first note_off
        assert notes[0].abs_tick == 0
        assert notes[0].duration_ticks == 480
        assert notes[0].velocity == 100
        assert notes[1].abs_tick == 240
        assert notes[1].duration_ticks == 480
        assert notes[1].velocity == 80

    def test_velocity_zero_as_note_off(self):
        """note_on with velocity=0 should act as note_off."""
        track = mido.MidiTrack()
        track.append(mido.Message("note_on", note=60, velocity=100, time=0))
        # note_on vel=0 is equivalent to note_off
        track.append(mido.Message("note_on", note=60, velocity=0, time=480))
        track.append(mido.MetaMessage("end_of_track", time=0))

        notes = pair_notes(track, track_name="test")
        assert len(notes) == 1
        assert notes[0].pitch == 60
        assert notes[0].duration_ticks == 480

    def test_multiple_pitches(self):
        track = mido.MidiTrack()
        track.append(mido.Message("note_on", note=60, velocity=100, time=0))
        track.append(mido.Message("note_on", note=64, velocity=90, time=0))
        track.append(mido.Message("note_off", note=60, velocity=0, time=480))
        track.append(mido.Message("note_off", note=64, velocity=0, time=0))
        track.append(mido.MetaMessage("end_of_track", time=0))

        notes = pair_notes(track, track_name="test")
        assert len(notes) == 2
        pitches = {n.pitch for n in notes}
        assert pitches == {60, 64}

    def test_unpaired_note_on_ignored(self):
        """A note_on with no matching note_off should not appear in results."""
        track = mido.MidiTrack()
        track.append(mido.Message("note_on", note=60, velocity=100, time=0))
        track.append(mido.MetaMessage("end_of_track", time=0))

        notes = pair_notes(track, track_name="test")
        assert len(notes) == 0

    def test_indices_are_correct(self):
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name="Lead", time=0))  # idx 0
        track.append(mido.Message("program_change", channel=0, program=0, time=0))  # idx 1
        track.append(mido.Message("note_on", note=60, velocity=100, time=0))  # idx 2
        track.append(mido.Message("note_off", note=60, velocity=0, time=480))  # idx 3
        track.append(mido.MetaMessage("end_of_track", time=0))  # idx 4

        notes = pair_notes(track, track_name="Lead")
        assert len(notes) == 1
        assert notes[0].note_on_idx == 2
        assert notes[0].note_off_idx == 3


# ---------------------------------------------------------------------------
# NoteIndex
# ---------------------------------------------------------------------------

class TestNoteIndex:
    def _make_model_with_notes(self) -> MidiModel:
        m = MidiModel()
        m.add_track("Piano", program=0, channel=0)
        m.add_track("Bass", program=32, channel=1)
        m.add_note("Piano", pitch=60, abs_tick=0, duration_ticks=480, velocity=80)
        m.add_note("Piano", pitch=64, abs_tick=0, duration_ticks=480, velocity=100)
        m.add_note("Piano", pitch=67, abs_tick=480, duration_ticks=480, velocity=40)
        m.add_note("Bass", pitch=36, abs_tick=0, duration_ticks=960, velocity=90)
        return m

    def test_rebuild(self):
        m = self._make_model_with_notes()
        idx = NoteIndex()
        idx.rebuild(m)
        assert len(idx.all) == 4

    def test_by_track(self):
        m = self._make_model_with_notes()
        idx = NoteIndex()
        idx.rebuild(m)
        assert len(idx.by_track["Piano"]) == 3
        assert len(idx.by_track["Bass"]) == 1

    def test_by_pitch(self):
        m = self._make_model_with_notes()
        idx = NoteIndex()
        idx.rebuild(m)
        assert len(idx.by_pitch[60]) == 1
        assert len(idx.by_pitch[64]) == 1
        assert len(idx.by_pitch[67]) == 1
        assert len(idx.by_pitch[36]) == 1
        assert len(idx.by_pitch.get(72, [])) == 0

    def test_by_channel(self):
        m = self._make_model_with_notes()
        idx = NoteIndex()
        idx.rebuild(m)
        assert len(idx.by_channel[0]) == 3  # Piano on channel 0
        assert len(idx.by_channel[1]) == 1  # Bass on channel 1

    def test_by_velocity_range(self):
        m = self._make_model_with_notes()
        idx = NoteIndex()
        idx.rebuild(m)
        # All notes: 80, 100, 40, 90
        loud = idx.by_velocity_range(90, 127)
        assert len(loud) == 2
        soft = idx.by_velocity_range(1, 50)
        assert len(soft) == 1
        assert soft[0].pitch == 67

    def test_rebuild_after_mutation(self):
        m = self._make_model_with_notes()
        idx = NoteIndex()
        idx.rebuild(m)
        assert len(idx.all) == 4

        m.add_note("Piano", pitch=72, abs_tick=960, duration_ticks=480, velocity=110)
        idx.rebuild(m)
        assert len(idx.all) == 5
        assert len(idx.by_pitch[72]) == 1

    def test_rebuild_after_removal(self):
        m = self._make_model_with_notes()
        idx = NoteIndex()
        idx.rebuild(m)
        assert len(idx.all) == 4

        m.remove_note_at("Piano", pitch=60, abs_tick=0)
        idx.rebuild(m)
        assert len(idx.all) == 3
        assert len(idx.by_pitch.get(60, [])) == 0
