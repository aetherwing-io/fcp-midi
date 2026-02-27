"""Tests for SoundFont metadata: SF2 parser and instrument registry."""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path

import pytest

from fcp_midi.lib.instrument_registry import InstrumentRegistry
from fcp_midi.lib.soundfont import SoundFontPreset, load_soundfont_presets
from fcp_midi.server.resolvers import (
    InstrumentResolution,
    resolve_bank,
    resolve_instrument,
)


# -----------------------------------------------------------------------
# SF2 binary fixture helper
# -----------------------------------------------------------------------

def _build_minimal_sf2(presets: list[tuple[str, int, int]]) -> bytes:
    """Build a minimal SF2 binary with just the phdr chunk.

    Each preset is (name, program, bank). An EOP terminator is appended.
    """
    # Build phdr chunk data
    phdr_records = []
    for name, program, bank in presets:
        name_bytes = name.encode("ascii")[:20].ljust(20, b"\x00")
        # phdr: name(20) + preset(H) + bank(H) + bag_ndx(H) + lib(I) + genre(I) + morph(I)
        record = struct.pack("<20sHHHIII", name_bytes, program, bank, 0, 0, 0, 0)
        phdr_records.append(record)
    # EOP terminator
    eop = struct.pack("<20sHHHIII", b"EOP\x00" + b"\x00" * 16, 0, 0, 0, 0, 0, 0)
    phdr_records.append(eop)

    phdr_data = b"".join(phdr_records)
    phdr_chunk = b"phdr" + struct.pack("<I", len(phdr_data)) + phdr_data

    # Wrap in LIST 'pdta'
    pdta_body = phdr_chunk
    pdta_chunk = b"LIST" + struct.pack("<I", len(pdta_body) + 4) + b"pdta" + pdta_body

    # Wrap in RIFF 'sfbk'
    riff_body = b"sfbk" + pdta_chunk
    riff = b"RIFF" + struct.pack("<I", len(riff_body)) + riff_body

    return riff


# -----------------------------------------------------------------------
# SF2 parser tests
# -----------------------------------------------------------------------

class TestSF2Parser:
    def test_parse_presets(self, tmp_path: Path) -> None:
        sf2_data = _build_minimal_sf2([
            ("Grand Piano", 0, 0),
            ("Warm Pad", 89, 1),
            ("Electric Bass", 33, 0),
        ])
        sf2_path = tmp_path / "test.sf2"
        sf2_path.write_bytes(sf2_data)

        presets = load_soundfont_presets(str(sf2_path))
        assert len(presets) == 3
        assert presets[0].name == "Grand Piano"
        assert presets[0].program == 0
        assert presets[0].bank == 0
        assert presets[1].name == "Warm Pad"
        assert presets[1].program == 89
        assert presets[1].bank == 1
        assert presets[2].name == "Electric Bass"
        assert presets[2].program == 33

    def test_empty_presets(self, tmp_path: Path) -> None:
        """SF2 with only EOP should return empty list."""
        sf2_data = _build_minimal_sf2([])
        sf2_path = tmp_path / "empty.sf2"
        sf2_path.write_bytes(sf2_data)

        presets = load_soundfont_presets(str(sf2_path))
        assert presets == []

    def test_invalid_file(self, tmp_path: Path) -> None:
        bad_path = tmp_path / "bad.sf2"
        bad_path.write_bytes(b"not a soundfont")

        with pytest.raises(ValueError, match="Not a valid SF2"):
            load_soundfont_presets(str(bad_path))

    def test_too_small_file(self, tmp_path: Path) -> None:
        tiny_path = tmp_path / "tiny.sf2"
        tiny_path.write_bytes(b"RIFF")

        with pytest.raises(ValueError, match="too small"):
            load_soundfont_presets(str(tiny_path))


# -----------------------------------------------------------------------
# Instrument registry tests
# -----------------------------------------------------------------------

