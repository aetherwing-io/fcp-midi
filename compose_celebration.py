#!/usr/bin/env python3
"""Phase 3: Compose "FCP Fanfare" using the MIDI FCP tools.

This script exercises the full MIDI FCP stack to compose a multi-track
celebratory piece and save it as celebration.mid — the ultimate integration test.

Composition: "FCP Fanfare"
- Tempo: 132 BPM, 4/4 time, key of C major
- Tracks: Piano, Bass, Strings, Drums
- Structure: Intro (4 bars) → Theme (8 bars) → Bridge (4 bars) → Finale (4 bars)
- Style: Triumphant fanfare, ascending motifs, building dynamics (p → ff)
"""

from fcp_midi.server.intent import IntentLayer


def main() -> None:
    intent = IntentLayer()

    # ── Session setup ──────────────────────────────────────────────
    print("Creating song...")
    print(intent.execute_session('new "FCP Fanfare" tempo:132 time-sig:4/4 key:C-major'))

    # ── Tracks ─────────────────────────────────────────────────────
    print("\nAdding tracks...")
    print("\n".join(intent.execute_ops([
        "track add Piano instrument:acoustic-grand-piano",
        "track add Bass instrument:acoustic-bass ch:2",
        "track add Strings instrument:string-ensemble-1 ch:3",
        "track add Drums instrument:standard-kit ch:10",
    ])))

    # ── Markers ────────────────────────────────────────────────────
    print("\nAdding markers...")
    print("\n".join(intent.execute_ops([
        'marker "Intro" at:1.1',
        'marker "Theme" at:5.1',
        'marker "Bridge" at:13.1',
        'marker "Finale" at:17.1',
    ])))

    print(intent.execute_session("checkpoint intro"))

    # ══════════════════════════════════════════════════════════════
    # INTRO (bars 1-4) — p, building anticipation
    # ══════════════════════════════════════════════════════════════
    print("\n=== INTRO (bars 1-4) ===")

    # Piano — ascending arpeggiated figures
    print("\n".join(intent.execute_ops([
        # Bar 1: C major arpeggio
        "note Piano C4 at:1.1 dur:eighth vel:49",
        "note Piano E4 at:1.2 dur:eighth vel:52",
        "note Piano G4 at:1.3 dur:eighth vel:55",
        "note Piano C5 at:1.4 dur:eighth vel:58",
        # Bar 2: F major arpeggio
        "note Piano F4 at:2.1 dur:eighth vel:55",
        "note Piano A4 at:2.2 dur:eighth vel:58",
        "note Piano C5 at:2.3 dur:eighth vel:60",
        "note Piano F5 at:2.4 dur:eighth vel:64",
        # Bar 3: G major arpeggio — building
        "note Piano G4 at:3.1 dur:eighth vel:60",
        "note Piano B4 at:3.2 dur:eighth vel:64",
        "note Piano D5 at:3.3 dur:eighth vel:67",
        "note Piano G5 at:3.4 dur:eighth vel:70",
        # Bar 4: Am → G suspension — tension
        "note Piano A4 at:4.1 dur:quarter vel:64",
        "note Piano E5 at:4.2 dur:quarter vel:67",
        "note Piano G4 at:4.3 dur:quarter vel:70",
        "note Piano B4 at:4.4 dur:quarter vel:75",
    ])))

    # Bass — simple whole notes
    print("\n".join(intent.execute_ops([
        "note Bass C3 at:1.1 dur:whole vel:55",
        "note Bass F3 at:2.1 dur:whole vel:55",
        "note Bass G3 at:3.1 dur:whole vel:58",
        "note Bass A3 at:4.1 dur:half vel:55",
        "note Bass G3 at:4.3 dur:half vel:58",
    ])))

    # Strings — sustained pad, entering bar 3
    print("\n".join(intent.execute_ops([
        "chord Strings Cmaj at:3.1 dur:whole vel:45",
        "chord Strings Cmaj at:4.1 dur:whole vel:52",
    ])))

    # Drums — light hi-hat, building
    print("\n".join(intent.execute_ops([
        # Bar 3: hi-hat pattern
        "note Drums midi:42 at:3.1 dur:eighth vel:40",
        "note Drums midi:42 at:3.2 dur:eighth vel:35",
        "note Drums midi:42 at:3.3 dur:eighth vel:40",
        "note Drums midi:42 at:3.4 dur:eighth vel:35",
        # Bar 4: add kick, build to theme
        "note Drums midi:42 at:4.1 dur:eighth vel:45",
        "note Drums midi:42 at:4.2 dur:eighth vel:40",
        "note Drums midi:42 at:4.3 dur:eighth vel:45",
        "note Drums midi:42 at:4.4 dur:eighth vel:50",
        "note Drums midi:36 at:4.1 dur:eighth vel:60",
        "note Drums midi:38 at:4.3 dur:eighth vel:55",
    ])))

    print(intent.execute_session("checkpoint theme-start"))

    # ══════════════════════════════════════════════════════════════
    # THEME (bars 5-12) — mf → f, triumphant melody
    # ══════════════════════════════════════════════════════════════
    print("\n=== THEME (bars 5-12) ===")

    # Piano — main melody (triumphant, ascending motifs)
    print("\n".join(intent.execute_ops([
        # Bar 5: C major fanfare motif
        "note Piano C5 at:5.1 dur:quarter vel:80",
        "note Piano E5 at:5.2 dur:quarter vel:80",
        "note Piano G5 at:5.3 dur:half vel:85",
        # Bar 6: answer phrase
        "note Piano A5 at:6.1 dur:quarter vel:85",
        "note Piano G5 at:6.2 dur:quarter vel:80",
        "note Piano E5 at:6.3 dur:quarter vel:80",
        "note Piano F5 at:6.4 dur:quarter vel:78",
        # Bar 7: ascending again
        "note Piano E5 at:7.1 dur:quarter vel:82",
        "note Piano G5 at:7.2 dur:quarter vel:85",
        "note Piano A5 at:7.3 dur:quarter vel:88",
        "note Piano B5 at:7.4 dur:quarter vel:90",
        # Bar 8: resolution to high C
        "note Piano C6 at:8.1 dur:half vel:92",
        "note Piano G5 at:8.3 dur:half vel:85",
        # Bar 9: second phrase — variation
        "note Piano C5 at:9.1 dur:eighth vel:82",
        "note Piano D5 at:9.2 dur:eighth vel:82",
        "note Piano E5 at:9.3 dur:quarter vel:85",
        "note Piano G5 at:9.4 dur:quarter vel:88",
        # Bar 10: descending response
        "note Piano F5 at:10.1 dur:quarter vel:85",
        "note Piano E5 at:10.2 dur:quarter vel:82",
        "note Piano D5 at:10.3 dur:quarter vel:80",
        "note Piano C5 at:10.4 dur:quarter vel:78",
        # Bar 11: building climax
        "note Piano D5 at:11.1 dur:quarter vel:85",
        "note Piano F5 at:11.2 dur:quarter vel:88",
        "note Piano A5 at:11.3 dur:quarter vel:92",
        "note Piano C6 at:11.4 dur:quarter vel:95",
        # Bar 12: climax resolution
        "note Piano D6 at:12.1 dur:half vel:96",
        "note Piano C6 at:12.3 dur:half vel:92",
    ])))

    # Piano — chords supporting melody
    print("\n".join(intent.execute_ops([
        "chord Piano Cmaj at:5.1 dur:half vel:60",
        "chord Piano Cmaj at:5.3 dur:half vel:60",
        "chord Piano Am at:6.1 dur:half vel:60",
        "chord Piano Cmaj at:6.3 dur:half vel:60",
        "chord Piano Cmaj at:7.1 dur:half vel:62",
        "chord Piano Am at:7.3 dur:half vel:62",
        "chord Piano Cmaj at:8.1 dur:whole vel:65",
        "chord Piano Cmaj at:9.1 dur:half vel:62",
        "chord Piano Cmaj at:9.3 dur:half vel:62",
        "chord Piano Dm at:10.1 dur:half vel:62",
        "chord Piano Cmaj at:10.3 dur:half vel:62",
        "chord Piano Dm at:11.1 dur:half vel:65",
        "chord Piano Am at:11.3 dur:half vel:68",
        "chord Piano Cmaj at:12.1 dur:whole vel:70",
    ])))

    # Bass — rhythmic foundation
    print("\n".join(intent.execute_ops([
        "note Bass C3 at:5.1 dur:quarter vel:70",
        "note Bass C3 at:5.3 dur:quarter vel:68",
        "note Bass C3 at:6.1 dur:quarter vel:70",
        "note Bass A2 at:6.3 dur:quarter vel:68",
        "note Bass C3 at:7.1 dur:quarter vel:72",
        "note Bass A2 at:7.3 dur:quarter vel:70",
        "note Bass C3 at:8.1 dur:half vel:72",
        "note Bass G2 at:8.3 dur:half vel:70",
        "note Bass C3 at:9.1 dur:quarter vel:70",
        "note Bass C3 at:9.3 dur:quarter vel:68",
        "note Bass D3 at:10.1 dur:quarter vel:70",
        "note Bass C3 at:10.3 dur:quarter vel:68",
        "note Bass D3 at:11.1 dur:quarter vel:72",
        "note Bass A2 at:11.3 dur:quarter vel:72",
        "note Bass C3 at:12.1 dur:half vel:75",
        "note Bass G2 at:12.3 dur:half vel:72",
    ])))

    # Strings — sustained harmonies
    print("\n".join(intent.execute_ops([
        "chord Strings Cmaj at:5.1 dur:whole vel:60",
        "chord Strings Am at:6.1 dur:whole vel:60",
        "chord Strings Cmaj at:7.1 dur:whole vel:65",
        "chord Strings Cmaj at:8.1 dur:whole vel:68",
        "chord Strings Cmaj at:9.1 dur:whole vel:62",
        "chord Strings Dm at:10.1 dur:whole vel:62",
        "chord Strings Dm at:11.1 dur:whole vel:68",
        "chord Strings Cmaj at:12.1 dur:whole vel:70",
    ])))

    # Drums — driving beat
    for bar in range(5, 13):
        ops = [
            # Kick on 1 and 3
            f"note Drums midi:36 at:{bar}.1 dur:eighth vel:85",
            f"note Drums midi:36 at:{bar}.3 dur:eighth vel:80",
            # Snare on 2 and 4
            f"note Drums midi:38 at:{bar}.2 dur:eighth vel:75",
            f"note Drums midi:38 at:{bar}.4 dur:eighth vel:75",
            # Hi-hat on every beat
            f"note Drums midi:42 at:{bar}.1 dur:eighth vel:55",
            f"note Drums midi:42 at:{bar}.2 dur:eighth vel:50",
            f"note Drums midi:42 at:{bar}.3 dur:eighth vel:55",
            f"note Drums midi:42 at:{bar}.4 dur:eighth vel:50",
        ]
        intent.execute_ops(ops)

    print(intent.execute_session("checkpoint bridge-start"))

    # ══════════════════════════════════════════════════════════════
    # BRIDGE (bars 13-16) — f, contrasting section
    # ══════════════════════════════════════════════════════════════
    print("\n=== BRIDGE (bars 13-16) ===")

    # Piano — reflective, chordal
    print("\n".join(intent.execute_ops([
        "chord Piano Am at:13.1 dur:whole vel:72",
        "chord Piano Dm at:14.1 dur:whole vel:72",
        "chord Piano Cmaj at:15.1 dur:whole vel:75",
        "chord Piano Cmaj at:16.1 dur:half vel:78",
        # Ascending run in bar 16 to finale
        "note Piano G5 at:16.3 dur:eighth vel:80",
        "note Piano A5 at:16.3 dur:eighth vel:82",
        "note Piano B5 at:16.4 dur:eighth vel:85",
    ])))

    # Piano — melody over bridge chords
    print("\n".join(intent.execute_ops([
        "note Piano E5 at:13.1 dur:half vel:75",
        "note Piano C5 at:13.3 dur:half vel:72",
        "note Piano D5 at:14.1 dur:half vel:75",
        "note Piano A4 at:14.3 dur:half vel:72",
        "note Piano E5 at:15.1 dur:quarter vel:78",
        "note Piano F5 at:15.2 dur:quarter vel:78",
        "note Piano G5 at:15.3 dur:half vel:80",
        "note Piano E5 at:16.1 dur:half vel:82",
    ])))

    # Bass — bridge line
    print("\n".join(intent.execute_ops([
        "note Bass A2 at:13.1 dur:whole vel:68",
        "note Bass D3 at:14.1 dur:whole vel:68",
        "note Bass C3 at:15.1 dur:whole vel:70",
        "note Bass C3 at:16.1 dur:half vel:70",
        "note Bass G2 at:16.3 dur:half vel:75",
    ])))

    # Strings — bridge harmonies
    print("\n".join(intent.execute_ops([
        "chord Strings Am at:13.1 dur:whole vel:65",
        "chord Strings Dm at:14.1 dur:whole vel:65",
        "chord Strings Cmaj at:15.1 dur:whole vel:70",
        "chord Strings Cmaj at:16.1 dur:whole vel:75",
    ])))

    # Drums — lighter in bridge, building to finale
    for bar in [13, 14]:
        intent.execute_ops([
            f"note Drums midi:42 at:{bar}.1 dur:eighth vel:45",
            f"note Drums midi:42 at:{bar}.2 dur:eighth vel:40",
            f"note Drums midi:42 at:{bar}.3 dur:eighth vel:45",
            f"note Drums midi:42 at:{bar}.4 dur:eighth vel:40",
            f"note Drums midi:36 at:{bar}.1 dur:eighth vel:65",
            f"note Drums midi:38 at:{bar}.3 dur:eighth vel:60",
        ])
    # Bars 15-16: building back up
    for bar in [15, 16]:
        intent.execute_ops([
            f"note Drums midi:36 at:{bar}.1 dur:eighth vel:80",
            f"note Drums midi:36 at:{bar}.3 dur:eighth vel:80",
            f"note Drums midi:38 at:{bar}.2 dur:eighth vel:70",
            f"note Drums midi:38 at:{bar}.4 dur:eighth vel:70",
            f"note Drums midi:42 at:{bar}.1 dur:eighth vel:55",
            f"note Drums midi:42 at:{bar}.2 dur:eighth vel:50",
            f"note Drums midi:42 at:{bar}.3 dur:eighth vel:55",
            f"note Drums midi:42 at:{bar}.4 dur:eighth vel:55",
        ])
    # Crash into finale
    intent.execute_ops(["note Drums midi:49 at:16.4 dur:quarter vel:100"])

    print(intent.execute_session("checkpoint finale-start"))

    # ══════════════════════════════════════════════════════════════
    # FINALE (bars 17-20) — ff, triumphant conclusion
    # ══════════════════════════════════════════════════════════════
    print("\n=== FINALE (bars 17-20) ===")

    # Piano — big chords + melody at ff
    print("\n".join(intent.execute_ops([
        # Melody
        "note Piano C6 at:17.1 dur:quarter vel:110",
        "note Piano E6 at:17.2 dur:quarter vel:110",
        "note Piano G5 at:17.3 dur:half vel:105",
        "note Piano A5 at:18.1 dur:quarter vel:108",
        "note Piano G5 at:18.2 dur:quarter vel:105",
        "note Piano E5 at:18.3 dur:half vel:100",
        "note Piano F5 at:19.1 dur:quarter vel:108",
        "note Piano G5 at:19.2 dur:quarter vel:110",
        "note Piano A5 at:19.3 dur:quarter vel:112",
        "note Piano B5 at:19.4 dur:quarter vel:115",
        # Final bar: big C octave
        "note Piano C6 at:20.1 dur:whole vel:120",
        "note Piano C5 at:20.1 dur:whole vel:115",
        "note Piano C4 at:20.1 dur:whole vel:110",
        # Supporting chords
        "chord Piano Cmaj at:17.1 dur:whole vel:80",
        "chord Piano Am at:18.1 dur:whole vel:80",
        "chord Piano Dm at:19.1 dur:half vel:82",
        "chord Piano Cmaj at:19.3 dur:half vel:85",
        "chord Piano Cmaj at:20.1 dur:whole vel:90",
    ])))

    # Bass — powerful finale
    print("\n".join(intent.execute_ops([
        "note Bass C3 at:17.1 dur:quarter vel:85",
        "note Bass C2 at:17.1 dur:quarter vel:80",
        "note Bass C3 at:17.3 dur:quarter vel:82",
        "note Bass A2 at:18.1 dur:half vel:82",
        "note Bass G2 at:18.3 dur:half vel:80",
        "note Bass D3 at:19.1 dur:quarter vel:82",
        "note Bass C3 at:19.3 dur:quarter vel:85",
        "note Bass G2 at:19.4 dur:quarter vel:82",
        # Final bar: sustained C
        "note Bass C2 at:20.1 dur:whole vel:90",
        "note Bass C3 at:20.1 dur:whole vel:85",
    ])))

    # Strings — full fortissimo
    print("\n".join(intent.execute_ops([
        "chord Strings Cmaj at:17.1 dur:whole vel:85",
        "chord Strings Am at:18.1 dur:whole vel:85",
        "chord Strings Dm at:19.1 dur:half vel:88",
        "chord Strings Cmaj at:19.3 dur:half vel:90",
        "chord Strings Cmaj at:20.1 dur:whole vel:95",
    ])))

    # Drums — full power
    for bar in [17, 18, 19]:
        intent.execute_ops([
            f"note Drums midi:49 at:{bar}.1 dur:eighth vel:100",  # crash
            f"note Drums midi:36 at:{bar}.1 dur:eighth vel:95",
            f"note Drums midi:36 at:{bar}.3 dur:eighth vel:90",
            f"note Drums midi:38 at:{bar}.2 dur:eighth vel:90",
            f"note Drums midi:38 at:{bar}.4 dur:eighth vel:90",
            f"note Drums midi:42 at:{bar}.1 dur:eighth vel:60",
            f"note Drums midi:42 at:{bar}.2 dur:eighth vel:55",
            f"note Drums midi:42 at:{bar}.3 dur:eighth vel:60",
            f"note Drums midi:42 at:{bar}.4 dur:eighth vel:55",
        ])
    # Final bar: crash + big kick
    intent.execute_ops([
        "note Drums midi:49 at:20.1 dur:half vel:120",
        "note Drums midi:57 at:20.1 dur:half vel:110",  # crash 2
        "note Drums midi:36 at:20.1 dur:quarter vel:110",
        "note Drums midi:36 at:20.3 dur:quarter vel:100",
    ])

    # ── Verify & Save ──────────────────────────────────────────────
    print("\n=== VERIFICATION ===")
    print(intent.execute_query("stats"))
    print()
    print(intent.execute_query("tracks"))
    print()
    print(intent.execute_query("map"))

    # Save
    print("\n=== SAVING ===")
    result = intent.execute_session("save as:celebration.mid")
    print(result)

    # Verify file
    import os
    if os.path.exists("celebration.mid"):
        size = os.path.getsize("celebration.mid")
        print(f"\ncelebration.mid written successfully ({size:,} bytes)")
        print("Open in GarageBand, MuseScore, or any MIDI player to hear the FCP Fanfare!")
    else:
        print("\nERROR: celebration.mid was not created!")
        return

    # Final verification: re-open the file
    print("\n=== ROUND-TRIP VERIFICATION ===")
    intent2 = IntentLayer()
    result = intent2.execute_session("open celebration.mid")
    print(result)
    print(intent2.execute_query("stats"))


if __name__ == "__main__":
    main()
