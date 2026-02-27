# Voltage Drop — MIDI FCP Recreation Prompt

Paste this prompt into a new session with the MIDI FCP server connected.

---

## Prompt

Create a drum and bass / electronica track called **"Voltage Drop"** using the MIDI FCP tools. The track should be ~30 seconds, in **E minor**, with tempo acceleration and a signature DROP. Full creative control — here's the blueprint:

### Song Setup
```
midi_session('new "Voltage Drop" tempo:140 time-sig:4/4 key:E-minor')
```

### Tracks (5)
| Track | Instrument | Channel | Role |
|-------|-----------|---------|------|
| Drums | standard-kit | 10 | Breakbeats, hi-hats, snare rolls |
| Bass | synth-bass-1 | 1 | Sub-bass (E1/B1/D2) |
| Lead | lead-1-square | 4 | Arpeggios + riff |
| Pad | pad-2-warm | 2 | Sustained chord wash |
| Stabs | brass-section | 3 | Syncopated chord hits |

### Tempo Map (accelerating energy)
- **140 BPM** — Bars 1-6 (INTRO)
- **155 BPM** — Bars 7-10 (BUILD)
- **174 BPM** — Bars 11-20 (DROP + OUTRO)

Set tempos: `tempo 155 at:7.1`, `tempo 174 at:11.1`

### Structure & Markers
Place markers at: INTRO@1.1, BUILD@7.1, DROP@11.1, OUTRO@19.1

### Section Details

**INTRO (Bars 1-6, 140 BPM)** — Atmospheric, mysterious
- **Pad**: Em chord (whole notes) bars 1-3, Am chord bars 4-6, vel:60-70
- **Drums**: Eighth-note closed hi-hats (midi:42) only, vel:35 alternating accents
- **Lead**: Enters bar 3. Sixteenth-note arpeggio: E4→G4→B4→E5 repeating pattern. Apply crescendo from vel:45 to vel:75 across bars 3-6
- **Bass**: Silent (builds anticipation)
- **Stabs**: Silent

**BUILD (Bars 7-10, 155 BPM)** — Tension escalation
- **Drums**: Full kit enters — kick (midi:36) on beats 1+3, snare (midi:38) on 2+4, sixteenth hi-hats. Bars 9-10: snare roll (sixteenth snares) with crescendo 55→100
- **Bass**: Teaser notes only — E2 on bar 7 beat 1, B1 on bar 8 beat 1 (half notes, vel:70-80)
- **Lead**: Continue arpeggio, transpose +5 semitones (bars 7-8), then +2 (bars 9-10). Crescendo 60→100
- **Pad**: Am chord bars 7-8, Em chord bars 9-10, vel:70-80
- **Stabs**: Silent (save for the DROP)

**DROP (Bars 11-18, 174 BPM)** — Maximum energy, the payoff
- **Drums**: DnB breakbeat — kick on 1 and &2 (the 2-step), snare on 2 and 4, eighth-note hi-hats. Crash cymbal (midi:49) on bar 11 beat 1 and bar 15 beat 1. Bars 15-18: add extra kick on beat 3 for drive. Open hi-hat (midi:46) accents on &4 of bars 14 and 18
- **Bass**: Heavy sub-bass pattern — E1 on beat 1, E1 on &2, B1 on beat 3, E1 on &4 (eighth notes, vel:110-120). Bars 13-14: D2 replaces B1 on beat 3. Bars 15-18: more aggressive — add G1 sixteenth ghost notes, B0 on beat 3. Bars 17-18: ascending line E1→D2→B1→E1 / E1→D2→G1→E1
- **Pad**: Em whole notes bars 11-14, Am bars 15-16, Em bars 17-18, vel:90-100
- **Stabs**: Syncopated brass chord stabs — Em chords on beat 1 and &2 (eighth notes, vel:95-115). Am chords bars 15-16. Bar 18: stab on beat 3 instead of &2 for variation
- **Lead**: Aggressive sixteenth-note riff. Bars 11-14: E5-E4-B4-E5 / G4-E5-E4-B4 pattern, vel:90-110. Bars 15-18: push higher with G5 and B5, vel:95-120

**OUTRO (Bars 19-20, 174 BPM)** — Quick wind-down
- **Drums**: Bar 19: crash + kick on 1, snare on 2, decaying hi-hats, open hat on &4. Bar 20: single kick on 1, snare on 2, crash ring-out (whole note)
- **Bass**: E1 half notes bar 19 (vel:110→90), E1 whole note bar 20 (vel:70)
- **Pad**: Em whole notes, vel:80→60 (fade)
- **Stabs**: Single Em stab on bar 19 beat 1 (vel:100), then silent
- **Lead**: Descending quarter notes E5→B4→G4→E4 (bar 19, vel:95→65), sustained E4 whole note (bar 20, vel:50)

### Production Tips
- Use `copy @track:Drums @range:M.B-M.B to:N.B` to replicate drum patterns efficiently
- Use `crescendo` for build sections and fade-outs
- Use `transpose` to shift the lead arpeggio between sections
- The DROP's power comes from: tempo jump to 174, all 5 tracks hitting simultaneously, crash cymbal, and the sub-bass entering at full force
- Total target: ~700+ notes, 20 bars, ~30 seconds

### Save
```
midi_session('save as:./voltage_drop.mid')
```
