#!/usr/bin/env python3
"""Voltage Drop — Original EDM/Pop track.

Neon-lit warehouse rave at 2am. High-energy, euphoric, relentless.

Key: F# minor
Tempo: 145 BPM
Structure: Build (8 bars) -> Drop 1 (8 bars) -> Breakdown (8 bars) -> Drop 2 (8 bars)

Tracks (13):
  0. Meta/Tempo
  1. Supersaw Lead (program 81)
  2. Pluck Synth (program 45)
  3. Sub Bass (program 38)
  4. Acid Bass (program 87) — Drop 2 only
  5. Pad (program 89)
  6. Choir/Vocal Pad (program 52)
  7. Arpeggio Synth (program 83)
  8. Drums - Kick (ch10, note 36)
  9. Drums - Snare/Clap (ch10, note 38+39)
  10. Drums - Hats (ch10, note 42+46)
  11. Drums - FX (ch10, note 49+57)
  12. FX Riser (program 99)
"""

import mido

# =============================================================================
# CONSTANTS
# =============================================================================
TICKS_PER_BEAT = 480
BPM = 145
TEMPO = mido.bpm2tempo(BPM)

# Durations in ticks
WHOLE = TICKS_PER_BEAT * 4
HALF = TICKS_PER_BEAT * 2
QUARTER = TICKS_PER_BEAT
EIGHTH = TICKS_PER_BEAT // 2
SIXTEENTH = TICKS_PER_BEAT // 4
THIRTY_SECOND = TICKS_PER_BEAT // 8
DOTTED_QUARTER = QUARTER + EIGHTH
DOTTED_HALF = HALF + QUARTER
BAR = WHOLE  # one measure in 4/4

# Note name to MIDI number
NOTE_MAP = {}
for _oct in range(0, 9):
    _base = 12 + _oct * 12
    for _i, _name in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F',
                                 'F#', 'G', 'G#', 'A', 'A#', 'B']):
        NOTE_MAP[f'{_name}{_oct}'] = _base + _i
_flat_map = {'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'}
for _oct in range(0, 9):
    for _flat, _sharp in _flat_map.items():
        NOTE_MAP[f'{_flat}{_oct}'] = NOTE_MAP[f'{_sharp}{_oct}']


def n(name):
    """Convert note name to MIDI number."""
    return NOTE_MAP[name]


# =============================================================================
# F# MINOR CHORD DEFINITIONS
# Progression: F#m -> D -> A -> E  (i -> VI -> III -> VII)
# =============================================================================
CHORDS_HIGH = {
    'F#m': [n('F#4'), n('A4'), n('C#5')],
    'D':   [n('D4'), n('F#4'), n('A4')],
    'A':   [n('A4'), n('C#5'), n('E5')],
    'E':   [n('E4'), n('G#4'), n('B4')],
}

CHORDS_WIDE = {
    'F#m': [n('F#3'), n('C#4'), n('A4'), n('F#5')],
    'D':   [n('D3'), n('A3'), n('F#4'), n('D5')],
    'A':   [n('A3'), n('E4'), n('C#5'), n('A5')],
    'E':   [n('E3'), n('B3'), n('G#4'), n('E5')],
}

SUB_ROOTS = {'F#m': n('F#1'), 'D': n('D1'), 'A': n('A1'), 'E': n('E1')}

PROGRESSION = ['F#m', 'D', 'A', 'E']

# Arpeggio patterns (8-note cycle, repeats over 16 sixteenths per bar)
ARP_NOTES = {
    'F#m': [n('F#4'), n('A4'), n('C#5'), n('F#5'), n('C#5'), n('A4'), n('F#4'), n('C#5')],
    'D':   [n('D4'), n('F#4'), n('A4'), n('D5'), n('A4'), n('F#4'), n('D4'), n('A4')],
    'A':   [n('A4'), n('C#5'), n('E5'), n('A5'), n('E5'), n('C#5'), n('A4'), n('E5')],
    'E':   [n('E4'), n('G#4'), n('B4'), n('E5'), n('B4'), n('G#4'), n('E4'), n('B4')],
}

