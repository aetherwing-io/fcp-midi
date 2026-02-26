"""
Full orchestral rendition of "Happy Birthday to You" in F major, 3/4 time.
Uses pretty_midi directly to construct the MIDI file from scratch.
"""

import pretty_midi
import os

# === Constants ===
TEMPO = 100.0
BEAT = 60.0 / TEMPO  # 0.6 seconds per beat
MEASURE = BEAT * 3    # 1.8 seconds per measure

# MIDI note numbers
C4 = 60
D4 = 62
E4 = 64
F4 = 65
G4 = 67
A4 = 69
Bb4 = 70
B4 = 71
C5 = 72
D5 = 74
E5 = 76
F5 = 77

# Lower octave
C3 = 48
D3 = 50
E3 = 52
F3 = 53
G3 = 55
A3 = 57
Bb3 = 58
C2 = 36
D2 = 38
E2 = 40
F2 = 41
G2 = 43
A2 = 45
Bb2 = 46

# Percussion
OPEN_TRIANGLE = 81
CLOSED_TRIANGLE = 80
TAMBOURINE = 54
RIDE_CYMBAL = 51

# GM Programs (0-indexed)
PROG_PIANO = 0
PROG_BASS = 32
PROG_STRINGS = 48
PROG_FRENCH_HORN = 60
PROG_CLARINET = 71
PROG_FLUTE = 73


def add_note(instrument, pitch, start, end, velocity=80):
    """Add a note to an instrument, clamping velocity to valid range."""
    vel = max(1, min(127, int(velocity)))
    note = pretty_midi.Note(velocity=vel, pitch=pitch, start=start, end=end)
    instrument.notes.append(note)


def beat_time(measure, beat):
    """Convert measure number (0-indexed) and beat (0-indexed) to seconds.

    Measure 0 is the pickup measure. The piece starts with a pickup on beats 1-2
    (0-indexed) of measure 0.
    """
    return measure * MEASURE + beat * BEAT


# === Create PrettyMIDI object ===
pm = pretty_midi.PrettyMIDI(initial_tempo=TEMPO, resolution=480)
pm.time_signature_changes.append(pretty_midi.TimeSignature(3, 4, 0.0))

# === Create Instruments ===
flute = pretty_midi.Instrument(program=PROG_FLUTE, name='Flute')
clarinet = pretty_midi.Instrument(program=PROG_CLARINET, name='Clarinet')
piano = pretty_midi.Instrument(program=PROG_PIANO, name='Piano')
strings = pretty_midi.Instrument(program=PROG_STRINGS, name='Strings')
bass = pretty_midi.Instrument(program=PROG_BASS, name='Bass')
french_horn = pretty_midi.Instrument(program=PROG_FRENCH_HORN, name='French Horn')
drums = pretty_midi.Instrument(program=0, is_drum=True, name='Percussion')


# ============================================================
# MELODY (Flute)
# ============================================================
# The melody of Happy Birthday in F major, 3/4 time.
# Each phrase starts with a pickup (anacrusis) on beats 2-3.
#
# Phrase 1: "Happy birthday to you"
#   Pickup (m0, beats 1-2): C4 C4
#   m1: D4 C4 F4
#   m2: E4 (held)
#
# Phrase 2: "Happy birthday to you"
#   Pickup (m2, beats 1-2): C4 C4
#   m3: D4 C4 G4
#   m4: F4 (held)
#
# Phrase 3: "Happy birthday dear ___"
#   Pickup (m4, beats 1-2): C4 C4
#   m5: C5 A4 F4
#   m6: E4 D4 (held)
#
# Phrase 4: "Happy birthday to you"
#   Pickup (m6, beat 1-2): Bb4 Bb4
#   m7: A4 F4 G4
#   m8: F4 (held, final)

# Dynamics per phrase
vel_p1 = 55   # phrase 1: piano
vel_p2 = 65   # phrase 2: mp
vel_p3 = 90   # phrase 3: mf-f (climax)
vel_p4 = 100  # phrase 4: forte (resolution)

melody_notes = []

