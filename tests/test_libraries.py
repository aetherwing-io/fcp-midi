"""Tests for reference data libraries."""

from __future__ import annotations

import pytest

from fcp_midi.lib.gm_instruments import (
    GM_INSTRUMENTS,
    INSTRUMENT_FAMILIES,
    instrument_to_program,
    program_to_instrument,
)
from fcp_midi.lib.gm_drums import (
    GM_DRUMS,
    drum_to_note,
    note_to_drum,
)
from fcp_midi.lib.chord_library import (
    CHORD_QUALITIES,
    get_intervals,
)
from fcp_midi.lib.cc_names import (
    CC_NAMES,
    cc_to_number,
    number_to_cc,
    parse_cc_value,
)
from fcp_midi.lib.velocity_names import (
    VELOCITY_NAMES,
    parse_velocity,
)


# ---------------------------------------------------------------------------
# GM Instruments
# ---------------------------------------------------------------------------


class TestGMInstruments:
    """Tests for GM instrument lookups."""

    def test_all_128_instruments_present(self):
        """All 128 GM programs (0-127) must be defined."""
        assert len(GM_INSTRUMENTS) == 128
        for i in range(128):
            assert i in GM_INSTRUMENTS, f"Program {i} missing"

    def test_forward_lookup_all(self):
        """Every instrument name maps back to its program number."""
        for program, name in GM_INSTRUMENTS.items():
            assert instrument_to_program(name) == program

    def test_reverse_lookup_all(self):
        """Every program number maps to its instrument name."""
        for program, name in GM_INSTRUMENTS.items():
            assert program_to_instrument(program) == name

    def test_reverse_lookup_out_of_range(self):
        """Out-of-range program numbers return None."""
        assert program_to_instrument(-1) is None
        assert program_to_instrument(128) is None
        assert program_to_instrument(999) is None

    def test_fuzzy_piano(self):
        """Partial match 'piano' should return acoustic-grand-piano (program 0)."""
        assert instrument_to_program("piano") == 0

    def test_fuzzy_strings(self):
        """Alias 'strings' should return string-ensemble-1 (program 48)."""
        assert instrument_to_program("strings") == 48

    def test_case_insensitive(self):
        """Lookups should be case-insensitive."""
        assert instrument_to_program("Acoustic-Grand-Piano") == 0
        assert instrument_to_program("VIOLIN") == 40
        assert instrument_to_program("Flute") == 73

    def test_spaces_instead_of_hyphens(self):
        """Spaces should be treated as hyphens."""
        assert instrument_to_program("acoustic grand piano") == 0
        assert instrument_to_program("electric piano 1") == 4

    def test_unknown_instrument(self):
        """Unknown names return None."""
        assert instrument_to_program("theremin") is None
        assert instrument_to_program("zzz-not-real") is None

    def test_instrument_families_coverage(self):
        """All 16 families exist and cover all 128 instruments."""
        assert len(INSTRUMENT_FAMILIES) == 16
        all_names = []
        for names in INSTRUMENT_FAMILIES.values():
            assert len(names) == 8
            all_names.extend(names)
        assert len(all_names) == 128

    def test_specific_instruments(self):
        """Spot-check specific well-known program numbers."""
        assert GM_INSTRUMENTS[0] == "acoustic-grand-piano"
        assert GM_INSTRUMENTS[38] == "synth-bass-1"
        assert GM_INSTRUMENTS[56] == "trumpet"
        assert GM_INSTRUMENTS[73] == "flute"
        assert GM_INSTRUMENTS[127] == "gunshot"


# ---------------------------------------------------------------------------
# GM Drums
# ---------------------------------------------------------------------------


