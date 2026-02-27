"""Tests for server layer: tool delegation, formatter, and reference card."""

from __future__ import annotations

from fcp_midi.model.song import Pitch, Song
from fcp_midi.server.formatter import (
    format_describe,
    format_events,
    format_map,
    format_result,
    format_stats,
    format_track_list,
)
from fcp_midi.server.reference_card import REFERENCE_CARD


def _c4() -> Pitch:
    return Pitch(name="C", accidental="", octave=4, midi_number=60)


def _song_with_notes() -> Song:
    s = Song.create(title="Test", tempo=120.0, time_sig=(4, 4), key="C-major")
    t = s.add_track("Piano", instrument="acoustic-grand-piano", program=0)
    s.add_note(t.id, _c4(), absolute_tick=0, duration_ticks=480, velocity=80)
    return s


# -----------------------------------------------------------------------
# Formatter tests
# -----------------------------------------------------------------------

class TestFormatResult:
    def test_success(self) -> None:
        r = format_result(True, "done")
        assert r.startswith("+")
        assert "done" in r

    def test_failure(self) -> None:
        r = format_result(False, "oops")
        assert r.startswith("!")
        assert "oops" in r

    def test_failure_with_hint(self) -> None:
        r = format_result(False, "oops", "try this")
        assert "try" in r


class TestFormatTrackList:
    def test_empty_song(self) -> None:
        s = Song.create()
        result = format_track_list(s)
        assert "No tracks" in result or result == ""

    def test_with_tracks(self) -> None:
        s = _song_with_notes()
        result = format_track_list(s)
        assert "Piano" in result
        assert "ch:" in result


class TestFormatStats:
    def test_with_notes(self) -> None:
        s = _song_with_notes()
        result = format_stats(s)
        assert "Notes: 1" in result
        assert "Tracks: 1" in result


class TestFormatMap:
    def test_with_song(self) -> None:
        s = _song_with_notes()
        result = format_map(s)
        assert "Test" in result
        assert "Piano" in result


class TestFormatEvents:
    def test_events(self) -> None:
        s = _song_with_notes()
        t = s.get_track_by_name("Piano")
        result = format_events(t, s)
        assert "C" in result


class TestFormatDescribe:
    def test_describe(self) -> None:
        s = _song_with_notes()
        t = s.get_track_by_name("Piano")
        result = format_describe(t, s)
        assert "Piano" in result
        assert "Notes: 1" in result


# -----------------------------------------------------------------------
# Reference card
# -----------------------------------------------------------------------

class TestReferenceCard:
    def test_non_empty(self) -> None:
        assert len(REFERENCE_CARD) > 100

    def test_contains_verbs(self) -> None:
        for verb in ("note", "chord", "track", "cc", "bend", "tempo",
                     "time-sig", "key-sig", "marker", "remove", "move",
                     "copy", "transpose", "velocity", "quantize", "modify",
                     "repeat", "crescendo", "decrescendo", "mute", "solo",
                     "program", "title"):
            assert verb in REFERENCE_CARD, f"Verb {verb!r} not found in reference card"

    def test_dispatch_verbs_covered_by_registry(self) -> None:
        """Every verb in the dispatch table must appear in the verb registry."""
        from fcp_midi.server.verb_registry import VERB_MAP
        dispatch_verbs = {
            "note", "chord", "track", "cc", "bend", "tempo",
            "time-sig", "key-sig", "marker", "title",
            "remove", "move", "copy", "transpose", "velocity",
            "quantize", "mute", "solo", "program", "modify",
            "repeat", "crescendo", "decrescendo",
        }
        for verb in dispatch_verbs:
            assert verb in VERB_MAP, f"Verb {verb!r} missing from verb registry"

    def test_contains_not_selector(self) -> None:
        assert "@not:" in REFERENCE_CARD


# -----------------------------------------------------------------------
# Tool delegation (IntentLayer facade)
# -----------------------------------------------------------------------

class TestIntentFacade:
    def test_ops_delegate_to_handlers(self) -> None:
        from fcp_midi.server.intent import IntentLayer
        il = IntentLayer()
        il.execute_session('new "Test" tempo:120')
        results = il.execute_ops(["track add Piano instrument:acoustic-grand-piano"])
        assert any("+" in r for r in results)

    def test_query_delegates(self) -> None:
        from fcp_midi.server.intent import IntentLayer
        il = IntentLayer()
        il.execute_session('new "Test" tempo:120')
        il.execute_ops(["track add Piano instrument:acoustic-grand-piano"])
        result = il.execute_query("tracks")
        assert "Piano" in result

    def test_session_delegates(self) -> None:
        from fcp_midi.server.intent import IntentLayer
        il = IntentLayer()
        result = il.execute_session('new "Delegation Test" tempo:140')
        assert "+" in result
        assert il.song is not None
        assert il.song.title == "Delegation Test"
