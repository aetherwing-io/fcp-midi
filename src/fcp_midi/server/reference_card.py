"""MIDI FCP reference card — generated from verb registry + static sections.

Uses ``VerbRegistry`` from fcp_core for structured verb management,
with domain-specific static sections for MIDI reference.
"""

from __future__ import annotations

from fcp_core import VerbRegistry

from fcp_midi.server.verb_registry import VERBS


# Build a VerbRegistry instance from the MIDI verb list
_registry = VerbRegistry()
_registry.register_many(VERBS)


# -----------------------------------------------------------------------
# Extra sections for the reference card (MIDI-specific)
# -----------------------------------------------------------------------

_EXTRA_SECTIONS: dict[str, str] = {}

_SELECTORS_SECTION = """\
## Selectors
  @track:NAME        Notes on a specific track
  @channel:N         Notes on MIDI channel N
  @range:M.B-M.B    Notes in range (inclusive start and end beats)
  @pitch:PITCH       Notes matching a pitch (e.g. C4)
  @velocity:N-M      Notes with velocity in range
  @all               All notes in the song
  @recent            Last event from the log
  @recent:N          Last N events from the log
  @not:TYPE:VALUE    Negate a selector (exclude matches)

  Combine selectors to intersect: @track:Piano @range:1.1-4.4
  Negate to exclude: @track:Piano @not:pitch:C4"""

_POSITION_SECTION = """\
## Position Syntax
  M.B                Measure.Beat (1-based): 1.1 = start
  M.B.T              With tick offset: 1.1.120
  tick:N             Raw absolute tick
  +DUR               Relative: reference tick + duration
  -DUR               Relative: reference tick - duration
  end                Song end (last note end tick)"""

_DURATION_SECTION = """\
## Duration Syntax
  whole, half, quarter, eighth, sixteenth, 32nd
  1n, 2n, 4n, 8n, 16n, 32n
  dotted-quarter, triplet-eighth
  ticks:N            Raw tick count"""

_PITCH_SECTION = """\
## Pitch Syntax
  C4, D#5, Bb3       Note + accidental + octave
  midi:60            Raw MIDI number (60 = middle C)"""

_CHORD_SECTION = """\
## Chord Symbols
  Cmaj, Am, Dm7, G7, Bdim, Faug, Csus4, Asus2
  Cmaj7, Am7, Dm7b5, G9, Cm6, Cadd9
  Dm/F               Slash chord (inversion)"""

_VELOCITY_SECTION = """\
## Velocity Syntax
  0-127              Numeric value
  ppp, pp, p, mp, mf, f, ff, fff   Dynamic names"""

_CC_SECTION = """\
## CC Names
  volume, pan, modulation, expression, sustain,
  reverb, chorus, brightness, portamento, breath"""

_QUERY_SECTION = """\
## Query Commands (via `midi_query` tool)
  map                Song overview
  tracks             List all tracks
  events TRACK|*|all [M.B-M.B]  Events on a track (or all)
  describe TRACK     Detailed track info
  stats              Song statistics
  status             Session status
  find PITCH         Search notes by pitch
  tracker TRACK M.B-M.B [res:RES]  Tracker step view (single track)
  tracker Track1,Track2 M.B-M.B [res:RES]  Multi-track combined view (read-only)
  tracker * M.B-M.B [res:RES]     All tracks combined view (read-only)
  history N          Recent N events from log
  diff checkpoint:NAME  Events since checkpoint
  instruments [FILTER] List available instruments"""

_SESSION_SECTION = """\
## Session Actions (via `midi_session` tool)
  new "Title" [tempo:N] [time-sig:N/D] [key:K] [ppqn:N]
  open ./file.mid
  save
  save as:./path.mid
  checkpoint NAME
  undo [to:NAME]
  redo
  load-soundfont PATH"""

_GM_SECTION = """\
## GM Instruments (examples)
  acoustic-grand-piano, electric-piano-1, vibraphone
  acoustic-guitar-nylon, electric-bass-finger, violin
  trumpet, alto-sax, flute, string-ensemble-1"""

_CUSTOM_INSTRUMENTS_SECTION = """\
## Custom Instruments
  program:N           Raw MIDI program number (0-127)
  bank:MSB            Bank select (MSB only)
  bank:MSB.LSB        Bank select (MSB and LSB)
  load-soundfont PATH Load presets from .sf2 file
  instruments [FILTER] Query available instruments"""

_EXAMPLE_SECTION = """\
## Example Workflow
  1. midi_session('new "My Song" tempo:120 time-sig:4/4 key:C-major')
  2. midi(['track add Piano instrument:acoustic-grand-piano'])
  3. midi(['track add Bass instrument:acoustic-bass'])
  4. midi(['note Piano C4 at:1.1 dur:quarter vel:mf',
          'note Piano E4 at:1.2 dur:quarter vel:mf',
          'chord Piano Cmaj at:2.1 dur:half vel:f'])
  5. midi(['note Bass C2 at:1.1 dur:half vel:f'])
  6. midi_query('map')
  7. midi_session('checkpoint v1')
  8. midi_session('save as:./my-song.mid')"""