# Drop 1 melody — anthemic, big intervals, octave jumps
DROP_MELODY = {
    'F#m': [
        (n('F#5'), QUARTER, 120),
        (n('F#6'), DOTTED_QUARTER, 127),
        (n('E6'), EIGHTH, 110),
        (n('C#6'), HALF, 120),
        (n('A5'), QUARTER, 115),
        (n('F#5'), QUARTER, 110),
        (n('E5'), QUARTER, 105),
        (n('F#5'), QUARTER, 120),
    ],
    'D': [
        (n('D5'), QUARTER, 115),
        (n('D6'), DOTTED_QUARTER, 127),
        (n('C#6'), EIGHTH, 110),
        (n('A5'), HALF, 118),
        (n('F#5'), QUARTER, 110),
        (n('A5'), QUARTER, 115),
        (n('D6'), QUARTER, 120),
        (n('C#6'), QUARTER, 110),
    ],
    'A': [
        (n('A5'), QUARTER, 120),
        (n('A6'), DOTTED_QUARTER, 127),
        (n('G#6'), EIGHTH, 115),
        (n('E6'), HALF, 120),
        (n('C#6'), QUARTER, 115),
        (n('E6'), QUARTER, 120),
        (n('A5'), QUARTER, 110),
        (n('C#6'), QUARTER, 118),
    ],
    'E': [
        (n('E5'), QUARTER, 115),
        (n('E6'), DOTTED_QUARTER, 127),
        (n('D#6'), EIGHTH, 110),
        (n('B5'), HALF, 118),
        (n('G#5'), QUARTER, 110),
        (n('B5'), QUARTER, 115),
        (n('E6'), QUARTER + EIGHTH, 125),
        (n('D#6'), EIGHTH, 110),
    ],
}

# Drop 2 melody — ornamented, higher energy
DROP2_MELODY = {
    'F#m': [
        (n('F#5'), SIXTEENTH, 110),
        (n('G#5'), SIXTEENTH, 100),
        (n('F#5'), EIGHTH, 120),
        (n('F#6'), QUARTER, 127),
        (n('E6'), EIGHTH, 115),
        (n('C#6'), EIGHTH, 110),
        (n('E6'), QUARTER, 120),
        (n('A5'), EIGHTH, 115),
        (n('C#6'), EIGHTH, 110),
        (n('F#5'), QUARTER, 108),
        (n('E5'), EIGHTH, 105),
        (n('F#5'), DOTTED_QUARTER, 122),
    ],
    'D': [
        (n('D5'), SIXTEENTH, 108),
        (n('E5'), SIXTEENTH, 100),
        (n('D5'), EIGHTH, 115),
        (n('D6'), QUARTER, 127),
        (n('C#6'), EIGHTH, 112),
        (n('A5'), EIGHTH, 110),
        (n('C#6'), QUARTER, 118),
        (n('F#5'), EIGHTH, 112),
        (n('A5'), EIGHTH, 115),
        (n('D6'), QUARTER, 122),
        (n('C#6'), EIGHTH, 110),
        (n('A5'), DOTTED_QUARTER, 115),
    ],
    'A': [
        (n('A5'), SIXTEENTH, 112),
        (n('B5'), SIXTEENTH, 100),
        (n('A5'), EIGHTH, 120),
        (n('A6'), QUARTER, 127),
        (n('G#6'), EIGHTH, 115),
        (n('E6'), EIGHTH, 112),
        (n('G#6'), QUARTER, 122),
        (n('C#6'), EIGHTH, 115),
        (n('E6'), EIGHTH, 118),
        (n('A5'), QUARTER, 112),
        (n('C#6'), EIGHTH, 116),
        (n('E6'), DOTTED_QUARTER, 125),
    ],
    'E': [
        (n('E5'), SIXTEENTH, 110),
        (n('F#5'), SIXTEENTH, 100),
        (n('E5'), EIGHTH, 118),
        (n('E6'), QUARTER, 127),
        (n('D#6'), EIGHTH, 112),
        (n('B5'), EIGHTH, 110),
        (n('D#6'), QUARTER, 120),
        (n('G#5'), EIGHTH, 112),
        (n('B5'), EIGHTH, 115),
        (n('E6'), QUARTER, 125),
        (n('F#6'), EIGHTH, 127),
        (n('E6'), DOTTED_QUARTER, 122),
    ],
}

