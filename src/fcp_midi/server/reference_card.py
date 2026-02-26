"""MIDI FCP reference card — comprehensive help text for the protocol."""

REFERENCE_CARD = """\
# MIDI FCP Reference Card

## Mutation Operations (via `midi` tool)

### Track Management
  track add NAME instrument:INSTRUMENT [ch:N]
  track remove NAME

### Notes & Chords
  note TRACK PITCH at:POS dur:DUR [vel:V] [ch:N]
  chord TRACK SYMBOL at:POS dur:DUR [vel:V] [ch:N]

### Controllers & Pitch Bend
  cc TRACK CC_NAME VALUE at:POS [ch:N]
  bend TRACK VALUE at:POS [ch:N]

### Tempo, Time & Key
  tempo BPM [at:POS]
  time-sig N/D [at:POS]
  key-sig KEY-MODE [at:POS]

### Markers & Title
  marker TEXT at:POS
  title TEXT

### Editing (selector-based)
  remove SELECTORS
  move SELECTORS to:POS
  copy SELECTORS to:POS
  transpose SELECTORS SEMITONES
  velocity SELECTORS DELTA
  quantize SELECTORS grid:DUR

### Track State
  mute TRACK
  solo TRACK
  program TRACK INSTRUMENT [at:POS]

## Selectors
  @track:NAME        Notes on a specific track
  @channel:N         Notes on MIDI channel N
  @range:M.B-M.B    Notes in a measure.beat range
  @pitch:PITCH       Notes matching a pitch (e.g. C4)
  @velocity:N-M      Notes with velocity in range
  @all               All notes in the song
  @recent            Last event from the log
  @recent:N          Last N events from the log

  Combine selectors to intersect: @track:Piano @range:1.1-4.4

## Position Syntax
  M.B                Measure.Beat (1-based): 1.1 = start
  M.B.T              With tick offset: 1.1.120
  tick:N             Raw absolute tick

## Duration Syntax
  whole, half, quarter, eighth, sixteenth, 32nd
  1n, 2n, 4n, 8n, 16n, 32n
  dotted-quarter, triplet-eighth
  ticks:N            Raw tick count

## Pitch Syntax
  C4, D#5, Bb3       Note + accidental + octave
  midi:60            Raw MIDI number (60 = middle C)

## Chord Symbols
  Cmaj, Am, Dm7, G7, Bdim, Faug, Csus4, Asus2
  Cmaj7, Am7, Dm7b5, G9, Cm6, Cadd9
  Dm/F               Slash chord (inversion)

## Velocity Syntax
  0-127              Numeric value
  ppp, pp, p, mp, mf, f, ff, fff   Dynamic names

## CC Names
  volume, pan, modulation, expression, sustain,
  reverb, chorus, brightness, portamento, breath

## Query Commands (via `midi_query` tool)
  map                Song overview
  tracks             List all tracks
  events TRACK [M.B-M.B]  Events on a track
  describe TRACK     Detailed track info
  stats              Song statistics
  status             Session status
  find PITCH         Search notes by pitch
  piano-roll TRACK M.B-M.B  ASCII visualization
  history N          Recent N events from log
  diff checkpoint:NAME  Events since checkpoint

## Session Actions (via `midi_session` tool)
  new "Title" [tempo:N] [time-sig:N/D] [key:K] [ppqn:N]
  open ./file.mid
  save
  save as:./path.mid
  checkpoint NAME
  undo [to:NAME]
  redo

## GM Instruments (examples)
  acoustic-grand-piano, electric-piano-1, vibraphone
  acoustic-guitar-nylon, electric-bass-finger, violin
  trumpet, alto-sax, flute, string-ensemble-1

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
  8. midi_session('save as:./my-song.mid')
"""