# --- Phrase 1: "Happy birthday to you" ---
# Pickup: two eighth-note-ish C4s on beats 2 and 2.5 of measure 0
melody_notes.append((C4, beat_time(0, 1.5), beat_time(0, 2.0), vel_p1))
melody_notes.append((C4, beat_time(0, 2.0), beat_time(0, 2.75), vel_p1))
# Bar 1: D4 (beat 0, dotted quarter), C4 (beat 1.5), F4 (beat 2)
melody_notes.append((D4, beat_time(1, 0), beat_time(1, 1.5), vel_p1))
melody_notes.append((C4, beat_time(1, 1.5), beat_time(1, 2.0), vel_p1))
melody_notes.append((F4, beat_time(1, 2.0), beat_time(2, 0), vel_p1))
# Bar 2: E4 (held whole bar)
melody_notes.append((E4, beat_time(2, 0), beat_time(2, 1.5), vel_p1))

# --- Phrase 2: "Happy birthday to you" ---
# Pickup: beats 1.5-2 and 2-2.75 of measure 2
melody_notes.append((C4, beat_time(2, 1.5), beat_time(2, 2.0), vel_p2))
melody_notes.append((C4, beat_time(2, 2.0), beat_time(2, 2.75), vel_p2))
# Bar 3: D4, C4, G4
melody_notes.append((D4, beat_time(3, 0), beat_time(3, 1.5), vel_p2))
melody_notes.append((C4, beat_time(3, 1.5), beat_time(3, 2.0), vel_p2))
melody_notes.append((G4, beat_time(3, 2.0), beat_time(4, 0), vel_p2))
# Bar 4: F4 (held)
melody_notes.append((F4, beat_time(4, 0), beat_time(4, 1.5), vel_p2))

# --- Phrase 3: "Happy birthday dear ___" ---
# Pickup: beats 1.5-2 and 2-2.75 of measure 4
melody_notes.append((C4, beat_time(4, 1.5), beat_time(4, 2.0), vel_p3))
melody_notes.append((C4, beat_time(4, 2.0), beat_time(4, 2.75), vel_p3))
# Bar 5: C5, A4, F4
melody_notes.append((C5, beat_time(5, 0), beat_time(5, 1.5), vel_p3))
melody_notes.append((A4, beat_time(5, 1.5), beat_time(5, 2.0), vel_p3))
melody_notes.append((F4, beat_time(5, 2.0), beat_time(6, 0), vel_p3))
# Bar 6: E4, D4 (held)
melody_notes.append((E4, beat_time(6, 0), beat_time(6, 1.0), vel_p3))
melody_notes.append((D4, beat_time(6, 1.0), beat_time(6, 1.5), vel_p3))

# --- Phrase 4: "Happy birthday to you" ---
# Pickup: beats 1.5-2 and 2-2.75 of measure 6
melody_notes.append((Bb4, beat_time(6, 1.5), beat_time(6, 2.0), vel_p4))
melody_notes.append((Bb4, beat_time(6, 2.0), beat_time(6, 2.75), vel_p4))
# Bar 7: A4, F4, G4
melody_notes.append((A4, beat_time(7, 0), beat_time(7, 1.5), vel_p4))
melody_notes.append((F4, beat_time(7, 1.5), beat_time(7, 2.0), vel_p4))
melody_notes.append((G4, beat_time(7, 2.0), beat_time(8, 0), vel_p4))
# Bar 8: F4 (held, final with fermata-like extension)
melody_notes.append((F4, beat_time(8, 0), beat_time(8, 2.5), vel_p4))

for pitch, start, end, vel in melody_notes:
    add_note(flute, pitch, start, end, vel)


# ============================================================
# HARMONY (Clarinet) — enters at phrase 2, harmonizes below/above
# ============================================================
# Generally a third below the melody, or a sixth above for variety.

harmony_notes = []

