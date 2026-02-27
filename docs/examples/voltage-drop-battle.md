# Voltage Drop — Agent Battle

A comparative test where two agents were given the same detailed EDM composition prompt to create a drum and bass track called "Voltage Drop."

## The Prompt

Both agents received the same blueprint: a 20-bar, ~30-second DnB track in E minor with tempo acceleration (140->155->174 BPM), 5 tracks (Drums, Bass, Lead, Pad, Stabs), and detailed per-section instructions including specific notes, velocities, and dynamics.

See [voltage_drop_prompt.md](voltage_drop_prompt.md) for the full prompt.

## Agent A — FCP (verb-based DSL)

Used the fcp-midi MCP tools — verb-based DSL with operations like `note`, `chord`, `crescendo`, `tempo`, `copy @track...`. The agent thinks in musical intent: sections, dynamics, and ranges.

**Output:** `voltage_drop_fcp.mid` — 12 tracks, 1,674 notes, 87.3s, 12,402 bytes

Instruments: Trumpet (117 notes), Acoustic Guitar (336), Acoustic Bass (128), Alto Sax (75), String Ensemble (96), Vibraphone (96), Flute (82), Drums (720 across 4 drum tracks), Orchestral Harp (24). Tempo: 145 BPM.

## Agent B — Raw Python

No tooling — wrote ~689 lines of raw mido/pretty-midi code. Manual tick calculation, nested loops for every bar/beat, explicit note-on/note-off events.

**Output:** `voltage_drop_python.mid` — 13 tracks, 694 notes, 144.2s, 7,848 bytes

Instruments: Muted Trumpet (36), Acoustic Grand Piano (89), Acoustic Bass (68), Tenor Sax (34), String Ensemble (32), Flute (12), Vibraphone (95), Drums (308 across 4 drum tracks), Acoustic Guitar (10), Contrabass (10). Tempos: 68/64/66/60/52 BPM.

**Script:** [voltage_drop_script.py](voltage_drop_script.py) (the raw Python code)

## Results

Both produced valid MIDI. FCP output was richer — more notes, more instrument detail, and denser arrangement. The raw version was longer in duration but sparser, requiring significantly more code to express the same musical intent.

| Metric | FCP | Raw Python |
|--------|-----|------------|
| File size | 12,402 bytes | 7,848 bytes |
| Track count | 12 | 13 |
| Note count | 1,674 | 694 |
| Duration | 87.3s | 144.2s |
| Code required | ~50 DSL ops | ~689 lines Python |

The FCP agent worked at the level of "create a crescendo from vel 45->75 across bars 3-6" while the raw agent worked at the level of "place note_on events with linearly interpolated velocity values in a nested loop."

## Original FCP Session

The original prompt session also produced `voltage_drop.mid` (5 tracks, 721 notes, 30.3s at 140 BPM) — a more faithful rendition of the DnB blueprint with Drums, Synth Bass, Pad, Brass Stabs, and Square Lead.

## Remixes

A "Nocturne" jazz/noir transformation was also produced: [voltage_drop_remix.py](voltage_drop_remix.py)

## Key Takeaway

FCP lets the LLM think in the domain (music) rather than the encoding (MIDI bytes) — the React:DOM analogy in action.
