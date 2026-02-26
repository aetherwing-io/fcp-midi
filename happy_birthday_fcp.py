#!/usr/bin/env python3
"""Full orchestral rendition of "Happy Birthday to You" using the MIDI FCP API.

Key: F major | Time: 3/4 (waltz) | Tempo: 100 BPM
Tracks: Flute (melody), Clarinet (harmony), Piano (waltz pattern),
        Strings (sustained pads), Bass (waltz oom), French Horn (brass),
        Drums (triangle/tambourine percussion)

Structure: 12 bars with pickup notes. The melody is the traditional
"Happy Birthday to You" arranged for full orchestra.
"""

from fcp_midi.server.intent import IntentLayer


def main() -> None:
    intent = IntentLayer()

    # ── Session setup ──────────────────────────────────────────────
    print("Creating song...")
    print(intent.execute_session(
        'new "Happy Birthday to You" tempo:100 time-sig:3/4 key:F-major'
    ))

    # ── Add orchestral tracks ──────────────────────────────────────
    print("\nAdding tracks...")
    print("\n".join(intent.execute_ops([
        "track add Flute instrument:flute",
        "track add Clarinet instrument:clarinet",
        "track add Piano instrument:acoustic-grand-piano",
        "track add Strings instrument:string-ensemble-1",
        "track add Bass instrument:acoustic-bass",
        "track add Horn instrument:french-horn",
        "track add Drums instrument:standard-kit ch:10",
    ])))

    # ── Markers ────────────────────────────────────────────────────
    print("\nAdding markers...")
    print("\n".join(intent.execute_ops([
        'marker Phrase-1 at:1.1',
        'marker Phrase-2 at:4.1',
        'marker Phrase-3-climax at:7.1',
        'marker Phrase-4-finale at:10.1',
    ])))

    # ==================================================================
    # MELODY — Flute
    # ==================================================================
    # "Happy Birthday to You" in F major, 3/4 time
    #
    # The melody across 12 bars (with pickup notes on beats 2-3):
    #
    # Bar 1:  rest  C4(8th) C4(8th)   -- pickup "Hap-py"
    # Bar 2:  D4(q) C4(q)   F4(q)     -- "birth-day to"
    # Bar 3:  E4(h.)                   -- "you"
    #
    # Bar 4:  rest  C4(8th) C4(8th)   -- pickup "Hap-py"
    # Bar 5:  D4(q) C4(q)   G4(q)     -- "birth-day to"
    # Bar 6:  F4(h.)                   -- "you"
    #
    # Bar 7:  rest  C4(8th) C4(8th)   -- pickup "Hap-py"
    # Bar 8:  C5(q) A4(q)   F4(q)     -- "birth-day dear"
    # Bar 9:  E4(q) D4(q)   rest      -- "[name]"
    #
    # Bar 10: rest  Bb4(8th) Bb4(8th) -- pickup "Hap-py"
    # Bar 11: A4(q) F4(q)   G4(q)     -- "birth-day to"
    # Bar 12: F4(h.)                   -- "you"
    # ==================================================================

    print("\n=== FLUTE MELODY ===")

    # -- Phrase 1: "Happy birthday to you" (bars 1-3) --
    # p (piano/soft) — vel ~60
    print("\n".join(intent.execute_ops([
        # Bar 1: pickup on beats 2-3
        "note Flute C4 at:1.2 dur:eighth vel:55",
        "note Flute C4 at:1.2.240 dur:eighth vel:58",
        # Bar 2: D4 C4 F4
        "note Flute D4 at:2.1 dur:quarter vel:62",
        "note Flute C4 at:2.2 dur:quarter vel:60",
        "note Flute F4 at:2.3 dur:quarter vel:65",
        # Bar 3: E4 held (dotted half = full bar in 3/4)
        "note Flute E4 at:3.1 dur:dotted-half vel:60",
    ])))

    # -- Phrase 2: "Happy birthday to you" (bars 4-6) --
    # mp — vel ~68
    print("\n".join(intent.execute_ops([
        # Bar 4: pickup
        "note Flute C4 at:4.2 dur:eighth vel:62",
        "note Flute C4 at:4.2.240 dur:eighth vel:65",
        # Bar 5: D4 C4 G4
        "note Flute D4 at:5.1 dur:quarter vel:70",
        "note Flute C4 at:5.2 dur:quarter vel:68",
        "note Flute G4 at:5.3 dur:quarter vel:72",
        # Bar 6: F4 held
        "note Flute F4 at:6.1 dur:dotted-half vel:68",
    ])))

    # -- Phrase 3: "Happy birthday dear ___" (bars 7-9) --
    # mf to f — vel ~80-90 (climax)
    print("\n".join(intent.execute_ops([
        # Bar 7: pickup
        "note Flute C4 at:7.2 dur:eighth vel:72",
        "note Flute C4 at:7.2.240 dur:eighth vel:75",
        # Bar 8: C5 A4 F4
        "note Flute C5 at:8.1 dur:quarter vel:88",
        "note Flute A4 at:8.2 dur:quarter vel:85",
        "note Flute F4 at:8.3 dur:quarter vel:82",
        # Bar 9: E4 D4
        "note Flute E4 at:9.1 dur:quarter vel:80",
        "note Flute D4 at:9.2 dur:half vel:78",
    ])))

    # -- Phrase 4: "Happy birthday to you" (bars 10-12) --
    # f, then gentle ending — vel ~85 tapering
    print("\n".join(intent.execute_ops([
        # Bar 10: pickup
        "note Flute Bb4 at:10.2 dur:eighth vel:80",
        "note Flute Bb4 at:10.2.240 dur:eighth vel:82",
        # Bar 11: A4 F4 G4
        "note Flute A4 at:11.1 dur:quarter vel:85",
        "note Flute F4 at:11.2 dur:quarter vel:82",
        "note Flute G4 at:11.3 dur:quarter vel:80",
        # Bar 12: F4 held — final, gentle
        "note Flute F4 at:12.1 dur:dotted-half vel:75",
    ])))

    # ==================================================================
    # HARMONY — Clarinet (enters phrase 2, harmonizes a 3rd/6th below)
    # ==================================================================
    print("\n=== CLARINET HARMONY ===")

    # -- Phrase 2 harmony (bars 4-6) — a third below the melody --
    print("\n".join(intent.execute_ops([
        # Bar 4: pickup harmony
        "note Clarinet A3 at:4.2 dur:eighth vel:50",
        "note Clarinet A3 at:4.2.240 dur:eighth vel:52",
        # Bar 5: Bb3 A3 E4 (third below D4 C4 G4)
        "note Clarinet Bb3 at:5.1 dur:quarter vel:58",
        "note Clarinet A3 at:5.2 dur:quarter vel:55",
        "note Clarinet E4 at:5.3 dur:quarter vel:60",
        # Bar 6: D4 held (third below F4)
        "note Clarinet D4 at:6.1 dur:dotted-half vel:55",
    ])))

    # -- Phrase 3 harmony (bars 7-9) — the climax --
    print("\n".join(intent.execute_ops([
        # Bar 7: pickup
        "note Clarinet A3 at:7.2 dur:eighth vel:60",
        "note Clarinet A3 at:7.2.240 dur:eighth vel:62",
        # Bar 8: A4 F4 D4 (third/sixth below C5 A4 F4)
        "note Clarinet A4 at:8.1 dur:quarter vel:75",
        "note Clarinet F4 at:8.2 dur:quarter vel:72",
        "note Clarinet D4 at:8.3 dur:quarter vel:70",
        # Bar 9: C4 Bb3
        "note Clarinet C4 at:9.1 dur:quarter vel:68",
        "note Clarinet Bb3 at:9.2 dur:half vel:65",
    ])))

    # -- Phrase 4 harmony (bars 10-12) --
    print("\n".join(intent.execute_ops([
        # Bar 10: pickup
        "note Clarinet G4 at:10.2 dur:eighth vel:68",
        "note Clarinet G4 at:10.2.240 dur:eighth vel:70",
        # Bar 11: F4 D4 E4 (third below A4 F4 G4)
        "note Clarinet F4 at:11.1 dur:quarter vel:72",
        "note Clarinet D4 at:11.2 dur:quarter vel:70",
        "note Clarinet E4 at:11.3 dur:quarter vel:68",
        # Bar 12: D4 held (below F4)
        "note Clarinet D4 at:12.1 dur:dotted-half vel:62",
    ])))

    # ==================================================================
    # PIANO — Waltz "oom-pah-pah" pattern
    # Bass note on beat 1, chord on beats 2 and 3
    # ==================================================================
    print("\n=== PIANO WALTZ PATTERN ===")

    # Chord progression in F major:
    # Bar 1: F (I)       Bar 2: F (I)        Bar 3: F (I) -> C7 (V7)
    # Bar 4: F (I)       Bar 5: C7 (V7)      Bar 6: F (I)
    # Bar 7: F (I)       Bar 8: F (I)        Bar 9: Bb (IV) -> Dm (vi)
    # Bar 10: Bb (IV)    Bar 11: F (I)->C7    Bar 12: F (I)

    waltz_bars = [
        # (bar, bass_note, chord_symbol, velocity_base)
        # Phrase 1
        (1,  "F3",  "Fmaj",  45),
        (2,  "F3",  "Fmaj",  50),
        (3,  "C3",  "Cmaj",  48),   # V chord under the held E4
        # Phrase 2
        (4,  "F3",  "Fmaj",  52),
        (5,  "C3",  "C7",    55),   # V7 under G4
        (6,  "F3",  "Fmaj",  55),
        # Phrase 3 (climax)
        (7,  "F3",  "Fmaj",  58),
        (8,  "F3",  "Fmaj",  68),   # f for "dear ___"
        (9,  "Bb2", "Bbmaj", 65),   # IV chord
        # Phrase 4
        (10, "Bb2", "Bbmaj", 62),
        (11, "F3",  "Fmaj",  60),
        (12, "F3",  "Fmaj",  55),   # gentle ending
    ]

    for bar, bass, chord, vel in waltz_bars:
        ops = [
            # "Oom" — bass note on beat 1
            f"note Piano {bass} at:{bar}.1 dur:quarter vel:{vel + 5}",
            # "Pah" — chord on beat 2
            f"chord Piano {chord} at:{bar}.2 dur:quarter vel:{vel}",
            # "Pah" — chord on beat 3
            f"chord Piano {chord} at:{bar}.3 dur:quarter vel:{vel - 3}",
        ]
        intent.execute_ops(ops)

    # Special: bar 11 switches to C7 on beat 3 for the V-I cadence
    intent.execute_ops([
        # Override bar 11 beat 3 with C7 instead of Fmaj
        "chord Piano C7 at:11.3 dur:quarter vel:62",
    ])

    print("  Piano waltz pattern complete (12 bars)")

    # ==================================================================
    # STRINGS — Sustained chord pads (enter softly from the beginning)
    # ==================================================================
    print("\n=== STRINGS PADS ===")

    string_pads = [
        # (bar, chord, velocity) — each lasts one full measure (dotted-half)
        # Phrase 1: pp
        (1,  "Fmaj",  35),
        (2,  "Fmaj",  38),
        (3,  "Cmaj",  38),
        # Phrase 2: p
        (4,  "Fmaj",  42),
        (5,  "C7",    45),
        (6,  "Fmaj",  45),
        # Phrase 3: mf-f (climax)
        (7,  "Fmaj",  50),
        (8,  "Fmaj",  62),
        (9,  "Bbmaj", 58),
        # Phrase 4: mf tapering
        (10, "Bbmaj", 55),
        (11, "Fmaj",  52),
        (12, "Fmaj",  48),
    ]

    for bar, chord, vel in string_pads:
        intent.execute_ops([
            f"chord Strings {chord} at:{bar}.1 dur:dotted-half vel:{vel}",
        ])

    print("  String pads complete (12 bars)")

    # ==================================================================
    # BASS — Waltz "oom" on beat 1 of each measure
    # ==================================================================
    print("\n=== BASS (Acoustic Bass) ===")

    bass_notes = [
        # (bar, pitch, velocity)
        # Phrase 1: p
        (1,  "F2", 45),
        (2,  "F2", 48),
        (3,  "C2", 48),
        # Phrase 2: mp
        (4,  "F2", 52),
        (5,  "C2", 55),
        (6,  "F2", 55),
        # Phrase 3: f (climax)
        (7,  "F2", 58),
        (8,  "F2", 70),
        (9,  "Bb1", 68),
        # Phrase 4: mf, tapering
        (10, "Bb1", 62),
        (11, "F2",  58),
        (12, "F2",  50),
    ]

    for bar, pitch, vel in bass_notes:
        intent.execute_ops([
            f"note Bass {pitch} at:{bar}.1 dur:dotted-half vel:{vel}",
        ])

    # Add bass motion: beat 3 passing tones for phrase 3 & 4
    intent.execute_ops([
        # Bar 8: bass walks F2 -> A2 on beat 3
        "note Bass A2 at:8.3 dur:quarter vel:65",
        # Bar 9: Bb going to G on beat 3
        "note Bass G2 at:9.3 dur:quarter vel:60",
        # Bar 11: F going to C for cadence
        "note Bass C2 at:11.3 dur:quarter vel:55",
    ])

    print("  Bass complete (12 bars)")

    # ==================================================================
    # BRASS — French Horn (enters for climax, bars 7-12)
    # ==================================================================
    print("\n=== FRENCH HORN (BRASS) ===")

    # Horn enters on the "Happy birthday dear" phrase for dramatic effect
    print("\n".join(intent.execute_ops([
        # Bar 7: pickup support (just beat 1 sustained)
        "note Horn F4 at:7.1 dur:dotted-half vel:55",
        # Bar 8: Big climax — C5 A4 F4 in octaves with melody
        "note Horn C4 at:8.1 dur:quarter vel:75",
        "note Horn A3 at:8.2 dur:quarter vel:72",
        "note Horn F3 at:8.3 dur:quarter vel:70",
        # Bar 9: resolution
        "note Horn Bb3 at:9.1 dur:quarter vel:68",
        "note Horn A3 at:9.2 dur:half vel:65",
        # Bar 10: sustained Bb
        "note Horn Bb3 at:10.1 dur:dotted-half vel:60",
        # Bar 11: walking with cadence
        "note Horn A3 at:11.1 dur:quarter vel:62",
        "note Horn F3 at:11.2 dur:quarter vel:60",
        "note Horn G3 at:11.3 dur:quarter vel:58",
        # Bar 12: final F — sustained, gentle
        "note Horn F3 at:12.1 dur:dotted-half vel:52",
    ])))

    # ==================================================================
    # DRUMS — Light triangle (midi:81) and tambourine (midi:54)
    # Tasteful orchestral percussion, not rock drums
    # ==================================================================
    print("\n=== DRUMS (Triangle/Tambourine) ===")

    # Triangle (GM percussion: midi:81 = open triangle)
    # Light hit on beat 1 of each bar
    for bar in range(1, 13):
        # Dynamics: soft at start, build at climax, taper at end
        if bar <= 3:
            vel = 35   # pp
        elif bar <= 6:
            vel = 45   # p
        elif bar <= 9:
            vel = 60   # mf-f (climax)
        else:
            vel = 50   # mp (tapering)

        # Final bar even softer
        if bar == 12:
            vel = 38

        intent.execute_ops([
            f"note Drums midi:81 at:{bar}.1 dur:eighth vel:{vel}",
        ])

    # Tambourine (GM: midi:54) on beats 2 and 3 — only during climax
    # bars 8-11 for extra shimmer
    for bar in range(8, 12):
        vel = 40 if bar >= 10 else 50
        intent.execute_ops([
            f"note Drums midi:54 at:{bar}.2 dur:eighth vel:{vel}",
            f"note Drums midi:54 at:{bar}.3 dur:eighth vel:{vel - 5}",
        ])

    # Final bar: single soft triangle ding
    intent.execute_ops([
        "note Drums midi:81 at:12.3 dur:quarter vel:30",
    ])

    print("  Percussion complete")

    # ==================================================================
    # FINAL CHORD — Let the last bar ring with a fermata feel
    # ==================================================================
    print("\n=== FINAL TOUCHES ===")

    # Extend the final F major chord with a ritardando effect:
    # Add extra sustained notes in bar 12 for strings and horn
    # (already covered by dotted-half durations above)

    # Add a final piano arpeggiated F chord in bar 12 for warmth
    intent.execute_ops([
        "note Piano F2 at:12.1 dur:dotted-half vel:50",
        "note Piano C3 at:12.1 dur:dotted-half vel:45",
        "note Piano F3 at:12.1 dur:dotted-half vel:45",
        "note Piano A3 at:12.1 dur:dotted-half vel:42",
        "note Piano C4 at:12.1 dur:dotted-half vel:40",
    ])

    print("  Final touches complete")

    # ── Verify & Save ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    print(intent.execute_query("stats"))
    print()
    print(intent.execute_query("tracks"))

    # Save
    print("\n" + "=" * 60)
    print("SAVING")
    print("=" * 60)
    result = intent.execute_session("save as:happy_birthday_fcp.mid")
    print(result)

    # Verify file
    import os
    path = "happy_birthday_fcp.mid"
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"\n{path} written successfully ({size:,} bytes)")
        print("Open in GarageBand, Logic Pro, MuseScore, or any MIDI player!")
    else:
        print(f"\nERROR: {path} was not created!")


if __name__ == "__main__":
    main()