# --- Phrase 2 harmony (a third below melody) ---
harmony_notes.append((A3, beat_time(2, 1.5), beat_time(2, 2.0), vel_p2 - 10))
harmony_notes.append((A3, beat_time(2, 2.0), beat_time(2, 2.75), vel_p2 - 10))
harmony_notes.append((Bb3, beat_time(3, 0), beat_time(3, 1.5), vel_p2 - 10))
harmony_notes.append((A3, beat_time(3, 1.5), beat_time(3, 2.0), vel_p2 - 10))
harmony_notes.append((E4, beat_time(3, 2.0), beat_time(4, 0), vel_p2 - 10))
harmony_notes.append((C4, beat_time(4, 0), beat_time(4, 1.5), vel_p2 - 10))

# --- Phrase 3 harmony (a third/sixth below) ---
harmony_notes.append((A3, beat_time(4, 1.5), beat_time(4, 2.0), vel_p3 - 10))
harmony_notes.append((A3, beat_time(4, 2.0), beat_time(4, 2.75), vel_p3 - 10))
harmony_notes.append((A4, beat_time(5, 0), beat_time(5, 1.5), vel_p3 - 10))
harmony_notes.append((F4, beat_time(5, 1.5), beat_time(5, 2.0), vel_p3 - 10))
harmony_notes.append((C4, beat_time(5, 2.0), beat_time(6, 0), vel_p3 - 10))
harmony_notes.append((C4, beat_time(6, 0), beat_time(6, 1.0), vel_p3 - 10))
harmony_notes.append((Bb3, beat_time(6, 1.0), beat_time(6, 1.5), vel_p3 - 10))

# --- Phrase 4 harmony (a third below) ---
harmony_notes.append((G4, beat_time(6, 1.5), beat_time(6, 2.0), vel_p4 - 10))
harmony_notes.append((G4, beat_time(6, 2.0), beat_time(6, 2.75), vel_p4 - 10))
harmony_notes.append((F4, beat_time(7, 0), beat_time(7, 1.5), vel_p4 - 10))
harmony_notes.append((C4, beat_time(7, 1.5), beat_time(7, 2.0), vel_p4 - 10))
harmony_notes.append((E4, beat_time(7, 2.0), beat_time(8, 0), vel_p4 - 10))
harmony_notes.append((C4, beat_time(8, 0), beat_time(8, 2.5), vel_p4 - 10))

for pitch, start, end, vel in harmony_notes:
    add_note(clarinet, pitch, start, end, vel)


# ============================================================
# PIANO — Waltz pattern: bass on beat 1, chord on beats 2 and 3
# ============================================================
# Chords in F major:
#   I  = F major: F3, A3-C4-F4
#   IV = Bb major: Bb2, Bb3-D4-F4
#   V  = C major (or C7): C3, C4-E4-G4 (or Bb3-C4-E4)
#   vi = Dm: D3, D4-F4-A4

# Chord progression per measure:
# m0 (pickup): just last two beats, I chord
# m1: I (F)
# m2: I (F) -> transition
# m3: V (C or C7)
# m4: I (F)
# m5: IV (Bb) -> vi? Actually let's do: IV then I
# m6: IV (Bb) -> V (C7)
# m7: V (C7) -> I
# m8: I (F) final

# Define chord voicings: (bass_note, [chord_notes])
I_chord = (F2, [A3, C4, F4])
IV_chord = (Bb2, [Bb3, D4, F4])
V_chord = (C3, [Bb3, C4, E4])  # C7 for dominant pull
V_simple = (C3, [C4, E4, G4])
vi_chord = (D3, [D4, F4, A4])
ii_chord = (G2, [Bb3, D4, G4])  # Gm for ii

# Measure chord assignments
measure_chords = {
    0: I_chord,     # pickup
    1: I_chord,     # "birthday to you"
    2: I_chord,     # held E4
    3: V_chord,     # "birthday to you" (V)
    4: I_chord,     # held F4
    5: IV_chord,    # "birthday dear" (IV, climax start)
    6: V_chord,     # "___" (V7, tension)
    7: V_simple,    # "birthday to you" (V resolving)
    8: I_chord,     # final F (I, resolution)
}

# Dynamics for piano per measure
piano_dynamics = {
    0: 40, 1: 45, 2: 50, 3: 55, 4: 60, 5: 75, 6: 80, 7: 85, 8: 90
}