# Pluck build patterns (16th arps per bar)
PLUCK_BUILD = {
    'F#m': [n('F#4'), n('A4'), n('C#5'), n('A4')] * 4,
    'D':   [n('D4'), n('F#4'), n('A4'), n('F#4')] * 4,
    'A':   [n('A3'), n('C#4'), n('E4'), n('C#4')] * 4,
    'E':   [n('E4'), n('G#4'), n('B4'), n('G#4')] * 4,
}

PLUCK_DROP_STABS = {
    'F#m': [n('F#4'), n('A4'), n('C#5')],
    'D':   [n('D4'), n('F#4'), n('A4')],
    'A':   [n('A4'), n('C#5'), n('E5')],
    'E':   [n('E4'), n('G#4'), n('B4')],
}

# Acid bass (16th rhythmic pattern per bar)
ACID_PATTERNS = {
    'F#m': [
        (n('F#2'), SIXTEENTH, 110), (None, SIXTEENTH, 0),
        (n('F#2'), SIXTEENTH, 100), (n('A2'), SIXTEENTH, 105),
        (n('F#2'), SIXTEENTH, 110), (None, SIXTEENTH, 0),
        (n('C#3'), SIXTEENTH, 108), (n('F#2'), SIXTEENTH, 100),
        (n('F#2'), SIXTEENTH, 112), (n('A2'), SIXTEENTH, 105),
        (n('F#2'), SIXTEENTH, 100), (None, SIXTEENTH, 0),
        (n('C#3'), SIXTEENTH, 110), (n('A2'), SIXTEENTH, 105),
        (n('F#2'), SIXTEENTH, 108), (None, SIXTEENTH, 0),
    ],
    'D': [
        (n('D2'), SIXTEENTH, 110), (None, SIXTEENTH, 0),
        (n('D2'), SIXTEENTH, 100), (n('F#2'), SIXTEENTH, 105),
        (n('D2'), SIXTEENTH, 110), (None, SIXTEENTH, 0),
        (n('A2'), SIXTEENTH, 108), (n('D2'), SIXTEENTH, 100),
        (n('D2'), SIXTEENTH, 112), (n('F#2'), SIXTEENTH, 105),
        (n('D2'), SIXTEENTH, 100), (None, SIXTEENTH, 0),
        (n('A2'), SIXTEENTH, 110), (n('F#2'), SIXTEENTH, 105),
        (n('D2'), SIXTEENTH, 108), (None, SIXTEENTH, 0),
    ],
    'A': [
        (n('A2'), SIXTEENTH, 110), (None, SIXTEENTH, 0),
        (n('A2'), SIXTEENTH, 100), (n('C#3'), SIXTEENTH, 105),
        (n('A2'), SIXTEENTH, 110), (None, SIXTEENTH, 0),
        (n('E3'), SIXTEENTH, 108), (n('A2'), SIXTEENTH, 100),
        (n('A2'), SIXTEENTH, 112), (n('C#3'), SIXTEENTH, 105),
        (n('A2'), SIXTEENTH, 100), (None, SIXTEENTH, 0),
        (n('E3'), SIXTEENTH, 110), (n('C#3'), SIXTEENTH, 105),
        (n('A2'), SIXTEENTH, 108), (None, SIXTEENTH, 0),
    ],
    'E': [
        (n('E2'), SIXTEENTH, 110), (None, SIXTEENTH, 0),
        (n('E2'), SIXTEENTH, 100), (n('G#2'), SIXTEENTH, 105),
        (n('E2'), SIXTEENTH, 110), (None, SIXTEENTH, 0),
        (n('B2'), SIXTEENTH, 108), (n('E2'), SIXTEENTH, 100),
        (n('E2'), SIXTEENTH, 112), (n('G#2'), SIXTEENTH, 105),
        (n('E2'), SIXTEENTH, 100), (None, SIXTEENTH, 0),
        (n('B2'), SIXTEENTH, 110), (n('G#2'), SIXTEENTH, 105),
        (n('E2'), SIXTEENTH, 108), (None, SIXTEENTH, 0),
    ],
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def add_note(track, pitch, duration, velocity=100, channel=0):
    """Add a single note (or rest if pitch is None)."""
    if pitch is None:
        track.append(mido.Message('note_on', note=0, velocity=0, time=duration, channel=channel))
    else:
        track.append(mido.Message('note_on', note=pitch, velocity=velocity, time=0, channel=channel))
        track.append(mido.Message('note_off', note=pitch, velocity=0, time=duration, channel=channel))


def add_chord(track, pitches, duration, velocity=100, channel=0):
    """Add a chord (multiple simultaneous notes)."""
    for i, p in enumerate(pitches):
        track.append(mido.Message('note_on', note=p, velocity=velocity, time=0, channel=channel))
    for i, p in enumerate(pitches):
        track.append(mido.Message('note_off', note=p, velocity=0,
                                  time=duration if i == 0 else 0, channel=channel))


def add_rest(track, duration, channel=0):
    """Add silence / advance time."""
    track.append(mido.Message('note_on', note=0, velocity=0, time=duration, channel=channel))


# =============================================================================
# DRUM CONSTANTS
# =============================================================================
KICK = 36
SNARE = 38
CLAP = 39
CLOSED_HH = 42
OPEN_HH = 46
CRASH = 49
SPLASH = 57
CH = 9  # drum channel (0-indexed)


# =============================================================================
# MAIN COMPOSITION
# =============================================================================

def create_voltage_drop():
    mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)

    # =========================================================================
    # Track 0: Tempo & Meta
    # =========================================================================
    tempo_track = mido.MidiTrack()
    mid.tracks.append(tempo_track)
    tempo_track.append(mido.MetaMessage('set_tempo', tempo=TEMPO, time=0))
    tempo_track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tempo_track.append(mido.MetaMessage('key_signature', key='F#m', time=0))
    tempo_track.append(mido.MetaMessage('track_name', name='Voltage Drop', time=0))
    # Section markers
    tempo_track.append(mido.MetaMessage('marker', text='Build', time=0))
    tempo_track.append(mido.MetaMessage('marker', text='Drop 1', time=BAR * 8))
    tempo_track.append(mido.MetaMessage('marker', text='Breakdown', time=BAR * 8))
    tempo_track.append(mido.MetaMessage('marker', text='Drop 2', time=BAR * 8))

    sections = ['build', 'drop1', 'breakdown', 'drop2']

    # =========================================================================
    # Track 1: Supersaw Lead (program 81, channel 0)
    # =========================================================================
    lead_track = mido.MidiTrack()
    lead_track.append(mido.MetaMessage('track_name', name='Supersaw Lead', time=0))
    lead_track.append(mido.Message('program_change', program=81, channel=0, time=0))
    for sec in sections:
        if sec in ('build', 'breakdown'):
            add_rest(lead_track, BAR * 8, channel=0)
        elif sec == 'drop1':
            for chord_name in PROGRESSION:
                for pitch, dur, vel in DROP_MELODY[chord_name]:
                    add_note(lead_track, pitch, dur, vel, channel=0)
        elif sec == 'drop2':
            for chord_name in PROGRESSION:
                for pitch, dur, vel in DROP2_MELODY[chord_name]:
                    add_note(lead_track, pitch, dur, vel, channel=0)
    mid.tracks.append(lead_track)

    # =========================================================================
    # Track 2: Pluck Synth (program 45, channel 1)
    # =========================================================================
    pluck_track = mido.MidiTrack()
    pluck_track.append(mido.MetaMessage('track_name', name='Pluck Synth', time=0))
    pluck_track.append(mido.Message('program_change', program=45, channel=1, time=0))
    for sec in sections:
        if sec == 'build':
            for chord_name in PROGRESSION:
                pattern = PLUCK_BUILD[chord_name]
                for bar_idx in range(2):
                    for note_idx in range(16):
                        p = pattern[note_idx % len(pattern)]
                        vel = 85 + (note_idx % 4) * 5
                        add_note(pluck_track, p, SIXTEENTH, vel, channel=1)
        elif sec in ('drop1', 'drop2'):
            for chord_name in PROGRESSION:
                stab = PLUCK_DROP_STABS[chord_name]
                for bar_idx in range(2):
                    # Beat 1: stab
                    add_chord(pluck_track, stab, EIGHTH, 110, channel=1)
                    add_rest(pluck_track, EIGHTH + QUARTER, channel=1)
                    # "and of 2": stab
                    add_chord(pluck_track, stab, EIGHTH, 100, channel=1)
                    add_rest(pluck_track, EIGHTH, channel=1)
                    # Beat 3: stab
                    add_chord(pluck_track, stab, EIGHTH, 105, channel=1)
                    add_rest(pluck_track, EIGHTH + QUARTER, channel=1)
        elif sec == 'breakdown':
            for chord_name in PROGRESSION:
                melody = DROP_MELODY[chord_name]
                for pitch, dur, vel in melody:
                    add_note(pluck_track, pitch, dur, max(50, vel - 50), channel=1)
    mid.tracks.append(pluck_track)

    # =========================================================================
    # Track 3: Sub Bass (program 38, channel 2)
    # =========================================================================
    sub_track = mido.MidiTrack()
    sub_track.append(mido.MetaMessage('track_name', name='Sub Bass', time=0))
    sub_track.append(mido.Message('program_change', program=38, channel=2, time=0))
    for sec in sections:
        if sec == 'build':
            for chord_name in PROGRESSION:
                root = SUB_ROOTS[chord_name]
                add_note(sub_track, root, BAR * 2, 100, channel=2)
        elif sec in ('drop1', 'drop2'):
            for chord_name in PROGRESSION:
                root = SUB_ROOTS[chord_name]
                for bar_idx in range(2):
                    for beat in range(4):
                        # Sidechain feel: note + gap
                        add_note(sub_track, root, EIGHTH + SIXTEENTH, 110, channel=2)
                        add_rest(sub_track, SIXTEENTH, channel=2)
        elif sec == 'breakdown':
            add_rest(sub_track, BAR * 8, channel=2)
    mid.tracks.append(sub_track)

    # =========================================================================
    # Track 4: Acid Bass (program 87, channel 3) — Drop 2 only
    # =========================================================================
    acid_track = mido.MidiTrack()
    acid_track.append(mido.MetaMessage('track_name', name='Acid Bass', time=0))
    acid_track.append(mido.Message('program_change', program=87, channel=3, time=0))
    for sec in sections:
        if sec == 'drop2':
            for chord_name in PROGRESSION:
                pattern = ACID_PATTERNS[chord_name]
                for bar_idx in range(2):
                    for pitch, dur, vel in pattern:
                        add_note(acid_track, pitch, dur, vel, channel=3)
        else:
            add_rest(acid_track, BAR * 8, channel=3)
    mid.tracks.append(acid_track)

    # =========================================================================
    # Track 5: Warm Pad (program 89, channel 4)
    # =========================================================================
    pad_track = mido.MidiTrack()
    pad_track.append(mido.MetaMessage('track_name', name='Warm Pad', time=0))
    pad_track.append(mido.Message('program_change', program=89, channel=4, time=0))
    for sec in sections:
        if sec in ('build', 'breakdown'):
            vel = 95 if sec == 'build' else 80
            for chord_name in PROGRESSION:
                add_chord(pad_track, CHORDS_WIDE[chord_name], BAR * 2, vel, channel=4)
        else:
            add_rest(pad_track, BAR * 8, channel=4)
    mid.tracks.append(pad_track)

    # =========================================================================
    # Track 6: Choir Pad (program 52, channel 5) — Breakdown only
    # =========================================================================
    choir_track = mido.MidiTrack()
    choir_track.append(mido.MetaMessage('track_name', name='Choir Pad', time=0))
    choir_track.append(mido.Message('program_change', program=52, channel=5, time=0))
    for sec in sections:
        if sec == 'breakdown':
            for chord_name in PROGRESSION:
                add_chord(choir_track, CHORDS_HIGH[chord_name], BAR * 2, 75, channel=5)
        else:
            add_rest(choir_track, BAR * 8, channel=5)
    mid.tracks.append(choir_track)

    # =========================================================================
    # Track 7: Arpeggio Synth (program 83, channel 6) — Runs throughout
    # =========================================================================
    arp_track = mido.MidiTrack()
    arp_track.append(mido.MetaMessage('track_name', name='Arpeggio Synth', time=0))
    arp_track.append(mido.Message('program_change', program=83, channel=6, time=0))
    vel_map = {'build': 70, 'drop1': 90, 'breakdown': 55, 'drop2': 95}
    for sec in sections:
        v = vel_map[sec]
        for chord_name in PROGRESSION:
            arp_pattern = ARP_NOTES[chord_name]
            for bar_idx in range(2):
                for note_idx in range(16):
                    p = arp_pattern[note_idx % len(arp_pattern)]
                    accent = 10 if (note_idx % 4 == 0) else 0
                    add_note(arp_track, p, SIXTEENTH, min(127, v + accent), channel=6)
    mid.tracks.append(arp_track)

    # =========================================================================
    # Track 8: Drums - Kick (ch10, note 36) — Four on the floor, HARD
    # =========================================================================
    kick_track = mido.MidiTrack()
    kick_track.append(mido.MetaMessage('track_name', name='Drums - Kick', time=0))
    for sec in sections:
        if sec == 'build':
            # Kick first 4 bars, drops out for tension bars 5-8
            for bar_idx in range(4):
                for beat in range(4):
                    add_note(kick_track, KICK, QUARTER, 127, channel=CH)
            add_rest(kick_track, BAR * 4, channel=CH)
        elif sec in ('drop1', 'drop2'):
            for bar_idx in range(8):
                for beat in range(4):
                    add_note(kick_track, KICK, QUARTER, 127, channel=CH)
        elif sec == 'breakdown':
            # Half-time: kick on 1 and 3
            for bar_idx in range(8):
                add_note(kick_track, KICK, QUARTER, 120, channel=CH)
                add_rest(kick_track, QUARTER, channel=CH)
                add_note(kick_track, KICK, QUARTER, 110, channel=CH)
                add_rest(kick_track, QUARTER, channel=CH)
    mid.tracks.append(kick_track)

    # =========================================================================
    # Track 9: Drums - Snare/Clap (ch10, notes 38+39)
    # =========================================================================
    snare_track = mido.MidiTrack()
    snare_track.append(mido.MetaMessage('track_name', name='Drums - Snare/Clap', time=0))
    for sec in sections:
        if sec == 'build':
            # Bars 1-4: snare+clap on 2 and 4
            for bar_idx in range(4):
                add_rest(snare_track, QUARTER, channel=CH)
                snare_track.append(mido.Message('note_on', note=SNARE, velocity=110, time=0, channel=CH))
                snare_track.append(mido.Message('note_on', note=CLAP, velocity=100, time=0, channel=CH))
                snare_track.append(mido.Message('note_off', note=SNARE, velocity=0, time=QUARTER, channel=CH))
                snare_track.append(mido.Message('note_off', note=CLAP, velocity=0, time=0, channel=CH))
                add_rest(snare_track, QUARTER, channel=CH)
                snare_track.append(mido.Message('note_on', note=SNARE, velocity=110, time=0, channel=CH))
                snare_track.append(mido.Message('note_on', note=CLAP, velocity=100, time=0, channel=CH))
                snare_track.append(mido.Message('note_off', note=SNARE, velocity=0, time=QUARTER, channel=CH))
                snare_track.append(mido.Message('note_off', note=CLAP, velocity=0, time=0, channel=CH))
            # Bars 5-6: 8th note snare roll (building)
            for bar_idx in range(2):
                for beat in range(8):
                    vel = 80 + beat * 3
                    add_note(snare_track, SNARE, EIGHTH, vel, channel=CH)
            # Bar 7: 16th note snare roll
            for note_idx in range(16):
                vel = 85 + note_idx * 2
                add_note(snare_track, SNARE, SIXTEENTH, min(127, vel), channel=CH)
            # Bar 8: 32nd note snare roll (peak)
            for note_idx in range(32):
                vel = 90 + note_idx
                add_note(snare_track, SNARE, THIRTY_SECOND, min(127, vel), channel=CH)
        elif sec in ('drop1', 'drop2'):
            for bar_idx in range(8):
                add_rest(snare_track, QUARTER, channel=CH)
                snare_track.append(mido.Message('note_on', note=SNARE, velocity=120, time=0, channel=CH))
                snare_track.append(mido.Message('note_on', note=CLAP, velocity=115, time=0, channel=CH))
                snare_track.append(mido.Message('note_off', note=SNARE, velocity=0, time=QUARTER, channel=CH))
                snare_track.append(mido.Message('note_off', note=CLAP, velocity=0, time=0, channel=CH))
                add_rest(snare_track, QUARTER, channel=CH)
                snare_track.append(mido.Message('note_on', note=SNARE, velocity=120, time=0, channel=CH))
                snare_track.append(mido.Message('note_on', note=CLAP, velocity=115, time=0, channel=CH))
                snare_track.append(mido.Message('note_off', note=SNARE, velocity=0, time=QUARTER, channel=CH))
                snare_track.append(mido.Message('note_off', note=CLAP, velocity=0, time=0, channel=CH))
        elif sec == 'breakdown':
            # Half-time: snare on beat 3
            for bar_idx in range(8):
                add_rest(snare_track, HALF, channel=CH)
                add_note(snare_track, SNARE, QUARTER, 105, channel=CH)
                add_rest(snare_track, QUARTER, channel=CH)
    mid.tracks.append(snare_track)

    # =========================================================================
    # Track 10: Drums - Hats (ch10, notes 42+46) — Driving 16ths
    # =========================================================================
    hat_track = mido.MidiTrack()
    hat_track.append(mido.MetaMessage('track_name', name='Drums - Hats', time=0))
    for sec in sections:
        if sec == 'build':
            for bar_idx in range(8):
                for note_idx in range(16):
                    if note_idx % 4 == 2:
                        vel = min(100, 85 + bar_idx * 2)
                        add_note(hat_track, OPEN_HH, SIXTEENTH, vel, channel=CH)
                    else:
                        vel = 90 if (note_idx % 4 == 0) else 72
                        add_note(hat_track, CLOSED_HH, SIXTEENTH, vel, channel=CH)
        elif sec in ('drop1', 'drop2'):
            for bar_idx in range(8):
                for note_idx in range(16):
                    if note_idx % 4 == 2:
                        add_note(hat_track, OPEN_HH, SIXTEENTH, 95, channel=CH)
                    else:
                        vel = 95 if (note_idx % 4 == 0) else 75
                        add_note(hat_track, CLOSED_HH, SIXTEENTH, vel, channel=CH)
        elif sec == 'breakdown':
            for bar_idx in range(8):
                for note_idx in range(8):
                    vel = 70 if (note_idx % 2 == 0) else 55
                    add_note(hat_track, CLOSED_HH, EIGHTH, vel, channel=CH)
    mid.tracks.append(hat_track)

    # =========================================================================
    # Track 11: Drums - FX (ch10, notes 49+57)
    # =========================================================================
    fx_drum_track = mido.MidiTrack()
    fx_drum_track.append(mido.MetaMessage('track_name', name='Drums - FX', time=0))
    for sec in sections:
        if sec == 'build':
            add_rest(fx_drum_track, BAR * 8, channel=CH)
        elif sec == 'drop1':
            # Crash every 2 bars
            add_note(fx_drum_track, CRASH, QUARTER, 127, channel=CH)
            add_rest(fx_drum_track, BAR * 2 - QUARTER, channel=CH)
            add_note(fx_drum_track, CRASH, QUARTER, 120, channel=CH)
            add_rest(fx_drum_track, BAR * 2 - QUARTER, channel=CH)
            add_note(fx_drum_track, CRASH, QUARTER, 120, channel=CH)
            add_rest(fx_drum_track, BAR * 2 - QUARTER, channel=CH)
            add_note(fx_drum_track, CRASH, QUARTER, 115, channel=CH)
            add_rest(fx_drum_track, BAR - QUARTER, channel=CH)
            # Splash fill last bar
            add_note(fx_drum_track, SPLASH, EIGHTH, 100, channel=CH)
            add_rest(fx_drum_track, EIGHTH, channel=CH)
            add_note(fx_drum_track, SPLASH, EIGHTH, 105, channel=CH)
            add_rest(fx_drum_track, EIGHTH, channel=CH)
            add_note(fx_drum_track, SPLASH, EIGHTH, 110, channel=CH)
            add_rest(fx_drum_track, EIGHTH + QUARTER, channel=CH)
        elif sec == 'drop2':
            # More crashes for energy
            for bar_idx in range(7):
                if bar_idx % 2 == 0:
                    add_note(fx_drum_track, CRASH, QUARTER, 125, channel=CH)
                else:
                    add_note(fx_drum_track, SPLASH, QUARTER, 105, channel=CH)
                add_rest(fx_drum_track, BAR - QUARTER, channel=CH)
            # Final bar: splash fill + crash
            add_note(fx_drum_track, SPLASH, SIXTEENTH, 100, channel=CH)
            add_note(fx_drum_track, SPLASH, SIXTEENTH, 105, channel=CH)
            add_note(fx_drum_track, SPLASH, SIXTEENTH, 110, channel=CH)
            add_note(fx_drum_track, SPLASH, SIXTEENTH, 115, channel=CH)
            add_note(fx_drum_track, CRASH, QUARTER, 127, channel=CH)
            add_rest(fx_drum_track, BAR - QUARTER - SIXTEENTH * 4, channel=CH)
        elif sec == 'breakdown':
            add_note(fx_drum_track, CRASH, QUARTER, 90, channel=CH)
            add_rest(fx_drum_track, BAR * 8 - QUARTER, channel=CH)
    mid.tracks.append(fx_drum_track)

    # =========================================================================
    # Track 12: FX Riser (program 99, channel 7)
    # =========================================================================
    riser_track = mido.MidiTrack()
    riser_track.append(mido.MetaMessage('track_name', name='FX Riser', time=0))
    riser_track.append(mido.Message('program_change', program=99, channel=7, time=0))
    for sec in sections:
        if sec == 'build':
            # Riser builds over last 4 bars
            add_rest(riser_track, BAR * 4, channel=7)
            add_note(riser_track, n('F#3'), BAR * 2, 60, channel=7)
            add_note(riser_track, n('A3'), BAR, 80, channel=7)
            add_note(riser_track, n('C#4'), HALF, 100, channel=7)
            add_note(riser_track, n('E4'), QUARTER, 110, channel=7)
            add_note(riser_track, n('F#4'), QUARTER, 120, channel=7)
        elif sec == 'breakdown':
            # Riser in last 4 bars before Drop 2
            add_rest(riser_track, BAR * 4, channel=7)
            add_note(riser_track, n('F#3'), BAR * 2, 55, channel=7)
            add_note(riser_track, n('A3'), BAR, 75, channel=7)
            add_note(riser_track, n('C#4'), HALF, 95, channel=7)
            add_note(riser_track, n('E4'), QUARTER, 110, channel=7)
            add_note(riser_track, n('F#4'), QUARTER, 125, channel=7)
        else:
            add_rest(riser_track, BAR * 8, channel=7)
    mid.tracks.append(riser_track)

    # =========================================================================
    # SAVE
    # =========================================================================
    output_path = '/Users/scottmeyer/projects/fcp-midi/tmp/mario/voltage_drop_python.mid'
    mid.save(output_path)
    print(f"Saved: {output_path}")

    # =========================================================================
    # STATS
    # =========================================================================
    total_events = sum(len(t) for t in mid.tracks)
    total_notes = 0
    for t in mid.tracks:
        for msg in t:
            if hasattr(msg, 'type') and msg.type == 'note_on' and msg.velocity > 0:
                total_notes += 1

    total_ticks = BAR * 32  # 32 bars
    duration_seconds = mido.tick2second(total_ticks, TICKS_PER_BEAT, TEMPO)

    print(f"\n{'='*50}")
    print(f"  VOLTAGE DROP")
    print(f"{'='*50}")
    print(f"  Tracks:         {len(mid.tracks)} (1 meta + {len(mid.tracks) - 1} instruments)")
    print(f"  Total events:   {total_events}")
    print(f"  Total notes:    {total_notes}")
    print(f"  Tempo:          {BPM} BPM")
    print(f"  Key:            F# minor")
    print(f"  Ticks/beat:     {TICKS_PER_BEAT}")
    print(f"  Duration:       {duration_seconds:.1f}s ({duration_seconds / 60:.1f} min)")
    print(f"  Bars:           32 (8+8+8+8)")
    print(f"{'='*50}")
    print(f"\n  Track listing:")
    for i, t in enumerate(mid.tracks):
        name = "?"
        note_count = 0
        for msg in t:
            if hasattr(msg, 'name'):
                name = msg.name
            if hasattr(msg, 'type') and msg.type == 'note_on' and msg.velocity > 0:
                note_count += 1
        print(f"    {i:2d}. {name:<25s} ({note_count:4d} notes)")
    print()


if __name__ == '__main__':
    create_voltage_drop()