def _build_reference_card() -> str:
    """Build the reference card from the verb registry and static sections."""
    lines: list[str] = []
    lines.append("# MIDI FCP Reference Card")
    lines.append("")
    lines.append("## Mutation Operations (via `midi` tool)")

    # Group verbs by category, preserving insertion order with custom titles
    categories = {
        "music": "Notes, Chords & Tracks",
        "meta": "Tempo, Time & Key",
        "editing": "Editing (selector-based)",
        "state": "Track State",
    }
    for cat_key, cat_title in categories.items():
        cat_verbs = [v for v in _registry.verbs if v.category == cat_key]
        if not cat_verbs:
            continue
        lines.append(f"")
        lines.append(f"### {cat_title}")
        for v in cat_verbs:
            lines.append(f"  {v.syntax}")

    # Static sections below
    lines.append("")
    lines.append(_SELECTORS_SECTION)
    lines.append(_POSITION_SECTION)
    lines.append(_DURATION_SECTION)
    lines.append(_PITCH_SECTION)
    lines.append(_CHORD_SECTION)
    lines.append(_VELOCITY_SECTION)
    lines.append(_CC_SECTION)
    lines.append(_QUERY_SECTION)
    lines.append(_SESSION_SECTION)
    lines.append(_GM_SECTION)
    lines.append(_CUSTOM_INSTRUMENTS_SECTION)
    lines.append(_EXAMPLE_SECTION)

    return "\n".join(lines)


def build_tool_description() -> str:
    """Build the inline tool description for the `midi` tool.

    Embeds the full reference card directly in the tool description so the
    LLM sees the complete command set on connect — no extra call needed.
    Follows the same pattern as fcp-drawio's `drawio` tool.
    """
    lines: list[str] = []
    lines.append(
        "Execute MIDI operations. Each op string follows: VERB TARGET [key:value ...]\n"
        "Call midi_help for the full reference card.\n"
    )
    lines.append("MIDI FCP — COMMAND REFERENCE\n")

    # Verb syntax by category (using registry)
    categories = {
        "music": "NOTES, CHORDS & TRACKS",
        "meta": "TEMPO, TIME & KEY",
        "editing": "EDITING (selector-based)",
        "state": "TRACK STATE",
    }
    for cat_key, cat_title in categories.items():
        cat_verbs = [v for v in _registry.verbs if v.category == cat_key]
        if not cat_verbs:
            continue
        lines.append(f"{cat_title}:")
        for v in cat_verbs:
            lines.append(f"  {v.syntax}")
        lines.append("")

    # Inline reference sections (compact)
    lines.append(
        "SELECTORS:\n"
        "  @track:NAME  @channel:N  @range:M.B-M.B  @pitch:PITCH\n"
        "  @velocity:N-M  @all  @recent  @recent:N  @not:TYPE:VALUE\n"
        "  Combine to intersect: @track:Piano @range:1.1-4.4\n"
    )
    lines.append(
        "POSITION:\n"
        "  M.B (1.1 = start)  M.B.T (tick offset)  tick:N  +DUR  -DUR  end\n"
    )
    lines.append(
        "DURATION:\n"
        "  whole, half, quarter, eighth, sixteenth, 32nd\n"
        "  1n, 2n, 4n, 8n, 16n, 32n\n"
        "  dotted-quarter, triplet-eighth, ticks:N\n"
    )
    lines.append(
        "PITCH:\n"
        "  C4, D#5, Bb3 (note+accidental+octave)  midi:60 (raw MIDI number)\n"
    )
    lines.append(
        "CHORDS:\n"
        "  Cmaj, Am, Dm7, G7, Bdim, Faug, Csus4, Asus2\n"
        "  Cmaj7, Am7, Dm7b5, G9, Cm6, Cadd9, Dm/F (slash)\n"
    )
    lines.append(
        "VELOCITY:\n"
        "  0-127 (numeric)  ppp, pp, p, mp, mf, f, ff, fff (dynamic names)\n"
    )
    lines.append(
        "CC NAMES:\n"
        "  volume, pan, modulation, expression, sustain,\n"
        "  reverb, chorus, brightness, portamento, breath\n"
    )
    lines.append(
        "GM INSTRUMENTS (examples):\n"
        "  acoustic-grand-piano, electric-piano-1, vibraphone\n"
        "  acoustic-guitar-nylon, electric-bass-finger, violin\n"
        "  trumpet, alto-sax, flute, string-ensemble-1\n"
        "  program:N (raw 0-127)  bank:MSB[.LSB]\n"
    )
    lines.append(
        "RESPONSE PREFIXES:\n"
        "  +  note/chord added     ~  event modified\n"
        "  *  track modified       -  event removed\n"
        "  !  meta event           @  bulk operation\n"
    )
    lines.append(
        "CONVENTIONS:\n"
        "  - Positions are 1-based: measure 1, beat 1 = 1.1\n"
        "  - Channels are 1-indexed user-facing (ch:1 through ch:16)\n"
        "  - Channel 10 is drums (GM standard)\n"
        "  - Track names are unique identifiers — no ID management needed\n"
        "  - Batch multiple ops in one call for efficiency\n"
        "  - Call midi_help after context truncation for full reference"
    )

    return "\n".join(lines)


# Build the card at module load time
REFERENCE_CARD = _build_reference_card()