for m in range(9):
    bass_pitch, chord_pitches = measure_chords[m]
    vel = piano_dynamics[m]

    if m == 0:
        # Pickup measure: only beats 1-2
        # Light chord on beats 1 and 2
        for cp in chord_pitches:
            add_note(piano, cp, beat_time(0, 1), beat_time(0, 1.8), vel - 15)
        for cp in chord_pitches:
            add_note(piano, cp, beat_time(0, 2), beat_time(0, 2.8), vel - 15)
        continue

    if m == 8:
        # Final measure: full chord on beat 1, let ring
        add_note(piano, bass_pitch, beat_time(m, 0), beat_time(m, 2.5), vel)
        for cp in chord_pitches:
            add_note(piano, cp, beat_time(m, 0), beat_time(m, 2.5), vel)
        continue

    # Standard waltz: bass on 1, chord on 2 and 3
    # Beat 1: bass note (oom)
    add_note(piano, bass_pitch, beat_time(m, 0), beat_time(m, 0.9), vel)

    # Beat 2: chord (pah)
    for cp in chord_pitches:
        add_note(piano, cp, beat_time(m, 1), beat_time(m, 1.8), vel - 10)

    # Beat 3: chord (pah)
    for cp in chord_pitches:
        add_note(piano, cp, beat_time(m, 2), beat_time(m, 2.8), vel - 10)


# ============================================================
# STRINGS — Sustained chord pads, soft throughout
# ============================================================
# Strings play long sustained chords, changing with the harmony.
# Each chord spans the full measure (or two).

# String voicings (slightly different register from piano)
string_chords = {
    'I':   [F3, A3, C4, F4],
    'IV':  [F3, Bb3, D4, F4],
    'V':   [E3, G3, C4, E4],
    'V7':  [E3, Bb3, C4, E4],
    'vi':  [D3, F3, A3, D4],
}

# Map measures to string chord names
measure_string_chords = {
    0: 'I', 1: 'I', 2: 'I', 3: 'V', 4: 'I',
    5: 'IV', 6: 'V7', 7: 'V', 8: 'I'
}

string_dynamics = {
    0: 35, 1: 40, 2: 40, 3: 45, 4: 50, 5: 65, 6: 70, 7: 75, 8: 80
}

for m in range(9):
    chord_name = measure_string_chords[m]
    pitches = string_chords[chord_name]
    vel = string_dynamics[m]

    if m == 0:
        # Pickup: start at beat 1
        start = beat_time(0, 1)
        end = beat_time(1, 0)
    elif m == 8:
        # Final: let ring with fermata
        start = beat_time(8, 0)
        end = beat_time(8, 2.8)
    else:
        start = beat_time(m, 0)
        end = beat_time(m + 1, 0)

    for p in pitches:
        add_note(strings, p, start, end, vel)


# ============================================================
# BASS — Waltz "oom" on beat 1 of each measure
# ============================================================
bass_notes_map = {
    1: F2, 2: F2, 3: C3, 4: F2,
    5: Bb2, 6: C3, 7: C3, 8: F2
}

bass_dynamics = {
    1: 50, 2: 50, 3: 55, 4: 55, 5: 70, 6: 75, 7: 80, 8: 85
}

for m in range(1, 9):
    pitch = bass_notes_map[m]
    vel = bass_dynamics[m]

    if m == 8:
        # Final: longer bass note
        add_note(bass, pitch, beat_time(m, 0), beat_time(m, 2.5), vel)
        # Add the octave below for richness
        add_note(bass, pitch - 12, beat_time(m, 0), beat_time(m, 2.5), vel - 15)
    else:
        # Standard: beat 1 with some sustain
        add_note(bass, pitch, beat_time(m, 0), beat_time(m, 1.5), vel)
        # Add a lighter note on beat 3 for movement in some measures
        if m in [1, 3, 5, 7]:
            add_note(bass, pitch, beat_time(m, 2), beat_time(m, 2.8), vel - 20)


