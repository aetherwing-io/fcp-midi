"""Tests for Song CRUD, auto-channel assignment, digest, and EventLog."""

from fcp_midi.model.song import Pitch, Song
from fcp_midi.model.event_log import (
    CheckpointEvent,
    EventLog,
    NoteAdded,
    NoteRemoved,
    TrackAdded,
    TrackRemoved,
    CCAdded,
    PitchBendAdded,
    TempoChanged,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _c4() -> Pitch:
    return Pitch(name="C", accidental="", octave=4, midi_number=60)


def _d4() -> Pitch:
    return Pitch(name="D", accidental="", octave=4, midi_number=62)


# ---------------------------------------------------------------------------
# Song.create
# ---------------------------------------------------------------------------


class TestSongCreate:
    def test_defaults(self):
        s = Song.create()
        assert s.title == "Untitled"
        assert s.ppqn == 480
        assert len(s.tempo_map) == 1
        assert s.tempo_map[0].bpm == 120.0
        assert len(s.time_signatures) == 1
        assert s.time_signatures[0].numerator == 4
        assert s.time_signatures[0].denominator == 4

    def test_custom_values(self):
        s = Song.create(title="My Song", tempo=140.0, time_sig=(3, 4), key="G-major")
        assert s.title == "My Song"
        assert s.tempo_map[0].bpm == 140.0
        assert s.time_signatures[0].numerator == 3
        assert len(s.key_signatures) == 1
        assert s.key_signatures[0].key == "G"
        assert s.key_signatures[0].mode == "major"


# ---------------------------------------------------------------------------
# Track CRUD
# ---------------------------------------------------------------------------


class TestTrackCRUD:
    def test_add_and_get_track(self):
        s = Song.create()
        t = s.add_track("Piano")
        assert t.name == "Piano"
        assert t.id in s.tracks
        assert s.get_track_by_name("piano") is t  # case-insensitive

    def test_remove_track(self):
        s = Song.create()
        t = s.add_track("Bass")
        removed = s.remove_track(t.id)
        assert removed is t
        assert t.id not in s.tracks
        assert t.id not in s.track_order

    def test_remove_nonexistent(self):
        s = Song.create()
        assert s.remove_track("does-not-exist") is None

    def test_get_track_by_name_miss(self):
        s = Song.create()
        assert s.get_track_by_name("Nope") is None


# ---------------------------------------------------------------------------
# Note CRUD
# ---------------------------------------------------------------------------


class TestNoteCRUD:
    def test_add_and_remove_note(self):
        s = Song.create()
        t = s.add_track("Lead")
        n = s.add_note(t.id, _c4(), absolute_tick=0, duration_ticks=480)
        assert n.id in t.notes
        assert n.pitch.midi_number == 60
        assert n.velocity == 80  # default

        removed = s.remove_note(t.id, n.id)
        assert removed is n
        assert n.id not in t.notes

    def test_remove_note_from_missing_track(self):
        s = Song.create()
        assert s.remove_note("bad_track", "bad_note") is None

    def test_note_inherits_track_channel(self):
        s = Song.create()
        t = s.add_track("Lead", channel=5)
        n = s.add_note(t.id, _c4(), absolute_tick=0, duration_ticks=240)
        assert n.channel == 5

    def test_note_explicit_channel(self):
        s = Song.create()
        t = s.add_track("Lead", channel=5)
        n = s.add_note(t.id, _c4(), absolute_tick=0, duration_ticks=240, channel=3)
        assert n.channel == 3


# ---------------------------------------------------------------------------
# CC / PitchBend
# ---------------------------------------------------------------------------


class TestCCAndPitchBend:
    def test_add_cc(self):
        s = Song.create()
        t = s.add_track("Synth")
        cc = s.add_cc(t.id, controller=1, value=64, absolute_tick=0)
        assert cc.id in t.control_changes
        assert cc.controller == 1
        assert cc.value == 64

    def test_add_pitch_bend(self):
        s = Song.create()
        t = s.add_track("Strings")
        pb = s.add_pitch_bend(t.id, value=4000, absolute_tick=0)
        assert pb.id in t.pitch_bends
        assert pb.value == 4000


# ---------------------------------------------------------------------------
# Auto-channel assignment (skip channel 9)
# ---------------------------------------------------------------------------


class TestAutoChannel:
    def test_first_track_gets_channel_0(self):
        s = Song.create()
        t = s.add_track("A")
        assert t.channel == 0

    def test_skips_channel_9(self):
        s = Song.create()
        # Channels 0-8 -> tracks 1-9
        for i in range(9):
            s.add_track(f"T{i}")
        # The 10th track should skip channel 9 (drums) and get 10
        t10 = s.add_track("T9")
        assert t10.channel == 10

    def test_sequential_channels(self):
        s = Song.create()
        channels = []
        for i in range(16):
            t = s.add_track(f"T{i}")
            channels.append(t.channel)
        # Should be 0,1,2,...,8,10,11,...,15,0 (wraps)
        assert 9 not in channels[:15]  # first 15 should never be 9


# ---------------------------------------------------------------------------
# get_digest
# ---------------------------------------------------------------------------


class TestDigest:
    def test_empty_song(self):
        s = Song.create()
        d = s.get_digest()
        assert "0t" in d
        assert "0e" in d
        assert "tempo:120" in d
        assert "4/4" in d

    def test_with_notes(self):
        s = Song.create()
        t = s.add_track("Piano")
        s.add_note(t.id, _c4(), absolute_tick=0, duration_ticks=480)
        d = s.get_digest()
        assert "1t" in d
        assert "1e" in d


# ---------------------------------------------------------------------------
# EventLog
# ---------------------------------------------------------------------------


class TestEventLogAppend:
    def test_append_increments_cursor(self):
        log = EventLog()
        log.append(NoteAdded(track_id="t1", note_id="n1"))
        assert log.cursor == 1
        log.append(NoteAdded(track_id="t1", note_id="n2"))
        assert log.cursor == 2

    def test_events_stored(self):
        log = EventLog()
        e1 = NoteAdded(track_id="t1", note_id="n1")
        log.append(e1)
        assert log.events == [e1]


class TestEventLogUndo:
    def test_undo_single(self):
        log = EventLog()
        e1 = NoteAdded(track_id="t1", note_id="n1")
        log.append(e1)
        undone = log.undo()
        assert undone == [e1]
        assert log.cursor == 0

    def test_undo_multiple(self):
        log = EventLog()
        e1 = NoteAdded(track_id="t1", note_id="n1")
        e2 = TrackAdded(track_id="t2")
        log.append(e1)
        log.append(e2)
        undone = log.undo(2)
        assert undone == [e2, e1]  # most-recent-first
        assert log.cursor == 0

    def test_undo_past_beginning(self):
        log = EventLog()
        log.append(NoteAdded(track_id="t1", note_id="n1"))
        undone = log.undo(5)
        assert len(undone) == 1
        assert log.cursor == 0

    def test_undo_empty(self):
        log = EventLog()
        assert log.undo() == []


class TestEventLogRedo:
    def test_redo_after_undo(self):
        log = EventLog()
        e1 = NoteAdded(track_id="t1", note_id="n1")
        log.append(e1)
        log.undo()
        redone = log.redo()
        assert redone == [e1]
        assert log.cursor == 1

    def test_redo_multiple(self):
        log = EventLog()
        e1 = NoteAdded(track_id="t1", note_id="n1")
        e2 = TrackAdded(track_id="t2")
        log.append(e1)
        log.append(e2)
        log.undo(2)
        redone = log.redo(2)
        assert redone == [e1, e2]  # forward order

    def test_redo_nothing(self):
        log = EventLog()
        log.append(NoteAdded(track_id="t1", note_id="n1"))
        assert log.redo() == []  # nothing to redo


class TestEventLogTruncation:
    def test_append_truncates_redo(self):
        log = EventLog()
        e1 = NoteAdded(track_id="t1", note_id="n1")
        e2 = NoteAdded(track_id="t1", note_id="n2")
        e3 = NoteAdded(track_id="t1", note_id="n3")
        log.append(e1)
        log.append(e2)
        log.undo()  # cursor at 1, e2 is in redo tail
        log.append(e3)  # should truncate e2

        assert log.cursor == 2
        assert len(log.events) == 2
        assert log.events[0] is e1
        assert log.events[1] is e3

        # Redo should yield nothing since e2 is gone
        assert log.redo() == []


class TestEventLogCheckpoint:
    def test_checkpoint_and_undo_to(self):
        log = EventLog()
        e1 = NoteAdded(track_id="t1", note_id="n1")
        log.append(e1)
        log.checkpoint("v1")
        e2 = NoteAdded(track_id="t1", note_id="n2")
        e3 = TrackAdded(track_id="t3")
        log.append(e2)
        log.append(e3)

        undone = log.undo_to("v1")
        # Should return e3 and e2, most-recent-first
        assert undone == [e3, e2]

    def test_undo_to_missing_checkpoint_raises(self):
        log = EventLog()
        try:
            log.undo_to("nope")
            assert False, "Expected KeyError"
        except KeyError:
            pass

    def test_checkpoint_truncated_on_new_append(self):
        log = EventLog()
        log.append(NoteAdded(track_id="t1", note_id="n1"))
        log.checkpoint("v1")  # cursor=2 (event + checkpoint event)
        log.append(NoteAdded(track_id="t1", note_id="n2"))

        # Undo back past the checkpoint event and the second note
        log.undo(2)  # undo n2 and n1 (checkpoint skipped)
        # Now cursor should be at 0
        # Append something new — should truncate everything
        log.append(TrackAdded(track_id="t9"))

        # The v1 checkpoint pointed to cursor=1, which is now gone
        try:
            log.undo_to("v1")
            assert False, "Expected KeyError (checkpoint should be invalidated)"
        except KeyError:
            pass


class TestEventLogRecent:
    def test_recent_default(self):
        log = EventLog()
        events = []
        for i in range(7):
            e = NoteAdded(track_id="t1", note_id=f"n{i}")
            log.append(e)
            events.append(e)

        recent = log.recent()
        assert len(recent) == 5
        assert recent == events[2:7]  # last 5 in chronological order

    def test_recent_skips_checkpoints(self):
        log = EventLog()
        e1 = NoteAdded(track_id="t1", note_id="n1")
        e2 = NoteAdded(track_id="t1", note_id="n2")
        log.append(e1)
        log.checkpoint("v1")
        log.append(e2)

        recent = log.recent(5)
        # Should only contain e1 and e2, not the checkpoint
        assert recent == [e1, e2]

    def test_recent_fewer_than_requested(self):
        log = EventLog()
        e1 = NoteAdded(track_id="t1", note_id="n1")
        log.append(e1)
        assert log.recent(10) == [e1]


# ---------------------------------------------------------------------------
# Registry incremental methods
# ---------------------------------------------------------------------------

from fcp_midi.model.registry import Registry


def _song_with_notes():
    """Create a song with 2 tracks and a few notes for registry tests."""
    s = Song.create(title="RegTest", tempo=120.0, time_sig=(4, 4))
    piano = s.add_track("Piano")
    bass = s.add_track("Bass")
    n1 = s.add_note(piano.id, _c4(), absolute_tick=0, duration_ticks=480, velocity=80)
    n2 = s.add_note(piano.id, _d4(), absolute_tick=480, duration_ticks=480, velocity=90)
    n3 = s.add_note(bass.id, _c4(), absolute_tick=0, duration_ticks=960, velocity=100)
    return s, piano, bass, n1, n2, n3


class TestRegistryAddNote:
    def test_add_note_indexes_correctly(self):
        s, piano, bass, n1, n2, n3 = _song_with_notes()
        reg = Registry()
        reg.add_note(n1, "Piano")
        assert len(reg.by_track("Piano")) == 1
        assert len(reg.by_pitch(60)) == 1
        assert reg.by_track("Piano")[0].id == n1.id

    def test_add_multiple_notes(self):
        s, piano, bass, n1, n2, n3 = _song_with_notes()
        reg = Registry()
        reg.add_note(n1, "Piano")
        reg.add_note(n2, "Piano")
        reg.add_note(n3, "Bass")
        assert len(reg.by_track("Piano")) == 2
        assert len(reg.by_track("Bass")) == 1
        assert len(reg.by_pitch(60)) == 2  # n1 (C4) + n3 (C4)
        assert len(reg.by_pitch(62)) == 1  # n2 (D4)


class TestRegistryRemoveNote:
    def test_remove_note(self):
        s, piano, bass, n1, n2, n3 = _song_with_notes()
        reg = Registry()
        reg.rebuild(s)
        assert len(reg.by_track("Piano")) == 2

        reg.remove_note(n1, "Piano")
        assert len(reg.by_track("Piano")) == 1
        assert reg.by_track("Piano")[0].id == n2.id
        assert len(reg.by_pitch(60)) == 1  # only n3 remains

    def test_remove_all_from_track(self):
        s, piano, bass, n1, n2, n3 = _song_with_notes()
        reg = Registry()
        reg.rebuild(s)
        reg.remove_note(n1, "Piano")
        reg.remove_note(n2, "Piano")
        assert len(reg.by_track("Piano")) == 0


class TestRegistryUpdateNote:
    def test_update_pitch(self):
        s, piano, bass, n1, n2, n3 = _song_with_notes()
        reg = Registry()
        reg.rebuild(s)
        assert len(reg.by_pitch(60)) == 2  # n1 + n3

        old_pitch = n1.pitch
        new_pitch = Pitch(name="E", accidental="", octave=4, midi_number=64)
        n1.pitch = new_pitch
        reg.update_note(n1, "Piano", "pitch", old_pitch)

        assert len(reg.by_pitch(60)) == 1  # only n3
        assert len(reg.by_pitch(64)) == 1  # n1 moved here

    def test_update_channel(self):
        s, piano, bass, n1, n2, n3 = _song_with_notes()
        reg = Registry()
        reg.rebuild(s)
        old_ch = n1.channel
        n1.channel = 5
        reg.update_note(n1, "Piano", "channel", old_ch)
        assert len(reg.by_channel(5)) == 1

    def test_update_velocity_is_noop(self):
        """Velocity changes don't affect indexes."""
        s, piano, bass, n1, n2, n3 = _song_with_notes()
        reg = Registry()
        reg.rebuild(s)
        old_vel = n1.velocity
        n1.velocity = 127
        reg.update_note(n1, "Piano", "velocity", old_vel)
        # Should not error; indexes unchanged
        assert len(reg.by_track("Piano")) == 2


class TestRegistryIncrementalConsistency:
    def test_incremental_matches_rebuild(self):
        """Build registry incrementally and verify it matches a full rebuild."""
        s, piano, bass, n1, n2, n3 = _song_with_notes()

        # Incremental build
        inc = Registry()
        inc.add_note(n1, "Piano")
        inc.add_note(n2, "Piano")
        inc.add_note(n3, "Bass")

        # Full rebuild
        full = Registry()
        full.rebuild(s)

        # Compare
        assert set(n.id for n in inc.by_track("Piano")) == set(n.id for n in full.by_track("Piano"))
        assert set(n.id for n in inc.by_track("Bass")) == set(n.id for n in full.by_track("Bass"))
        assert set(n.id for n in inc.by_pitch(60)) == set(n.id for n in full.by_pitch(60))
        assert set(n.id for n in inc.by_pitch(62)) == set(n.id for n in full.by_pitch(62))