class TestGMDrums:
    """Tests for GM drum map lookups."""

    def test_all_drum_notes_present(self):
        """Notes 35-81 must all be defined."""
        assert len(GM_DRUMS) == 47  # 35 through 81 inclusive
        for note in range(35, 82):
            assert note in GM_DRUMS, f"Note {note} missing"

    def test_forward_lookup_all(self):
        """Every drum name maps back to its note number."""
        for note, name in GM_DRUMS.items():
            assert drum_to_note(name) == note

    def test_reverse_lookup_all(self):
        """Every note number maps to its drum name."""
        for note, name in GM_DRUMS.items():
            assert note_to_drum(note) == name

    def test_reverse_lookup_out_of_range(self):
        """Out-of-range note numbers return None."""
        assert note_to_drum(0) is None
        assert note_to_drum(34) is None
        assert note_to_drum(82) is None

    def test_alias_kick(self):
        assert drum_to_note("kick") == 36

    def test_alias_snare(self):
        assert drum_to_note("snare") == 38

    def test_alias_hihat(self):
        assert drum_to_note("hihat") == 42

    def test_alias_hi_hat(self):
        assert drum_to_note("hi-hat") == 42

    def test_alias_ride(self):
        assert drum_to_note("ride") == 51

    def test_alias_crash(self):
        assert drum_to_note("crash") == 49

    def test_alias_tom(self):
        assert drum_to_note("tom") == 50

    def test_case_insensitive(self):
        assert drum_to_note("Acoustic-Snare") == 38
        assert drum_to_note("COWBELL") == 56

    def test_spaces_instead_of_hyphens(self):
        assert drum_to_note("acoustic bass drum") == 35
        assert drum_to_note("closed hi hat") == 42

    def test_unknown_drum(self):
        assert drum_to_note("kazoo") is None

    def test_specific_drums(self):
        """Spot-check specific drum assignments."""
        assert GM_DRUMS[36] == "bass-drum-1"
        assert GM_DRUMS[38] == "acoustic-snare"
        assert GM_DRUMS[42] == "closed-hi-hat"
        assert GM_DRUMS[49] == "crash-cymbal-1"
        assert GM_DRUMS[56] == "cowbell"


# ---------------------------------------------------------------------------
# Chord Library
# ---------------------------------------------------------------------------


class TestChordLibrary:
    """Tests for chord quality definitions."""

    def test_major_chord(self):
        assert get_intervals("maj") == [0, 4, 7]

    def test_default_is_major(self):
        assert get_intervals("") == [0, 4, 7]

    def test_minor_chord(self):
        assert get_intervals("min") == [0, 3, 7]
        assert get_intervals("m") == [0, 3, 7]

    def test_dominant_seventh(self):
        assert get_intervals("7") == [0, 4, 7, 10]

    def test_major_seventh(self):
        assert get_intervals("maj7") == [0, 4, 7, 11]

    def test_minor_seventh(self):
        assert get_intervals("min7") == [0, 3, 7, 10]
        assert get_intervals("m7") == [0, 3, 7, 10]

    def test_diminished(self):
        assert get_intervals("dim") == [0, 3, 6]

    def test_augmented(self):
        assert get_intervals("aug") == [0, 4, 8]

    def test_suspended(self):
        assert get_intervals("sus2") == [0, 2, 7]
        assert get_intervals("sus4") == [0, 5, 7]

    def test_add9(self):
        assert get_intervals("add9") == [0, 4, 7, 14]

    def test_half_diminished(self):
        assert get_intervals("min7b5") == [0, 3, 6, 10]
        assert get_intervals("m7b5") == [0, 3, 6, 10]

    def test_diminished_seventh(self):
        assert get_intervals("dim7") == [0, 3, 6, 9]

    def test_ninth(self):
        assert get_intervals("9") == [0, 4, 7, 10, 14]

    def test_minor_ninth(self):
        assert get_intervals("min9") == [0, 3, 7, 10, 14]
        assert get_intervals("m9") == [0, 3, 7, 10, 14]

    def test_sixth(self):
        assert get_intervals("6") == [0, 4, 7, 9]

    def test_minor_sixth(self):
        assert get_intervals("min6") == [0, 3, 7, 9]
        assert get_intervals("m6") == [0, 3, 7, 9]

    def test_unknown_quality(self):
        assert get_intervals("power5") is None
        assert get_intervals("zzz") is None

    def test_all_qualities_defined(self):
        """Every entry in CHORD_QUALITIES should be accessible via get_intervals."""
        for quality, intervals in CHORD_QUALITIES.items():
            assert get_intervals(quality) == intervals