# ============================================================
# FRENCH HORN — Enters at phrase 3 (climax), punctuation
# ============================================================
# Bars 5-8: the "Happy birthday dear ___" climax and resolution.
# Horn plays sustained notes on key beats, adding warmth and weight.

horn_notes = []

# Bar 5 (m5): IV chord — horn plays Bb3 and F4 (root and fifth of Bb)
horn_notes.append((Bb3, beat_time(5, 0), beat_time(5, 2.5), 75))
horn_notes.append((F4, beat_time(5, 0), beat_time(5, 2.5), 65))

# Bar 6 (m6): V7 — horn plays C4 and E4
horn_notes.append((C4, beat_time(6, 0), beat_time(6, 1.5), 80))
horn_notes.append((E4, beat_time(6, 0), beat_time(6, 1.5), 70))

# Bar 7 (m7): V resolving — horn plays G3 and C4
horn_notes.append((G3, beat_time(7, 0), beat_time(7, 2.8), 85))
horn_notes.append((C4, beat_time(7, 0), beat_time(7, 2.8), 75))

# Bar 8 (m8): I final — horn plays F3 and C4, triumphant
horn_notes.append((F3, beat_time(8, 0), beat_time(8, 2.5), 90))
horn_notes.append((C4, beat_time(8, 0), beat_time(8, 2.5), 80))
horn_notes.append((F4, beat_time(8, 0), beat_time(8, 2.5), 70))

for pitch, start, end, vel in horn_notes:
    add_note(french_horn, pitch, start, end, vel)


# ============================================================
# PERCUSSION — Light triangle hits, tambourine accents
# ============================================================
# Triangle on beat 1 of each full measure.
# Tambourine added in the climactic section (bars 5-8).

for m in range(1, 9):
    # Dynamics ramp
    if m <= 2:
        vel = 35
    elif m <= 4:
        vel = 45
    elif m <= 6:
        vel = 60
    else:
        vel = 70

    # Triangle on beat 1
    add_note(drums, OPEN_TRIANGLE, beat_time(m, 0), beat_time(m, 0.3), vel)

    # Tambourine on beats 2 and 3 for measures 5-8 (climax and resolution)
    if m >= 5:
        add_note(drums, TAMBOURINE, beat_time(m, 1), beat_time(m, 1.2), vel - 20)
        add_note(drums, TAMBOURINE, beat_time(m, 2), beat_time(m, 2.2), vel - 20)

    # Closed triangle on beat 3 for gentle timekeeping (earlier measures)
    if m < 5:
        add_note(drums, CLOSED_TRIANGLE, beat_time(m, 2), beat_time(m, 2.2), vel - 15)


# ============================================================
# Assemble and write
# ============================================================
pm.instruments.append(flute)
pm.instruments.append(clarinet)
pm.instruments.append(piano)
pm.instruments.append(strings)
pm.instruments.append(bass)
pm.instruments.append(french_horn)
pm.instruments.append(drums)

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'happy_birthday_raw.mid')
pm.write(output_path)

# === Summary ===
print("=" * 60)
print("  HAPPY BIRTHDAY - Full Orchestral Arrangement")
print("=" * 60)
print(f"  Output file: {output_path}")
print(f"  File size:   {os.path.getsize(output_path)} bytes")
print(f"  Tempo:       {TEMPO} BPM")
print(f"  Time sig:    3/4 (waltz)")
print(f"  Key:         F major")
print(f"  Duration:    ~{beat_time(8, 3):.1f} seconds ({beat_time(8,3)/MEASURE:.0f} measures)")
print(f"  Tracks:      {len(pm.instruments)}")
print("-" * 60)
for inst in pm.instruments:
    drum_label = " [DRUM]" if inst.is_drum else ""
    prog_label = f" (GM {inst.program})" if not inst.is_drum else ""
    print(f"  {inst.name:15s}{prog_label}{drum_label}: {len(inst.notes):3d} notes")
print("-" * 60)
total_notes = sum(len(inst.notes) for inst in pm.instruments)
print(f"  Total notes: {total_notes}")
print("=" * 60)
print("\nDone! Open happy_birthday_raw.mid in any MIDI player.")
