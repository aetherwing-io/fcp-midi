# FCP-MIDI Examples

## Super Mario Bros

Classic game theme — a showcase of multi-track MIDI composition.

| Property | Value |
|----------|-------|
| File | `super_mario_bros.mid` |
| Duration | 16.0s |
| Tracks | 4 |
| Notes | 288 |
| Tempo | 180 BPM |
| Instruments | Lead 1/square (x2), Synth Bass 1, Drums |

## Voltage Drop — Agent Battle

A comparative test of FCP vs raw Python for EDM composition. See [voltage-drop-battle.md](voltage-drop-battle.md) for the full writeup.

### Files

| File | Description | Size | Tracks | Notes | Duration |
|------|-------------|------|--------|-------|----------|
| `voltage_drop.mid` | FCP output (original session) | 4,728 bytes | 5 | 721 | 30.3s |
| `voltage_drop_fcp.mid` | FCP output (battle version) | 12,402 bytes | 12 | 1,674 | 87.3s |
| `voltage_drop_python.mid` | Raw Python output | 7,848 bytes | 13 | 694 | 144.2s |
| `voltage_drop_prompt.md` | The composition prompt | -- | -- | -- | -- |
| `voltage_drop_script.py` | Raw Python approach (~689 lines) | -- | -- | -- | -- |
| `voltage_drop_remix.py` | Nocturne remix stub | -- | -- | -- | -- |
