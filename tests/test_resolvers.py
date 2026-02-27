"""Tests for the centralized parameter resolution module."""

from __future__ import annotations

import pytest

from fcp_midi.model.event_log import EventLog, NoteAdded
from fcp_midi.model.registry import Registry
from fcp_midi.model.song import Pitch, Song
from fcp_midi.server.resolvers import (
    OpContext,
    display_channel,
    max_tick,
    pitch_from_midi,
    resolve_channel,
    resolve_duration,
    resolve_position,
    resolve_track,
    resolve_velocity,
    suggest_track_name,
)


def _song_with_piano() -> tuple[Song, str]:
    s = Song.create(title="Test", tempo=120.0, time_sig=(4, 4))
    t = s.add_track("Piano")
    return s, t.id


class TestResolveChannel:
    def test_absent(self) -> None:
        assert resolve_channel({}) is None

    def test_present(self) -> None:
        assert resolve_channel({"ch": "3"}) == 2  # 1-indexed -> 0-indexed

    def test_channel_1(self) -> None:
        assert resolve_channel({"ch": "1"}) == 0


class TestDisplayChannel:
    def test_zero(self) -> None:
        assert display_channel(0) == 1

    def test_nine(self) -> None:
        assert display_channel(9) == 10


class TestResolvePosition:
    def test_default(self) -> None:
        s, _ = _song_with_piano()
        result = resolve_position({}, s, 0)
        assert result == 0  # 1.1 = tick 0

    def test_explicit(self) -> None:
        s, _ = _song_with_piano()
        result = resolve_position({"at": "2.1"}, s, 0)
        assert result == 1920  # measure 2 in 4/4 at ppqn 480

    def test_invalid(self) -> None:
        s, _ = _song_with_piano()
        result = resolve_position({"at": "invalid"}, s, 0)
        assert isinstance(result, str)
        assert "!" in result


class TestResolveDuration:
    def test_default(self) -> None:
        s, _ = _song_with_piano()
        result = resolve_duration({}, s)
        assert result == 480  # quarter at ppqn 480

    def test_half(self) -> None:
        s, _ = _song_with_piano()
        result = resolve_duration({"dur": "half"}, s)
        assert result == 960


class TestResolveVelocity:
    def test_default(self) -> None:
        assert resolve_velocity({}) == 80

    def test_numeric(self) -> None:
        assert resolve_velocity({"vel": "100"}) == 100

    def test_symbolic(self) -> None:
        assert resolve_velocity({"vel": "ff"}) == 112


class TestResolveTrack:
    def test_found(self) -> None:
        s, _ = _song_with_piano()
        result = resolve_track(s, "Piano")
        assert not isinstance(result, str)
        assert result.name == "Piano"

    def test_missing(self) -> None:
        s, _ = _song_with_piano()
        result = resolve_track(s, "Guitar")
        assert isinstance(result, str)
        assert "!" in result

    def test_none_name(self) -> None:
        s, _ = _song_with_piano()
        result = resolve_track(s, None)
        assert isinstance(result, str)
        assert "!" in result


class TestSuggestTrackName:
    def test_close_match(self) -> None:
        s, _ = _song_with_piano()
        result = suggest_track_name(s, "Paino")
        assert result is not None
        assert "Piano" in result

    def test_no_match(self) -> None:
        s, _ = _song_with_piano()
        result = suggest_track_name(s, "XYZ")
        assert "Piano" in result  # lists available


class TestPitchFromMidi:
    def test_c4(self) -> None:
        p = pitch_from_midi(60)
        assert p.name == "C"
        assert p.octave == 4
        assert p.midi_number == 60

    def test_black_key(self) -> None:
        p = pitch_from_midi(61)
        assert p.accidental == "#"


class TestMaxTick:
    def test_empty(self) -> None:
        s = Song.create()
        assert max_tick(s) == 0

    def test_with_notes(self) -> None:
        s, tid = _song_with_piano()
        c4 = Pitch(name="C", accidental="", octave=4, midi_number=60)
        s.add_note(tid, c4, absolute_tick=100, duration_ticks=200)
        assert max_tick(s) == 300
