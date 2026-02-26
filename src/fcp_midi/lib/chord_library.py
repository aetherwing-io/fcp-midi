"""Chord quality definitions — interval arrays for common chord types."""

from __future__ import annotations

CHORD_QUALITIES: dict[str, list[int]] = {
    "maj": [0, 4, 7],
    "": [0, 4, 7],  # default = major
    "min": [0, 3, 7],
    "m": [0, 3, 7],
    "7": [0, 4, 7, 10],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "m7": [0, 3, 7, 10],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "add9": [0, 4, 7, 14],
    "min7b5": [0, 3, 6, 10],
    "m7b5": [0, 3, 6, 10],
    "dim7": [0, 3, 6, 9],
    "9": [0, 4, 7, 10, 14],
    "min9": [0, 3, 7, 10, 14],
    "m9": [0, 3, 7, 10, 14],
    "6": [0, 4, 7, 9],
    "min6": [0, 3, 7, 9],
    "m6": [0, 3, 7, 9],
}


def get_intervals(quality: str) -> list[int] | None:
    """Return the interval array for a chord quality, or None if unknown."""
    return CHORD_QUALITIES.get(quality)
