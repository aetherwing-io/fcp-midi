"""Unified instrument lookup: GM instruments + SoundFont presets.

The registry is the single source of truth for resolving instrument names
to MIDI program numbers (and optional bank select values).
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from fcp_midi.lib.gm_instruments import (
    GM_INSTRUMENTS,
    _normalize,
    instrument_to_program,
)
from fcp_midi.lib.soundfont import SoundFontPreset, load_soundfont_presets


@dataclass
class InstrumentSpec:
    """Resolved instrument specification."""
    name: str
    program: int
    bank_msb: int = 0
    bank_lsb: int = 0
    source: str = "gm"  # "gm" | "soundfont" | "custom"


class InstrumentRegistry:
    """Unified instrument lookup combining GM + custom presets."""

    def __init__(self) -> None:
        self._specs: dict[str, InstrumentSpec] = {}
        self._load_gm()

    def _load_gm(self) -> None:
        """Pre-populate with the 128 GM instruments."""
        for program, name in GM_INSTRUMENTS.items():
            self._specs[name] = InstrumentSpec(name=name, program=program)

    def load_soundfont(self, path: str) -> int:
        """Load presets from an SF2 file. Returns count of presets loaded."""
        presets = load_soundfont_presets(path)
        count = 0
        for p in presets:
            normalized = _normalize(p.name)
            if not normalized:
                continue
            self._specs[normalized] = InstrumentSpec(
                name=normalized,
                program=p.program,
                bank_msb=p.bank,
                bank_lsb=0,
                source="soundfont",
            )
            count += 1
        return count

    def resolve(self, name: str) -> InstrumentSpec | None:
        """Look up an instrument by name.

        Priority: exact match (SF2 overrides GM) > alias > partial > fuzzy.
        """
        normalized = _normalize(name)

        # Exact match
        if normalized in self._specs:
            return self._specs[normalized]

        # Fall back to GM lookup (handles aliases and partial matching)
        program = instrument_to_program(name)
        if program is not None:
            gm_name = GM_INSTRUMENTS.get(program, normalized)
            return InstrumentSpec(name=gm_name, program=program)

        # Fuzzy match — edit-distance based, catches typos like "piono", "vilon"
        candidates = list(self._specs.keys())
        matches = difflib.get_close_matches(normalized, candidates, n=1, cutoff=0.6)
        if matches:
            return self._specs[matches[0]]

        return None

    def suggest(self, name: str) -> str | None:
        """Return a 'did you mean?' suggestion for a failed lookup."""
        normalized = _normalize(name)
        candidates = list(self._specs.keys())
        matches = difflib.get_close_matches(normalized, candidates, n=3, cutoff=0.4)
        if matches:
            suggestions = ", ".join(matches)
            return f"Did you mean: {suggestions}?"
        return None

    def list_instruments(self, source: str | None = None) -> list[InstrumentSpec]:
        """List all available instruments, optionally filtered by source."""
        specs = list(self._specs.values())
        if source is not None:
            specs = [s for s in specs if s.source == source]
        return sorted(specs, key=lambda s: (s.bank_msb, s.program, s.name))