# ---------------------------------------------------------------------------
# CC Names
# ---------------------------------------------------------------------------


class TestCCNames:
    """Tests for CC name/number mappings."""

    def test_forward_lookup_all(self):
        """Every CC name maps to its number."""
        for name, number in CC_NAMES.items():
            assert cc_to_number(name) == number

    def test_reverse_lookup_all(self):
        """Every CC number maps back to a name."""
        for name, number in CC_NAMES.items():
            result = number_to_cc(number)
            assert result is not None
            # The reverse lookup gives the canonical name (first name for that number)
            assert CC_NAMES[result] == number

    def test_case_insensitive(self):
        assert cc_to_number("Modulation") == 1
        assert cc_to_number("SUSTAIN") == 64
        assert cc_to_number("Pan") == 10

    def test_spaces_instead_of_hyphens(self):
        assert cc_to_number("portamento time") == 5
        assert cc_to_number("soft pedal") == 67
        assert cc_to_number("all notes off") == 123

    def test_unknown_cc(self):
        assert cc_to_number("whammy-bar") is None

    def test_reverse_unknown(self):
        assert number_to_cc(999) is None

    def test_specific_ccs(self):
        """Spot-check well-known CCs."""
        assert cc_to_number("volume") == 7
        assert cc_to_number("pan") == 10
        assert cc_to_number("sustain") == 64
        assert cc_to_number("expression") == 11

    def test_parse_cc_sustain_on(self):
        assert parse_cc_value("sustain", "on") == (64, 127)

    def test_parse_cc_sustain_off(self):
        assert parse_cc_value("sustain", "off") == (64, 0)

    def test_parse_cc_numeric_value(self):
        assert parse_cc_value("volume", "100") == (7, 100)

    def test_parse_cc_on_off_case_insensitive(self):
        assert parse_cc_value("sustain", "ON") == (64, 127)
        assert parse_cc_value("sustain", "Off") == (64, 0)

    def test_parse_cc_unknown_name_raises(self):
        with pytest.raises(ValueError, match="Unknown CC name"):
            parse_cc_value("whammy", "64")

    def test_parse_cc_invalid_value_raises(self):
        with pytest.raises(ValueError, match="Invalid CC value"):
            parse_cc_value("volume", "loud")

    def test_parse_cc_out_of_range_raises(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_cc_value("volume", "200")


# ---------------------------------------------------------------------------
# Velocity Names
# ---------------------------------------------------------------------------


class TestVelocityNames:
    """Tests for symbolic velocity parsing."""

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("ppp", 16),
            ("pp", 33),
            ("p", 49),
            ("mp", 64),
            ("mf", 80),
            ("f", 96),
            ("ff", 112),
            ("fff", 127),
        ],
    )
    def test_all_symbolic_names(self, name: str, expected: int):
        assert parse_velocity(name) == expected

    def test_numeric_string(self):
        assert parse_velocity("80") == 80
        assert parse_velocity("0") == 0
        assert parse_velocity("127") == 127

    def test_case_insensitive(self):
        assert parse_velocity("MF") == 80
        assert parse_velocity("Ff") == 112

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown velocity"):
            parse_velocity("loud")

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_velocity("200")

    def test_velocity_names_dict(self):
        """All 8 dynamic levels should be defined."""
        assert len(VELOCITY_NAMES) == 8
        for name in ("ppp", "pp", "p", "mp", "mf", "f", "ff", "fff"):
            assert name in VELOCITY_NAMES
