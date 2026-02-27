"""Minimal SoundFont 2 (.sf2) preset reader.

Reads only the preset headers (phdr sub-chunk) — no sample data.
Zero external dependencies; uses only the ``struct`` module.

SF2 format overview:
    RIFF 'sfbk'
      LIST 'INFO' ...
      LIST 'sdta' ...
      LIST 'pdta'
        'phdr' sub-chunk  <-- we read this
        ...
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SoundFontPreset:
    """A single preset from a SoundFont file."""
    name: str
    program: int    # 0-127
    bank: int       # bank number (MSB)


# Each preset header record is 38 bytes:
#   name:            20 bytes (null-terminated ASCII)
#   preset:          uint16  (program number)
#   bank:            uint16  (bank number)
#   preset_bag_ndx:  uint16
#   library:         uint32
#   genre:           uint32
#   morphology:      uint32
_PHDR_SIZE = 38
_PHDR_STRUCT = struct.Struct("<20sHHHIII")


def load_soundfont_presets(path: str | Path) -> list[SoundFontPreset]:
    """Read preset headers from an SF2 file.

    Returns a list of :class:`SoundFontPreset` with name, program, and bank.
    The terminal "EOP" (End Of Presets) record is excluded.
    """
    data = Path(path).read_bytes()
    if len(data) < 12:
        raise ValueError(f"File too small to be SF2: {path}")

    # Verify RIFF header and 'sfbk' form type
    riff_id = data[0:4]
    form_type = data[8:12]
    if riff_id != b"RIFF" or form_type != b"sfbk":
        raise ValueError(f"Not a valid SF2 file: {path}")

    # Walk top-level chunks to find LIST 'pdta'
    phdr_data = _find_phdr(data, 12)
    if phdr_data is None:
        raise ValueError(f"No preset headers (phdr) found in: {path}")

    # Parse 38-byte records
    n_records = len(phdr_data) // _PHDR_SIZE
    if n_records < 2:
        return []  # Need at least one preset + EOP terminator

    presets: list[SoundFontPreset] = []
    for i in range(n_records - 1):  # Skip the terminal EOP record
        offset = i * _PHDR_SIZE
        name_bytes, program, bank, _bag, _lib, _genre, _morph = (
            _PHDR_STRUCT.unpack_from(phdr_data, offset)
        )
        name = name_bytes.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()
        if name:
            presets.append(SoundFontPreset(name=name, program=program, bank=bank))

    return presets


def _find_phdr(data: bytes, start: int) -> bytes | None:
    """Walk RIFF chunks starting at *start* to find the 'phdr' sub-chunk."""
    pos = start
    end = len(data)

    while pos + 8 <= end:
        chunk_id = data[pos:pos + 4]
        chunk_size = struct.unpack_from("<I", data, pos + 4)[0]

        if chunk_id == b"LIST" and pos + 12 <= end:
            list_type = data[pos + 8:pos + 12]
            if list_type == b"pdta":
                # Search inside pdta for phdr
                return _find_sub_chunk(data, pos + 12, pos + 8 + chunk_size, b"phdr")
            else:
                # Recurse into other LIST chunks? No — pdta is top-level.
                pass

        # Advance to next chunk (chunks are word-aligned)
        pos += 8 + chunk_size
        if chunk_size % 2:
            pos += 1  # pad byte

    return None


def _find_sub_chunk(data: bytes, start: int, end: int, target: bytes) -> bytes | None:
    """Find a sub-chunk by ID within a range."""
    pos = start
    while pos + 8 <= end:
        chunk_id = data[pos:pos + 4]
        chunk_size = struct.unpack_from("<I", data, pos + 4)[0]

        if chunk_id == target:
            chunk_start = pos + 8
            chunk_end = chunk_start + chunk_size
            if chunk_end <= end:
                return data[chunk_start:chunk_end]

        pos += 8 + chunk_size
        if chunk_size % 2:
            pos += 1  # pad byte

    return None