class TestInstrumentRegistry:
    def test_default_has_128_gm_instruments(self) -> None:
        reg = InstrumentRegistry()
        specs = reg.list_instruments()
        assert len(specs) == 128

    def test_resolve_gm_name(self) -> None:
        reg = InstrumentRegistry()
        spec = reg.resolve("violin")
        assert spec is not None
        assert spec.program == 40
        assert spec.source == "gm"

    def test_resolve_gm_partial_match(self) -> None:
        reg = InstrumentRegistry()
        spec = reg.resolve("grand-piano")
        assert spec is not None
        assert spec.program == 0

    def test_resolve_unknown_returns_none(self) -> None:
        reg = InstrumentRegistry()
        spec = reg.resolve("zzz-nonexistent-instrument")
        assert spec is None

    def test_resolve_with_bank(self) -> None:
        reg = InstrumentRegistry()
        spec = reg.resolve("violin")
        assert spec is not None
        assert spec.bank_msb == 0
        assert spec.bank_lsb == 0

    def test_load_soundfont(self, tmp_path: Path) -> None:
        sf2_data = _build_minimal_sf2([
            ("Synth Lead", 80, 5),
            ("Custom Pad", 89, 3),
        ])
        sf2_path = tmp_path / "custom.sf2"
        sf2_path.write_bytes(sf2_data)

        reg = InstrumentRegistry()
        count = reg.load_soundfont(str(sf2_path))
        assert count == 2

        # SF2 presets should be resolvable
        spec = reg.resolve("Synth Lead")
        assert spec is not None
        assert spec.program == 80
        assert spec.bank_msb == 5
        assert spec.source == "soundfont"

    def test_soundfont_overrides_gm(self, tmp_path: Path) -> None:
        """SF2 preset with same name as GM instrument takes precedence."""
        sf2_data = _build_minimal_sf2([
            ("violin", 40, 2),  # Same name as GM, different bank
        ])
        sf2_path = tmp_path / "override.sf2"
        sf2_path.write_bytes(sf2_data)

        reg = InstrumentRegistry()
        reg.load_soundfont(str(sf2_path))

        spec = reg.resolve("violin")
        assert spec is not None
        assert spec.bank_msb == 2
        assert spec.source == "soundfont"

    def test_list_filtered_by_source(self, tmp_path: Path) -> None:
        sf2_data = _build_minimal_sf2([("Test Preset", 0, 1)])
        sf2_path = tmp_path / "filter.sf2"
        sf2_path.write_bytes(sf2_data)

        reg = InstrumentRegistry()
        reg.load_soundfont(str(sf2_path))

        gm_only = reg.list_instruments(source="gm")
        sf_only = reg.list_instruments(source="soundfont")

        # The "violin" override from above isn't in this test; all 128 should be gm
        # (unless one got overridden, but we only added "Test Preset" bank:1)
        assert len(sf_only) == 1
        assert sf_only[0].name == "test-preset"
        # GM count may be 127 if "test-preset" matched "acoustic-grand-piano"
        # but since name is different, should still be 128
        assert len(gm_only) == 128

    # Fuzzy matching tests

    def test_fuzzy_resolve_typo(self) -> None:
        """Typo in instrument name should fuzzy-match."""
        reg = InstrumentRegistry()
        spec = reg.resolve("violen")  # typo for "violin"
        assert spec is not None
        assert spec.program == 40

    def test_fuzzy_resolve_close_misspelling(self) -> None:
        """Close misspelling should auto-resolve."""
        reg = InstrumentRegistry()
        spec = reg.resolve("trumpt")  # typo for "trumpet"
        assert spec is not None
        assert spec.program == 56

    def test_fuzzy_resolve_too_far(self) -> None:
        """Completely wrong name should not fuzzy-match."""
        reg = InstrumentRegistry()
        spec = reg.resolve("zzz-blorp-machine")
        assert spec is None

    def test_suggest_returns_suggestions(self) -> None:
        """suggest() should return close matches for error messages."""
        reg = InstrumentRegistry()
        suggestion = reg.suggest("violen")
        assert suggestion is not None
        assert "violin" in suggestion

    def test_suggest_returns_none_for_gibberish(self) -> None:
        reg = InstrumentRegistry()
        suggestion = reg.suggest("zzzzzzzzz")
        assert suggestion is None

    def test_fuzzy_resolve_soundfont_preset(self, tmp_path: Path) -> None:
        """Fuzzy matching should also work on SF2 preset names."""
        sf2_data = _build_minimal_sf2([
            ("Warm Strings", 48, 2),
        ])
        sf2_path = tmp_path / "fuzzy.sf2"
        sf2_path.write_bytes(sf2_data)

        reg = InstrumentRegistry()
        reg.load_soundfont(str(sf2_path))

        spec = reg.resolve("warm-strigns")  # typo
        assert spec is not None
        assert spec.program == 48
        assert spec.source == "soundfont"


# -----------------------------------------------------------------------
# Resolver helper tests
# -----------------------------------------------------------------------

class TestResolverHelpers:

    def test_resolve_bank_none(self) -> None:
        result = resolve_bank({})
        assert result == (None, None)

    def test_resolve_bank_msb_only(self) -> None:
        result = resolve_bank({"bank": "5"})
        assert result == (5, None)

    def test_resolve_bank_msb_lsb(self) -> None:
        result = resolve_bank({"bank": "3.12"})
        assert result == (3, 12)

    def test_resolve_bank_invalid(self) -> None:
        result = resolve_bank({"bank": "abc"})
        assert isinstance(result, str)  # error string

    def test_resolve_bank_out_of_range(self) -> None:
        result = resolve_bank({"bank": "200"})
        assert isinstance(result, str)

    def test_resolve_instrument_program_number(self) -> None:
        result = resolve_instrument({"program": "42"}, None)
        assert isinstance(result, InstrumentResolution)
        assert result.program == 42
        assert result.instrument_name == "cello"  # GM program 42

    def test_resolve_instrument_by_name(self) -> None:
        reg = InstrumentRegistry()
        result = resolve_instrument({"instrument": "violin"}, reg)
        assert isinstance(result, InstrumentResolution)
        assert result.program == 40

    def test_resolve_instrument_fuzzy_name(self) -> None:
        reg = InstrumentRegistry()
        result = resolve_instrument({"instrument": "violen"}, reg)
        assert isinstance(result, InstrumentResolution)
        assert result.program == 40  # violin

    def test_resolve_instrument_unknown_with_suggestion(self) -> None:
        reg = InstrumentRegistry()
        result = resolve_instrument({"instrument": "zzz-blorp"}, reg)
        assert isinstance(result, str)  # error string

    def test_resolve_instrument_drum_kit(self) -> None:
        reg = InstrumentRegistry()
        result = resolve_instrument({"instrument": "drums"}, reg)
        assert isinstance(result, InstrumentResolution)
        assert result.is_drum_kit is True

    def test_resolve_instrument_no_params(self) -> None:
        result = resolve_instrument({}, None)
        assert isinstance(result, InstrumentResolution)
        assert result.program is None
        assert result.instrument_name is None
