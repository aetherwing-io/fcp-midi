# Tracker Format v2 Enhancements

## Context

The tracker format was implemented in the first pass (replacing piano-roll). It works, round-trips correctly, and all 866 tests pass. But testing it revealed three enhancements worth making. This prompt covers research + implementation for all three.

## Current State

- `src/fcp_midi/server/tracker_format.py` — core format/parse/pair logic
- `src/fcp_midi/server/queries_v2.py` — `_query_tracker()` dispatches single-track queries
- `src/fcp_midi/adapter_v2.py` — block-mode import via `_start_tracker` / `_flush_tracker`
- Tests: `tests/test_tracker_format.py`, `tests/test_tracker_import.py`, updated `tests/test_queries_v2.py` and `tests/test_adapter_v2.py`

## Enhancement 1: Duration-in-steps (drop OFF events)

### Problem

OFF events double token count and create noisy lines:
```
Step 03: [C4_v0_OFF], [E4_v0_OFF], [G4_v0_OFF], [D5_v0_OFF], [C4_v95_ON], [F4_v85_ON]
```

### Change

Replace ON/OFF pair model with duration-in-token model:
```
[C4_v100_2]  →  pitch C4, velocity 100, sustain 2 steps
```

Before:
```
Step 01: [C4_v100_ON], [E4_v90_ON]
Step 03: [C4_v0_OFF], [E4_v0_OFF]
```

After:
```
Step 01: [C4_v100_2], [E4_v90_2]
```

### Impact

- `format_tracker()` — generate `[pitch_vel_dur]` tokens instead of separate ON/OFF
- `parse_event_token()` — parse new format (third field is int duration, not ON/OFF)
- `pair_tracker_events()` — simplify dramatically: no FIFO pairing needed, each token has all info
- `parse_step_line()` — no change (it delegates to parse_event_token)
- All tracker tests need updating for new token format
- Round-trip test should still pass with new format

### Research needed

- Verify the duration-in-steps model handles edge cases: notes that sustain beyond the queried range, notes shorter than 1 step (round up to 1?)
- Check if any step can have the same pitch appear twice with different durations (overlapping notes) — if so, the format handles it naturally since each token is independent

## Enhancement 2: Instrument in header

### Problem

The header shows track name but not the instrument. Knowing `Piano` is `acoustic-grand-piano` vs `electric-piano-1` matters for compositional decisions.

### Change

```
Before: [Track: Piano | Range: 1.1-4.4]
After:  [Track: Piano (acoustic-grand-piano) | Range: 1.1-4.4]
```

Also tighten resolution label: `[Resolution: 16th]` instead of `[Resolution: 16th notes]`.

### Impact

- `format_tracker()` — needs access to instrument name. Currently receives `notes, track_name, time_sigs, ppqn, start_tick, end_tick, resolution`. Needs an `instrument` param (or look it up).
- `_query_tracker()` in `queries_v2.py` — pass instrument name from `ref.program` through GM lookup
- `_resolution_label()` — simplify to just return the short name

### Research needed

- Check how `_instrument_name()` in `queries_v2.py` resolves program numbers to names. Use the same lookup.
- For the import side: the instrument in the header is informational only (the track already exists). No parsing needed.

## Enhancement 3: Multi-track combined view

### Problem

Per-track querying works for editing one voice, but composition requires seeing vertical alignment across tracks. Currently you'd need 3-4 separate queries and mental interleaving.

### Change

Support `tracker * 1.1-4.4` or `tracker Piano,Bass,Drums 1.1-4.4` for read-only combined view:
```
[Resolution: 8th]
[Tracks: Piano, Bass, Drums | Range: 1.1-2.4]
Step 01: Piano[C4_v100_4, E4_v90_4] Bass[C2_v100_8] Drums[kick_v120_1]
Step 03: Piano[G4_v80_2] Drums[hihat_v80_1]
Step 05: Drums[snare_v100_1, hihat_v80_1]
```

### Design decisions needed

- **Track selection syntax**: `*` for all, comma-separated list for specific tracks, or both?
- **Line length**: busy arrangements with 5+ tracks could make lines very long. Should there be a line-wrapping strategy? Or cap at N tracks?
- **Drum names**: on channel 10, MIDI note numbers are meaningless. Should percussion tracks use GM drum names (`kick`, `snare`, `hihat`) instead of pitch names (`C2`, `D2`, `F#2`)? Research what GM drum map looks like and whether the model already has this mapping.

### Impact

- `format_tracker()` — new code path for multi-track: accepts list of (track_name, notes) instead of single track
- `_query_tracker()` — detect `*` or comma-separated track names, gather notes from multiple tracks
- Import: stays single-track only. Multi-track output is read-only.
- New tests for multi-track output format

### Research needed

- Look at how `events *` already handles multi-track in `_query_events()` — follow the same pattern
- Check if there's an existing GM drum map in the codebase (search for drum names, percussion, channel 10 mapping)
- Determine if drum name mapping should live in tracker_format.py or be a shared utility
- Test with the actual MCP server to see if multi-track output is readable at different resolutions

## Implementation Order

1. **Enhancement 1 first** (duration-in-steps) — this changes the token format, so everything else builds on it
2. **Enhancement 2** (instrument in header) — small, independent
3. **Enhancement 3** (multi-track) — largest, depends on the final token format from #1

## Verification

After each enhancement:
- `cd fcp-midi && uv run pytest` — all tests pass
- Manual test via Python (the published MCP server won't have changes): create a model, add notes across multiple tracks, query with tracker, verify output format
- Round-trip test: format → parse → add_note → format again, verify identical output
