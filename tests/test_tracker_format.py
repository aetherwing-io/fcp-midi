"""Tests for tracker_format.py — core format/parse/pair logic."""

from __future__ import annotations

import pytest

from fcp_midi.model.midi_model import MidiModel, NoteRef, pair_notes
from fcp_midi.server.tracker_format import (
    auto_detect_resolution,
    format_tracker,
    format_tracker_multi,
    pair_tracker_events,
    parse_event_token,
    parse_step_line,
    _drum_pitch_name,
    _ticks_per_step,
    MAX_COMBINED_TRACKS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_note_ref(pitch: int, abs_tick: int, dur: int, vel: int = 100) -> NoteRef:
    return NoteRef(
        track_name="Piano",
        note_on_idx=0,
        note_off_idx=1,
        abs_tick=abs_tick,
        duration_ticks=dur,
        pitch=pitch,
        velocity=vel,
        channel=0,
    )


def _make_note(
    track_name: str,
    pitch: int,
    abs_tick: int,
    dur: int,
    vel: int = 100,
    channel: int = 0,
) -> NoteRef:
    """Helper that allows specifying track name and channel."""
    return NoteRef(
        track_name=track_name,
        note_on_idx=0,
        note_off_idx=1,
        abs_tick=abs_tick,
        duration_ticks=dur,
        pitch=pitch,
        velocity=vel,
        channel=channel,
    )


# ---------------------------------------------------------------------------
# format_tracker
# ---------------------------------------------------------------------------

class TestFormatTracker:
    def test_basic(self):
        ppqn = 480
        notes = [
            _make_note_ref(60, 0, ppqn, 100),       # C4 at step 1, dur=quarter
            _make_note_ref(64, ppqn, ppqn, 90),      # E4 at step 2 (if quarter res)
        ]
        result = format_tracker(notes, "Piano", [], ppqn, 0, ppqn * 4)
        assert "[Resolution:" in result
        assert "[Track: Piano" in result
        # Duration-in-token format: each note appears once with duration
        assert "[C4_v100_1]" in result
        assert "[E4_v90_1]" in result
        # No ON/OFF events
        assert "_ON]" not in result
        assert "_OFF]" not in result

    def test_simultaneous_chord(self):
        ppqn = 480
        notes = [
            _make_note_ref(60, 0, ppqn, 100),  # C4
            _make_note_ref(64, 0, ppqn, 90),   # E4
            _make_note_ref(67, 0, ppqn, 90),   # G4
        ]
        result = format_tracker(notes, "Piano", [], ppqn, 0, ppqn * 4)
        # All three should appear on the same step line
        lines = result.strip().split("\n")
        step_lines = [l for l in lines if l.startswith("Step")]
        # All three on one line with duration
        on_line = step_lines[0]
        assert "[C4_v100_1]" in on_line
        assert "[E4_v90_1]" in on_line
        assert "[G4_v90_1]" in on_line

    def test_no_notes_in_range(self):
        ppqn = 480
        notes = [_make_note_ref(60, 0, ppqn, 100)]
        result = format_tracker(notes, "Piano", [], ppqn, ppqn * 10, ppqn * 20)
        assert "No notes" in result

    def test_explicit_resolution(self):
        ppqn = 480
        notes = [_make_note_ref(60, 0, ppqn, 100)]
        result = format_tracker(notes, "Piano", [], ppqn, 0, ppqn * 4, resolution="8th")
        assert "[Resolution: 8th]" in result
        # Simplified label — no "notes" suffix
        assert "8th notes" not in result

    def test_duration_in_steps(self):
        """Notes spanning multiple steps show correct duration."""
        ppqn = 480
        tps = ppqn // 4  # 16th note = 120 ticks
        notes = [
            _make_note_ref(60, 0, tps * 4, 100),  # C4 lasting 4 steps
        ]
        result = format_tracker(notes, "Piano", [], ppqn, 0, ppqn * 4, resolution="16th")
        assert "[C4_v100_4]" in result

    def test_instrument_in_header(self):
        """When instrument is provided, it appears in parentheses after track name."""
        ppqn = 480
        notes = [_make_note_ref(60, 0, ppqn, 100)]
        result = format_tracker(
            notes, "Piano", [], ppqn, 0, ppqn * 4,
            instrument="acoustic-grand-piano",
        )
        assert "[Track: Piano (acoustic-grand-piano) |" in result

    def test_instrument_none_backward_compat(self):
        """When instrument is None, header shows track name only (no parens)."""
        ppqn = 480
        notes = [_make_note_ref(60, 0, ppqn, 100)]
        result = format_tracker(notes, "Piano", [], ppqn, 0, ppqn * 4, instrument=None)
        assert "[Track: Piano |" in result
        assert "(" not in result.split("\n")[1]  # no parens on the Track line

    def test_instrument_drums(self):
        """Drums instrument label appears correctly."""
        ppqn = 480
        notes = [_make_note_ref(36, 0, ppqn, 100)]
        result = format_tracker(
            notes, "Drums", [], ppqn, 0, ppqn * 4,
            instrument="drums",
        )
        assert "[Track: Drums (drums) |" in result

    def test_simplified_resolution_labels(self):
        """Resolution labels should be short — no 'notes' suffix."""
        ppqn = 480
        notes = [_make_note_ref(60, 0, ppqn, 100)]
        for res, expected in [
            ("quarter", "[Resolution: quarter]"),
            ("8th", "[Resolution: 8th]"),
            ("16th", "[Resolution: 16th]"),
            ("32nd", "[Resolution: 32nd]"),
        ]:
            result = format_tracker(
                notes, "Piano", [], ppqn, 0, ppqn * 4, resolution=res,
            )
            assert expected in result, f"Expected {expected!r} for resolution={res!r}"
            assert "notes]" not in result

    def test_notes_beyond_range_show_full_duration(self):
        """Notes extending past the end_tick still show their full duration."""
        ppqn = 480
        tps = ppqn // 4  # 16th = 120 ticks
        notes = [
            _make_note_ref(60, 0, tps * 8, 100),  # C4 lasting 8 steps, well past end
        ]
        result = format_tracker(notes, "Piano", [], ppqn, 0, tps * 4, resolution="16th")
        assert "[C4_v100_8]" in result


# ---------------------------------------------------------------------------
# auto_detect_resolution
# ---------------------------------------------------------------------------

class TestAutoDetectResolution:
    def test_quarter_boundaries(self):
        ppqn = 480
        notes = [
            _make_note_ref(60, 0, ppqn, 100),           # starts on quarter
            _make_note_ref(64, ppqn, ppqn, 90),         # starts on quarter
        ]
        assert auto_detect_resolution(notes, ppqn) == "quarter"

    def test_16th_boundaries(self):
        ppqn = 480
        step = ppqn // 4  # 120 ticks = 16th
        notes = [
            _make_note_ref(60, 0, step, 100),
            _make_note_ref(64, step, step, 90),
            _make_note_ref(67, step * 3, step, 80),
        ]
        res = auto_detect_resolution(notes, ppqn)
        assert res == "16th"

    def test_8th_boundaries(self):
        ppqn = 480
        step = ppqn // 2  # 240 ticks = 8th
        notes = [
            _make_note_ref(60, 0, step, 100),
            _make_note_ref(64, step, step, 90),
        ]
        res = auto_detect_resolution(notes, ppqn)
        assert res == "8th"

    def test_default_on_empty(self):
        assert auto_detect_resolution([], 480) == "16th"

    def test_unaligned_defaults_16th(self):
        ppqn = 480
        # Notes at weird offsets that don't align to any standard grid
        notes = [
            _make_note_ref(60, 7, 33, 100),
        ]
        res = auto_detect_resolution(notes, ppqn)
        assert res == "16th"


# ---------------------------------------------------------------------------
# parse_event_token
# ---------------------------------------------------------------------------

class TestParseEventToken:
    def test_basic(self):
        midi, vel, dur = parse_event_token("[C4_v100_4]")
        assert midi == 60
        assert vel == 100
        assert dur == 4

    def test_single_step(self):
        midi, vel, dur = parse_event_token("[D#5_v80_1]")
        assert midi == 75
        assert vel == 80
        assert dur == 1

    def test_with_whitespace(self):
        midi, vel, dur = parse_event_token("  [E4_v80_2]  ")
        assert midi == 64
        assert vel == 80
        assert dur == 2

    def test_invalid(self):
        with pytest.raises(ValueError):
            parse_event_token("[invalid]")

    def test_flat(self):
        midi, vel, dur = parse_event_token("[Bb3_v50_3]")
        assert midi == 58
        assert vel == 50
        assert dur == 3

    def test_old_on_off_format_rejected(self):
        """The old ON/OFF format should no longer parse."""
        with pytest.raises(ValueError):
            parse_event_token("[C4_v100_ON]")
        with pytest.raises(ValueError):
            parse_event_token("[C4_v0_OFF]")


# ---------------------------------------------------------------------------
# parse_step_line
# ---------------------------------------------------------------------------

class TestParseStepLine:
    def test_single_event(self):
        step, events = parse_step_line("Step 03: [C4_v100_4]")
        assert step == 3
        assert len(events) == 1
        assert events[0] == (60, 100, 4)

    def test_multiple_events(self):
        step, events = parse_step_line("Step 01: [C4_v100_4], [E4_v90_4], [G4_v90_4]")
        assert step == 1
        assert len(events) == 3
        assert events[0][0] == 60  # C4
        assert events[1][0] == 64  # E4
        assert events[2][0] == 67  # G4
        # All have duration 4
        for _, _, dur in events:
            assert dur == 4

    def test_invalid_line(self):
        with pytest.raises(ValueError):
            parse_step_line("not a step line")


# ---------------------------------------------------------------------------
# pair_tracker_events
# ---------------------------------------------------------------------------

class TestPairTrackerEvents:
    def test_basic_duration(self):
        steps = [
            (1, [(60, 100, 4)]),    # C4 at step 1, duration 4 steps
        ]
        result = pair_tracker_events(steps, 0, 120)  # 16th at ppqn=480
        assert len(result) == 1
        pitch, vel, tick, dur = result[0]
        assert pitch == 60
        assert vel == 100
        assert tick == 0
        assert dur == 4 * 120  # 4 steps * 120 ticks/step

    def test_single_step_duration(self):
        steps = [
            (1, [(60, 100, 1)]),    # C4 at step 1, duration 1 step
        ]
        result = pair_tracker_events(steps, 0, 120)
        assert len(result) == 1
        pitch, vel, tick, dur = result[0]
        assert dur == 120

    def test_multiple_notes_same_step(self):
        steps = [
            (1, [(60, 100, 2), (64, 90, 2)]),
        ]
        result = pair_tracker_events(steps, 0, 120)
        assert len(result) == 2
        # Both should have duration = 2 steps = 240 ticks
        for pitch, vel, tick, dur in result:
            assert dur == 240

    def test_notes_at_different_steps(self):
        steps = [
            (1, [(60, 100, 4)]),    # C4 at step 1
            (3, [(64, 90, 2)]),     # E4 at step 3
        ]
        result = pair_tracker_events(steps, 0, 120)
        assert len(result) == 2
        # C4 at tick 0, E4 at tick 240
        assert result[0] == (60, 100, 0, 480)
        assert result[1] == (64, 90, 240, 240)

    def test_start_tick_offset(self):
        steps = [
            (1, [(60, 100, 2)]),
        ]
        result = pair_tracker_events(steps, 480, 120)  # start_tick = 480
        assert len(result) == 1
        pitch, vel, tick, dur = result[0]
        assert tick == 480  # start_tick + (1-1)*tps


# ---------------------------------------------------------------------------
# Round-trip test
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_format_parse_format(self):
        """Format notes -> parse output -> pair -> verify matches original."""
        ppqn = 480
        tps = ppqn // 4  # 16th = 120 ticks
        notes = [
            _make_note_ref(60, 0, tps * 4, 100),      # C4, 4 steps long
            _make_note_ref(64, 0, tps * 4, 90),       # E4, 4 steps long
            _make_note_ref(67, tps * 2, tps * 2, 80), # G4, starts at step 3, 2 steps
        ]
        output = format_tracker(notes, "Piano", [], ppqn, 0, ppqn * 4, resolution="16th")

        # Parse the step lines from the output
        lines = output.strip().split("\n")
        step_lines = [l for l in lines if l.startswith("Step")]

        parsed_steps = []
        for line in step_lines:
            parsed_steps.append(parse_step_line(line))

        # Convert to notes
        paired = pair_tracker_events(parsed_steps, 0, tps)

        # We should get 3 notes back
        assert len(paired) == 3

        # Verify pitches and velocities match
        original_set = {(n.pitch, n.velocity) for n in notes}
        paired_set = {(p, v) for p, v, _, _ in paired}
        assert original_set == paired_set

        # Verify ticks and durations match
        for p, v, tick, dur in paired:
            matching = [n for n in notes if n.pitch == p and n.velocity == v]
            assert len(matching) == 1
            assert tick == matching[0].abs_tick
            assert dur == matching[0].duration_ticks


# ---------------------------------------------------------------------------
# format_tracker_multi
# ---------------------------------------------------------------------------

class TestFormatTrackerMulti:
    def test_two_tracks_interleaved(self):
        """Two tracks with events at different steps appear interleaved."""
        ppqn = 480
        tps = ppqn // 4  # 16th = 120 ticks

        piano_notes = [
            _make_note(
                "Piano", 60, 0, tps * 4, 100, channel=0,
            ),  # C4 at step 1
            _make_note(
                "Piano", 64, tps * 2, tps * 2, 90, channel=0,
            ),  # E4 at step 3
        ]
        bass_notes = [
            _make_note(
                "Bass", 36, 0, tps * 8, 100, channel=1,
            ),  # C2 at step 1
        ]
        track_data = [
            ("Piano", piano_notes, False),
            ("Bass", bass_notes, False),
        ]
        result = format_tracker_multi(
            track_data, [], ppqn, 0, ppqn * 4, resolution="16th",
        )
        assert "[Resolution: 16th]" in result
        assert "[Tracks: Piano, Bass |" in result
        # Step 01 has both Piano and Bass tokens
        lines = result.strip().split("\n")
        step1 = [l for l in lines if l.startswith("Step 01")]
        assert len(step1) == 1
        assert "Piano[" in step1[0]
        assert "Bass[" in step1[0]
        # Step 03 has only Piano
        step3 = [l for l in lines if l.startswith("Step 03")]
        assert len(step3) == 1
        assert "Piano[" in step3[0]
        assert "Bass[" not in step3[0]

    def test_three_tracks(self):
        """Three tracks appear in the header and output."""
        ppqn = 480
        tps = ppqn // 4
        track_data = [
            ("Piano", [_make_note("Piano", 60, 0, tps, 100)], False),
            ("Bass", [_make_note("Bass", 36, 0, tps, 100, channel=1)], False),
            ("Drums", [_make_note("Drums", 36, 0, tps, 120, channel=9)], True),
        ]
        result = format_tracker_multi(
            track_data, [], ppqn, 0, ppqn * 4, resolution="16th",
        )
        assert "[Tracks: Piano, Bass, Drums |" in result
        # All three tracks on step 01
        step1_line = [l for l in result.split("\n") if l.startswith("Step 01")][0]
        assert "Piano[" in step1_line
        assert "Bass[" in step1_line
        assert "Drums[" in step1_line

    def test_drum_name_substitution(self):
        """Drum tracks show drum names instead of pitch names."""
        ppqn = 480
        tps = ppqn // 4
        drum_notes = [
            _make_note("Drums", 36, 0, tps, 120, channel=9),       # kick
            _make_note("Drums", 38, tps, tps, 100, channel=9),     # snare
            _make_note("Drums", 42, tps * 2, tps, 80, channel=9),  # hihat
        ]
        track_data = [("Drums", drum_notes, True)]
        result = format_tracker_multi(
            track_data, [], ppqn, 0, ppqn * 4, resolution="16th",
        )
        assert "kick_v120_1" in result
        assert "snare_v100_1" in result
        assert "hihat_v80_1" in result
        # Should NOT contain pitch names like C2, D2, etc.
        assert "C2_" not in result
        assert "D2_" not in result

    def test_drum_aliases_preferred(self):
        """Common drums use short aliases, others use full GM names."""
        # Short aliases
        assert _drum_pitch_name(36) == "kick"
        assert _drum_pitch_name(38) == "snare"
        assert _drum_pitch_name(42) == "hihat"
        assert _drum_pitch_name(49) == "crash"
        assert _drum_pitch_name(51) == "ride"
        # Full GM name for non-aliased drum
        assert _drum_pitch_name(56) == "cowbell"
        assert _drum_pitch_name(54) == "tambourine"

    def test_drum_pitch_fallback(self):
        """For MIDI numbers outside GM drum range, falls back to pitch name."""
        # MIDI 30 is not a GM drum (35-81 range)
        name = _drum_pitch_name(30)
        assert name == "F#1"  # standard pitch name

    def test_cap_at_4_tracks(self):
        """Only the first 4 tracks are shown; extras get an omitted note."""
        ppqn = 480
        tps = ppqn // 4
        track_data = []
        for i in range(6):
            name = f"Track{i}"
            notes = [_make_note(name, 60 + i, 0, tps, 100, channel=i)]
            track_data.append((name, notes, False))

        result = format_tracker_multi(
            track_data, [], ppqn, 0, ppqn * 4, resolution="16th",
        )
        # Header shows only first 4
        assert "[Tracks: Track0, Track1, Track2, Track3 |" in result
        assert "Track4" not in result.split("(+")[0]  # not in main output
        assert "Track5" not in result.split("(+")[0]
        # Omission note
        assert "(+2 more tracks omitted)" in result

    def test_empty_tracks_no_notes_in_range(self):
        """Tracks with no notes in the requested range are still listed but
        produce no step entries for that track."""
        ppqn = 480
        tps = ppqn // 4
        piano_notes = [_make_note("Piano", 60, 0, tps, 100)]
        # Bass has a note far outside the range
        bass_notes = [_make_note("Bass", 36, ppqn * 100, tps, 100, channel=1)]
        track_data = [
            ("Piano", piano_notes, False),
            ("Bass", bass_notes, False),
        ]
        result = format_tracker_multi(
            track_data, [], ppqn, 0, ppqn * 4, resolution="16th",
        )
        # Piano should be present
        assert "Piano[" in result
        # Bass should NOT appear in any step line (no notes in range)
        step_lines = [l for l in result.split("\n") if l.startswith("Step")]
        for line in step_lines:
            assert "Bass[" not in line

    def test_all_tracks_empty(self):
        """When no tracks have notes in range, a 'No notes' message appears."""
        ppqn = 480
        tps = ppqn // 4
        piano_notes = [_make_note("Piano", 60, ppqn * 100, tps, 100)]
        track_data = [("Piano", piano_notes, False)]
        result = format_tracker_multi(
            track_data, [], ppqn, 0, ppqn * 4, resolution="16th",
        )
        assert "No notes" in result

    def test_uses_plural_tracks_header(self):
        """Multi-track header uses [Tracks: ...] (plural), not [Track: ...]."""
        ppqn = 480
        tps = ppqn // 4
        track_data = [
            ("Piano", [_make_note("Piano", 60, 0, tps, 100)], False),
            ("Bass", [_make_note("Bass", 36, 0, tps, 100, channel=1)], False),
        ]
        result = format_tracker_multi(
            track_data, [], ppqn, 0, ppqn * 4, resolution="16th",
        )
        assert "[Tracks:" in result
        assert "[Track:" not in result

    def test_multi_track_token_format_no_outer_brackets(self):
        """Multi-track tokens use TrackName[token, token] — no [ ] around
        individual tokens (unlike single-track format)."""
        ppqn = 480
        tps = ppqn // 4
        piano_notes = [
            _make_note("Piano", 60, 0, tps * 2, 100),
            _make_note("Piano", 64, 0, tps * 2, 90),
        ]
        track_data = [("Piano", piano_notes, False)]
        result = format_tracker_multi(
            track_data, [], ppqn, 0, ppqn * 4, resolution="16th",
        )
        step_lines = [l for l in result.split("\n") if l.startswith("Step")]
        assert len(step_lines) >= 1
        # The format should be Piano[C4_v100_2, E4_v90_2]
        # NOT Piano[[C4_v100_2], [E4_v90_2]]
        step1 = step_lines[0]
        assert "Piano[C4_v100_2, E4_v90_2]" in step1

    def test_auto_resolution_across_all_tracks(self):
        """Resolution auto-detection uses notes from ALL tracks combined."""
        ppqn = 480
        # Piano notes align to quarter boundaries
        piano_notes = [_make_note("Piano", 60, 0, ppqn, 100)]
        # Bass note at 16th boundary (ppqn // 4 = 120 ticks)
        bass_notes = [_make_note("Bass", 36, ppqn // 4, ppqn // 4, 100, channel=1)]
        track_data = [
            ("Piano", piano_notes, False),
            ("Bass", bass_notes, False),
        ]
        result = format_tracker_multi(
            track_data, [], ppqn, 0, ppqn * 4,
        )
        # Should detect 16th because bass is on 16th boundary
        assert "[Resolution: 16th]" in result
