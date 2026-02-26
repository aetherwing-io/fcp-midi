"""Intent dispatch layer — routes parsed ops to model mutations and queries."""

from __future__ import annotations

import difflib
import re

from fcp_midi.model.event_log import (
    CCAdded,
    CheckpointEvent,
    EventLog,
    KeySignatureChanged,
    MarkerAdded,
    NoteAdded,
    NoteModified,
    NoteRemoved,
    PitchBendAdded,
    TempoChanged,
    TimeSignatureChanged,
    TrackAdded,
    TrackRemoved,
)
from fcp_midi.model.registry import Registry
from fcp_midi.model.song import Note, Pitch, Song
from fcp_midi.model.timing import position_to_ticks, ticks_to_position
from fcp_midi.parser.chord import parse_chord
from fcp_midi.parser.duration import parse_duration
from fcp_midi.parser.ops import ParsedOp, ParseError, parse_op
from fcp_midi.parser.pitch import parse_pitch
from fcp_midi.parser.position import parse_position
from fcp_midi.parser.selector import Selector
from fcp_midi.lib.cc_names import cc_to_number, parse_cc_value
from fcp_midi.lib.gm_instruments import instrument_to_program, program_to_instrument
from fcp_midi.lib.velocity_names import parse_velocity
from fcp_midi.server.formatter import (
    format_describe,
    format_events,
    format_map,
    format_piano_roll,
    format_result,
    format_stats,
    format_track_list,
)


class IntentLayer:
    """Core orchestration: parse ops, dispatch to model, format responses."""

    def __init__(self) -> None:
        self.song: Song | None = None
        self.event_log: EventLog = EventLog()
        self.registry: Registry = Registry()
        # Stashed state for undo: maps event index -> data needed to reverse
        self._undo_stash: dict[int, object] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_ops(self, ops: list[str]) -> list[str]:
        """Execute a batch of mutation ops, return formatted results."""
        results: list[str] = []
        for op_str in ops:
            result = self._execute_single_op(op_str)
            results.append(result)

        # Append digest if song exists
        if self.song:
            results.append(self.song.get_digest())
        return results

    def execute_query(self, q: str) -> str:
        """Execute a read-only query and return formatted output."""
        if self.song is None:
            return "! No song loaded. Use midi_session to create or open one."

        q = q.strip()
        parts = q.split(None, 1)
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if command == "map":
            return format_map(self.song)
        elif command == "tracks":
            return format_track_list(self.song)
        elif command == "events":
            return self._query_events(args)
        elif command == "describe":
            return self._query_describe(args)
        elif command == "stats":
            return format_stats(self.song)
        elif command == "status":
            return self._query_status()
        elif command == "find":
            return self._query_find(args)
        elif command == "piano-roll":
            return self._query_piano_roll(args)
        elif command == "history":
            return self._query_history(args)
        elif command == "diff":
            return self._query_diff(args)
        else:
            return f"! Unknown query: {command!r}\n  try: map, tracks, events, describe, stats, find, piano-roll, history"

    def execute_session(self, action: str) -> str:
        """Execute a session lifecycle action."""
        action = action.strip()
        parts_raw = _tokenize_session(action)
        command = parts_raw[0].lower() if parts_raw else ""
        rest = parts_raw[1:]

        if command == "new":
            return self._session_new(rest)
        elif command == "open":
            return self._session_open(rest)
        elif command == "save":
            return self._session_save(rest)
        elif command == "checkpoint":
            return self._session_checkpoint(rest)
        elif command == "undo":
            return self._session_undo(rest)
        elif command == "redo":
            return self._session_redo(rest)
        else:
            return f"! Unknown session action: {command!r}\n  try: new, open, save, checkpoint, undo, redo"

    # ------------------------------------------------------------------
    # Op dispatch
    # ------------------------------------------------------------------

    def _execute_single_op(self, op_str: str) -> str:
        """Parse and execute a single op string."""
        if self.song is None:
            return format_result(False, "No song loaded. Create or open one first.",
                                 'midi_session(\'new "Title" tempo:120\')')

        parsed = parse_op(op_str)
        if isinstance(parsed, ParseError):
            return format_result(False, f"Parse error: {parsed.error}")

        try:
            return self._dispatch_op(parsed)
        except Exception as exc:
            return format_result(False, f"Error: {exc}")

    def _dispatch_op(self, op: ParsedOp) -> str:
        """Route a parsed op to the appropriate handler."""
        verb = op.verb
        handlers = {
            "note": self._op_note,
            "chord": self._op_chord,
            "track": self._op_track,
            "cc": self._op_cc,
            "bend": self._op_bend,
            "tempo": self._op_tempo,
            "time-sig": self._op_time_sig,
            "key-sig": self._op_key_sig,
            "marker": self._op_marker,
            "title": self._op_title,
            "remove": self._op_remove,
            "move": self._op_move,
            "copy": self._op_copy,
            "transpose": self._op_transpose,
            "velocity": self._op_velocity,
            "quantize": self._op_quantize,
            "mute": self._op_mute,
            "solo": self._op_solo,
            "program": self._op_program,
        }
        handler = handlers.get(verb)
        if handler is None:
            return format_result(False, f"Unknown verb: {verb!r}")
        return handler(op)

    # ------------------------------------------------------------------
    # Op handlers
    # ------------------------------------------------------------------

    def _op_note(self, op: ParsedOp) -> str:
        assert self.song is not None
        track = self._resolve_track(op.target)
        if isinstance(track, str):
            return track  # error message

        pitch_str = op.params.get("pitch")
        if not pitch_str:
            return format_result(False, "Missing pitch for note")

        try:
            pitch = parse_pitch(pitch_str)
        except ValueError as e:
            return format_result(False, f"Invalid pitch: {e}")

        at_str = op.params.get("at", "1.1")
        try:
            tick = parse_position(at_str, self.song.time_signatures, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid position: {e}")

        dur_str = op.params.get("dur", "quarter")
        try:
            dur = parse_duration(dur_str, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid duration: {e}")

        vel_str = op.params.get("vel", "80")
        try:
            vel = parse_velocity(vel_str)
        except ValueError as e:
            return format_result(False, f"Invalid velocity: {e}")

        ch = int(op.params["ch"]) if "ch" in op.params else None

        note = self.song.add_note(track.id, pitch, tick, dur, vel, ch)
        self.event_log.append(NoteAdded(track_id=track.id, note_id=note.id))
        self.registry.rebuild(self.song)

        pos = ticks_to_position(tick, self.song.time_signatures, self.song.ppqn)
        return format_result(
            True,
            f"Note {pitch_str} at {pos} on {track.name} (vel:{vel} dur:{dur_str})"
        )

    def _op_chord(self, op: ParsedOp) -> str:
        assert self.song is not None
        track = self._resolve_track(op.target)
        if isinstance(track, str):
            return track

        chord_str = op.params.get("chord")
        if not chord_str:
            return format_result(False, "Missing chord symbol")

        try:
            pitches = parse_chord(chord_str)
        except ValueError as e:
            return format_result(False, f"Invalid chord: {e}")

        at_str = op.params.get("at", "1.1")
        try:
            tick = parse_position(at_str, self.song.time_signatures, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid position: {e}")

        dur_str = op.params.get("dur", "quarter")
        try:
            dur = parse_duration(dur_str, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid duration: {e}")

        vel_str = op.params.get("vel", "80")
        try:
            vel = parse_velocity(vel_str)
        except ValueError as e:
            return format_result(False, f"Invalid velocity: {e}")

        ch = int(op.params["ch"]) if "ch" in op.params else None

        for pitch in pitches:
            note = self.song.add_note(track.id, pitch, tick, dur, vel, ch)
            self.event_log.append(NoteAdded(track_id=track.id, note_id=note.id))

        self.registry.rebuild(self.song)

        pos = ticks_to_position(tick, self.song.time_signatures, self.song.ppqn)
        return format_result(
            True,
            f"Chord {chord_str} ({len(pitches)} notes) at {pos} on {track.name}"
        )

    def _op_track(self, op: ParsedOp) -> str:
        assert self.song is not None
        sub = op.target  # "add" or "remove"

        if sub == "add":
            name = op.params.get("name")
            if not name:
                return format_result(False, "Missing track name",
                                     "track add MyTrack instrument:acoustic-grand-piano")

            inst_name = op.params.get("instrument")
            program = None
            if inst_name:
                program = instrument_to_program(inst_name)
                if program is None:
                    return format_result(False, f"Unknown instrument: {inst_name!r}")

            ch = int(op.params["ch"]) if "ch" in op.params else None

            track = self.song.add_track(
                name=name,
                instrument=inst_name,
                program=program,
                channel=ch,
            )
            self.event_log.append(TrackAdded(track_id=track.id))
            self.registry.rebuild(self.song)

            inst_display = inst_name or "no instrument"
            return format_result(True, f"Track '{name}' added (ch:{track.channel}, {inst_display})")

        elif sub == "remove":
            name = op.params.get("name")
            if not name:
                return format_result(False, "Missing track name for remove")

            track = self.song.get_track_by_name(name)
            if not track:
                suggestion = self._suggest_track_name(name)
                return format_result(False, f"Track '{name}' not found", suggestion)

            removed = self.song.remove_track(track.id)
            if removed:
                self.event_log.append(TrackRemoved(track_id=removed.id))
                self.registry.rebuild(self.song)
                return format_result(True, f"Track '{name}' removed")
            return format_result(False, f"Failed to remove track '{name}'")

        else:
            return format_result(False, f"Unknown track sub-command: {sub!r}",
                                 "track add NAME or track remove NAME")

    def _op_cc(self, op: ParsedOp) -> str:
        assert self.song is not None
        track = self._resolve_track(op.target)
        if isinstance(track, str):
            return track

        cc_name = op.params.get("cc_name")
        cc_value_str = op.params.get("cc_value")
        if not cc_name or not cc_value_str:
            return format_result(False, "Missing CC name or value",
                                 "cc Piano volume 100 at:1.1")

        try:
            cc_num, cc_val = parse_cc_value(cc_name, cc_value_str)
        except ValueError as e:
            return format_result(False, str(e))

        at_str = op.params.get("at", "1.1")
        try:
            tick = parse_position(at_str, self.song.time_signatures, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid position: {e}")

        ch = int(op.params["ch"]) if "ch" in op.params else None

        cc = self.song.add_cc(track.id, cc_num, cc_val, tick, ch)
        self.event_log.append(CCAdded(track_id=track.id, cc_id=cc.id))
        self.registry.rebuild(self.song)

        pos = ticks_to_position(tick, self.song.time_signatures, self.song.ppqn)
        return format_result(True, f"CC {cc_name}={cc_val} at {pos} on {track.name}")

    def _op_bend(self, op: ParsedOp) -> str:
        assert self.song is not None
        track = self._resolve_track(op.target)
        if isinstance(track, str):
            return track

        value_str = op.params.get("value", "0")
        if value_str.lower() == "center":
            value = 0
        else:
            try:
                value = int(value_str)
            except ValueError:
                return format_result(False, f"Invalid bend value: {value_str!r}")

        if value < -8192 or value > 8191:
            return format_result(False, f"Bend value out of range (-8192 to 8191): {value}")

        at_str = op.params.get("at", "1.1")
        try:
            tick = parse_position(at_str, self.song.time_signatures, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid position: {e}")

        ch = int(op.params["ch"]) if "ch" in op.params else None

        pb = self.song.add_pitch_bend(track.id, value, tick, ch)
        self.event_log.append(PitchBendAdded(track_id=track.id, pb_id=pb.id))
        self.registry.rebuild(self.song)

        pos = ticks_to_position(tick, self.song.time_signatures, self.song.ppqn)
        return format_result(True, f"Pitch bend={value} at {pos} on {track.name}")

    def _op_tempo(self, op: ParsedOp) -> str:
        assert self.song is not None
        bpm_str = op.target
        if not bpm_str:
            return format_result(False, "Missing BPM value", "tempo 120")

        try:
            bpm = float(bpm_str)
        except ValueError:
            return format_result(False, f"Invalid BPM: {bpm_str!r}")

        at_str = op.params.get("at", "1.1")
        try:
            tick = parse_position(at_str, self.song.time_signatures, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid position: {e}")

        old_bpm = self.song.tempo_map[0].bpm if self.song.tempo_map else 120.0
        self.song.add_tempo(bpm, tick)
        self.event_log.append(TempoChanged(old_bpm=old_bpm, new_bpm=bpm, absolute_tick=tick))

        pos = ticks_to_position(tick, self.song.time_signatures, self.song.ppqn)
        return format_result(True, f"Tempo {bpm:.0f} BPM at {pos}")

    def _op_time_sig(self, op: ParsedOp) -> str:
        assert self.song is not None
        ts_str = op.target
        if not ts_str:
            return format_result(False, "Missing time signature", "time-sig 3/4")

        match = re.match(r"^(\d+)/(\d+)$", ts_str)
        if not match:
            return format_result(False, f"Invalid time signature: {ts_str!r}", "time-sig 3/4")

        num = int(match.group(1))
        denom = int(match.group(2))

        at_str = op.params.get("at", "1.1")
        try:
            tick = parse_position(at_str, self.song.time_signatures, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid position: {e}")

        old_ts = self.song.time_signatures[0] if self.song.time_signatures else None
        old_num = old_ts.numerator if old_ts else 4
        old_denom = old_ts.denominator if old_ts else 4

        self.song.add_time_signature(num, denom, tick)
        self.event_log.append(TimeSignatureChanged(
            old_numerator=old_num, old_denominator=old_denom,
            new_numerator=num, new_denominator=denom,
            absolute_tick=tick,
        ))

        return format_result(True, f"Time signature {num}/{denom}")

    def _op_key_sig(self, op: ParsedOp) -> str:
        assert self.song is not None
        ks_str = op.target
        if not ks_str:
            return format_result(False, "Missing key signature", "key-sig C-major")

        # Parse KEY-MODE: e.g. "C-major", "G-minor", "Bb-major"
        parts = ks_str.replace("-", " ").split()
        key = parts[0] if parts else "C"
        mode = parts[1] if len(parts) > 1 else "major"

        at_str = op.params.get("at", "1.1")
        try:
            tick = parse_position(at_str, self.song.time_signatures, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid position: {e}")

        old_ks = self.song.key_signatures[0] if self.song.key_signatures else None
        old_key = old_ks.key if old_ks else "C"
        old_mode = old_ks.mode if old_ks else "major"

        self.song.add_key_signature(key, mode, tick)
        self.event_log.append(KeySignatureChanged(
            old_key=old_key, old_mode=old_mode,
            new_key=key, new_mode=mode,
            absolute_tick=tick,
        ))

        return format_result(True, f"Key signature {key} {mode}")

    def _op_marker(self, op: ParsedOp) -> str:
        assert self.song is not None
        text = op.target
        if not text:
            return format_result(False, "Missing marker text", 'marker "Chorus" at:5.1')

        at_str = op.params.get("at", "1.1")
        try:
            tick = parse_position(at_str, self.song.time_signatures, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid position: {e}")

        self.song.add_marker(text, tick)
        self.event_log.append(MarkerAdded(text=text, absolute_tick=tick))

        pos = ticks_to_position(tick, self.song.time_signatures, self.song.ppqn)
        return format_result(True, f"Marker '{text}' at {pos}")

    def _op_title(self, op: ParsedOp) -> str:
        assert self.song is not None
        title = op.target
        if not title:
            return format_result(False, "Missing title", 'title "My Song"')

        self.song.title = title
        return format_result(True, f"Title set to '{title}'")

    def _op_remove(self, op: ParsedOp) -> str:
        assert self.song is not None
        notes = self._resolve_selectors(op.selectors)
        if isinstance(notes, str):
            return notes

        if not notes:
            return format_result(False, "No notes matched selectors")

        count = 0
        for note in notes:
            removed = self.song.remove_note(note.track_id, note.id)
            if removed:
                self.event_log.append(NoteRemoved(track_id=note.track_id, note_id=note.id))
                count += 1

        self.registry.rebuild(self.song)
        return format_result(True, f"Removed {count} note(s)")

    def _op_move(self, op: ParsedOp) -> str:
        assert self.song is not None
        notes = self._resolve_selectors(op.selectors)
        if isinstance(notes, str):
            return notes
        if not notes:
            return format_result(False, "No notes matched selectors")

        to_str = op.params.get("to")
        if not to_str:
            return format_result(False, "Missing to: parameter", "move @track:Piano to:3.1")

        try:
            to_tick = parse_position(to_str, self.song.time_signatures, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid position: {e}")

        # Calculate delta from earliest note
        min_tick = min(n.absolute_tick for n in notes)
        delta = to_tick - min_tick

        for note in notes:
            old_tick = note.absolute_tick
            note.absolute_tick = max(0, note.absolute_tick + delta)
            self.event_log.append(NoteModified(
                track_id=note.track_id, note_id=note.id,
                field_name="absolute_tick", old_value=old_tick, new_value=note.absolute_tick,
            ))

        self.registry.rebuild(self.song)
        pos = ticks_to_position(to_tick, self.song.time_signatures, self.song.ppqn)
        return format_result(True, f"Moved {len(notes)} note(s) to {pos}")

    def _op_copy(self, op: ParsedOp) -> str:
        assert self.song is not None
        notes = self._resolve_selectors(op.selectors)
        if isinstance(notes, str):
            return notes
        if not notes:
            return format_result(False, "No notes matched selectors")

        to_str = op.params.get("to")
        if not to_str:
            return format_result(False, "Missing to: parameter")

        try:
            to_tick = parse_position(to_str, self.song.time_signatures, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid position: {e}")

        min_tick = min(n.absolute_tick for n in notes)
        delta = to_tick - min_tick

        for note in notes:
            new_tick = max(0, note.absolute_tick + delta)
            new_note = self.song.add_note(
                note.track_id, note.pitch, new_tick,
                note.duration_ticks, note.velocity, note.channel,
            )
            self.event_log.append(NoteAdded(track_id=note.track_id, note_id=new_note.id))

        self.registry.rebuild(self.song)
        pos = ticks_to_position(to_tick, self.song.time_signatures, self.song.ppqn)
        return format_result(True, f"Copied {len(notes)} note(s) to {pos}")

    def _op_transpose(self, op: ParsedOp) -> str:
        assert self.song is not None
        notes = self._resolve_selectors(op.selectors)
        if isinstance(notes, str):
            return notes
        if not notes:
            return format_result(False, "No notes matched selectors")

        semitones_str = op.target
        if not semitones_str:
            return format_result(False, "Missing semitone count", "transpose @track:Piano +5")

        try:
            semitones = int(semitones_str)
        except ValueError:
            return format_result(False, f"Invalid semitone value: {semitones_str!r}")

        count = 0
        for note in notes:
            new_midi = note.pitch.midi_number + semitones
            if 0 <= new_midi <= 127:
                old_pitch = note.pitch
                note.pitch = _pitch_from_midi(new_midi)
                self.event_log.append(NoteModified(
                    track_id=note.track_id, note_id=note.id,
                    field_name="pitch", old_value=old_pitch, new_value=note.pitch,
                ))
                count += 1

        self.registry.rebuild(self.song)
        direction = "up" if semitones > 0 else "down"
        return format_result(True, f"Transposed {count} note(s) {direction} {abs(semitones)} semitones")

    def _op_velocity(self, op: ParsedOp) -> str:
        assert self.song is not None
        notes = self._resolve_selectors(op.selectors)
        if isinstance(notes, str):
            return notes
        if not notes:
            return format_result(False, "No notes matched selectors")

        delta_str = op.target
        if not delta_str:
            return format_result(False, "Missing velocity delta", "velocity @track:Piano +10")

        try:
            delta = int(delta_str)
        except ValueError:
            return format_result(False, f"Invalid velocity delta: {delta_str!r}")

        for note in notes:
            old_vel = note.velocity
            note.velocity = max(1, min(127, note.velocity + delta))
            self.event_log.append(NoteModified(
                track_id=note.track_id, note_id=note.id,
                field_name="velocity", old_value=old_vel, new_value=note.velocity,
            ))

        self.registry.rebuild(self.song)
        return format_result(True, f"Adjusted velocity of {len(notes)} note(s) by {delta:+d}")

    def _op_quantize(self, op: ParsedOp) -> str:
        assert self.song is not None
        notes = self._resolve_selectors(op.selectors)
        if isinstance(notes, str):
            return notes
        if not notes:
            return format_result(False, "No notes matched selectors")

        grid_str = op.params.get("grid", "quarter")
        try:
            grid_ticks = parse_duration(grid_str, self.song.ppqn)
        except ValueError as e:
            return format_result(False, f"Invalid grid: {e}")

        for note in notes:
            old_tick = note.absolute_tick
            # Snap to nearest grid point
            note.absolute_tick = round(note.absolute_tick / grid_ticks) * grid_ticks
            if note.absolute_tick != old_tick:
                self.event_log.append(NoteModified(
                    track_id=note.track_id, note_id=note.id,
                    field_name="absolute_tick", old_value=old_tick, new_value=note.absolute_tick,
                ))

        self.registry.rebuild(self.song)
        return format_result(True, f"Quantized {len(notes)} note(s) to {grid_str}")

    def _op_mute(self, op: ParsedOp) -> str:
        assert self.song is not None
        track = self._resolve_track(op.target)
        if isinstance(track, str):
            return track

        track.mute = not track.mute
        state = "muted" if track.mute else "unmuted"
        return format_result(True, f"Track '{track.name}' {state}")

    def _op_solo(self, op: ParsedOp) -> str:
        assert self.song is not None
        track = self._resolve_track(op.target)
        if isinstance(track, str):
            return track

        track.solo = not track.solo
        state = "solo on" if track.solo else "solo off"
        return format_result(True, f"Track '{track.name}' {state}")

    def _op_program(self, op: ParsedOp) -> str:
        assert self.song is not None
        track = self._resolve_track(op.target)
        if isinstance(track, str):
            return track

        inst_name = op.params.get("instrument")
        if not inst_name:
            return format_result(False, "Missing instrument name")

        program = instrument_to_program(inst_name)
        if program is None:
            return format_result(False, f"Unknown instrument: {inst_name!r}")

        track.instrument = inst_name
        track.program = program
        return format_result(True, f"Track '{track.name}' instrument set to {inst_name} (program:{program})")

    # ------------------------------------------------------------------
    # Track resolution with fuzzy matching
    # ------------------------------------------------------------------

    def _resolve_track(self, name: str | None) -> "str | Song.Track":  # type: ignore[name-defined]
        """Resolve a track name, returning the Track or an error string."""
        from fcp_midi.model.song import Track

        if not name:
            return format_result(False, "Missing track name")

        assert self.song is not None
        track = self.song.get_track_by_name(name)
        if track:
            return track

        suggestion = self._suggest_track_name(name)
        return format_result(False, f"Track '{name}' not found", suggestion)

    def _suggest_track_name(self, name: str) -> str | None:
        """Fuzzy-match a track name and return a suggestion string."""
        if not self.song or not self.song.tracks:
            return None

        existing = [t.name for t in self.song.tracks.values()]
        matches = difflib.get_close_matches(name, existing, n=1, cutoff=0.4)
        if matches:
            return f"Did you mean '{matches[0]}'?"
        return f"Available tracks: {', '.join(existing)}"

    # ------------------------------------------------------------------
    # Selector resolution
    # ------------------------------------------------------------------

    def _resolve_selectors(self, selectors: list[Selector]) -> list[Note] | str:
        """Resolve selectors into a list of notes via the registry."""
        assert self.song is not None

        if not selectors:
            return format_result(False, "No selectors specified",
                                 "Use @track:NAME, @range:M.B-M.B, @pitch:P, @all, etc.")

        # Build filter kwargs for registry.search()
        track_name: str | None = None
        pitch_midi: int | None = None
        range_start: int | None = None
        range_end: int | None = None
        channel: int | None = None
        vel_low: int | None = None
        vel_high: int | None = None
        use_all = False
        use_recent: int | None = None

        for sel in selectors:
            if sel.type == "track":
                track_name = sel.value
            elif sel.type == "channel":
                try:
                    channel = int(sel.value)
                except ValueError:
                    return format_result(False, f"Invalid channel: {sel.value!r}")
            elif sel.type == "range":
                # Format: M.B-M.B
                range_parts = sel.value.split("-")
                if len(range_parts) != 2:
                    return format_result(False, f"Invalid range: {sel.value!r}", "@range:1.1-4.4")
                try:
                    range_start = parse_position(
                        range_parts[0], self.song.time_signatures, self.song.ppqn
                    )
                    range_end = parse_position(
                        range_parts[1], self.song.time_signatures, self.song.ppqn
                    )
                except ValueError as e:
                    return format_result(False, f"Invalid range position: {e}")
            elif sel.type == "pitch":
                try:
                    p = parse_pitch(sel.value)
                    pitch_midi = p.midi_number
                except ValueError as e:
                    return format_result(False, f"Invalid pitch: {e}")
            elif sel.type == "velocity":
                vel_parts = sel.value.split("-")
                if len(vel_parts) != 2:
                    return format_result(False, f"Invalid velocity range: {sel.value!r}")
                try:
                    vel_low = int(vel_parts[0])
                    vel_high = int(vel_parts[1])
                except ValueError:
                    return format_result(False, f"Invalid velocity values: {sel.value!r}")
            elif sel.type == "all":
                use_all = True
            elif sel.type == "recent":
                use_recent = int(sel.value) if sel.value else 1

        # Handle @recent: get note IDs from recent events
        if use_recent is not None:
            events = self.event_log.recent(use_recent)
            note_ids = set()
            for ev in events:
                if hasattr(ev, "note_id"):
                    note_ids.add(ev.note_id)
            # Find matching notes across all tracks
            notes = []
            for track in self.song.tracks.values():
                for nid, note in track.notes.items():
                    if nid in note_ids:
                        notes.append(note)
            return notes

        if use_all:
            return self.registry.search()

        return self.registry.search(
            track=track_name,
            pitch=pitch_midi,
            range_start=range_start,
            range_end=range_end,
            channel=channel,
            vel_low=vel_low,
            vel_high=vel_high,
        )

    # ------------------------------------------------------------------
    # Query handlers
    # ------------------------------------------------------------------

    def _query_events(self, args: str) -> str:
        assert self.song is not None
        parts = args.strip().split()
        if not parts:
            return "! Missing track name.\n  try: events Piano or events Piano 1.1-4.4"

        track_name = parts[0]
        track = self.song.get_track_by_name(track_name)
        if not track:
            suggestion = self._suggest_track_name(track_name)
            msg = f"Track '{track_name}' not found"
            if suggestion:
                msg += f"\n  try: {suggestion}"
            return f"! {msg}"

        start_tick = None
        end_tick = None
        if len(parts) > 1:
            range_str = parts[1]
            range_parts = range_str.split("-")
            if len(range_parts) == 2:
                try:
                    start_tick = parse_position(
                        range_parts[0], self.song.time_signatures, self.song.ppqn
                    )
                    end_tick = parse_position(
                        range_parts[1], self.song.time_signatures, self.song.ppqn
                    )
                except ValueError as e:
                    return f"! Invalid range: {e}"

        return format_events(track, self.song, start_tick, end_tick)

    def _query_describe(self, args: str) -> str:
        assert self.song is not None
        track_name = args.strip()
        if not track_name:
            return "! Missing track name.\n  try: describe Piano"

        track = self.song.get_track_by_name(track_name)
        if not track:
            suggestion = self._suggest_track_name(track_name)
            msg = f"Track '{track_name}' not found"
            if suggestion:
                msg += f"\n  try: {suggestion}"
            return f"! {msg}"

        return format_describe(track, self.song)

    def _query_status(self) -> str:
        assert self.song is not None
        title = self.song.title
        path = self.song.file_path or "(unsaved)"
        n_events = self.event_log.cursor
        return f"Session: {title}\n  File: {path}\n  Events in log: {n_events}"

    def _query_find(self, args: str) -> str:
        assert self.song is not None
        pitch_str = args.strip()
        if not pitch_str:
            return "! Missing pitch.\n  try: find C4"

        try:
            pitch = parse_pitch(pitch_str)
        except ValueError as e:
            return f"! Invalid pitch: {e}"

        notes = self.registry.by_pitch(pitch.midi_number)
        if not notes:
            return f"No notes matching {pitch_str}."

        lines = [f"Found {len(notes)} note(s) matching {pitch_str}:"]
        for note in sorted(notes, key=lambda n: n.absolute_tick):
            pos = ticks_to_position(note.absolute_tick, self.song.time_signatures, self.song.ppqn)
            # Find track name
            track = self.song.tracks.get(note.track_id)
            track_name = track.name if track else "?"
            lines.append(f"  {pos}  {track_name}  vel:{note.velocity}")

        return "\n".join(lines)

    def _query_piano_roll(self, args: str) -> str:
        assert self.song is not None
        parts = args.strip().split()
        if len(parts) < 2:
            return "! Usage: piano-roll TRACK M.B-M.B\n  try: piano-roll Piano 1.1-8.4"

        track_name = parts[0]
        track = self.song.get_track_by_name(track_name)
        if not track:
            suggestion = self._suggest_track_name(track_name)
            msg = f"Track '{track_name}' not found"
            if suggestion:
                msg += f"\n  try: {suggestion}"
            return f"! {msg}"

        range_str = parts[1]
        range_parts = range_str.split("-")
        if len(range_parts) != 2:
            return "! Invalid range format.\n  try: piano-roll Piano 1.1-8.4"

        try:
            start_tick = parse_position(
                range_parts[0], self.song.time_signatures, self.song.ppqn
            )
            end_tick = parse_position(
                range_parts[1], self.song.time_signatures, self.song.ppqn
            )
        except ValueError as e:
            return f"! Invalid range: {e}"

        return format_piano_roll(track, self.song, start_tick, end_tick)

    def _query_history(self, args: str) -> str:
        count_str = args.strip()
        try:
            count = int(count_str) if count_str else 5
        except ValueError:
            count = 5

        events = self.event_log.recent(count)
        if not events:
            return "No events in log."

        lines = [f"Last {len(events)} event(s):"]
        for ev in events:
            lines.append(f"  {ev.type}: {_format_event_summary(ev)}")
        return "\n".join(lines)

    def _query_diff(self, args: str) -> str:
        assert self.song is not None
        # args: "checkpoint:NAME"
        args = args.strip()
        if args.startswith("checkpoint:"):
            cp_name = args[len("checkpoint:"):]
        else:
            return "! Usage: diff checkpoint:NAME"

        # Get all events from checkpoint to current cursor
        events = self.event_log.events
        cp_events = [e for e in events if isinstance(e, CheckpointEvent) and e.name == cp_name]
        if not cp_events:
            return f"! Checkpoint '{cp_name}' not found."

        # Find the position of the checkpoint in the events list
        cp_idx = None
        for i, ev in enumerate(events):
            if isinstance(ev, CheckpointEvent) and ev.name == cp_name:
                cp_idx = i
                break

        if cp_idx is None:
            return f"! Checkpoint '{cp_name}' not found."

        # Events after the checkpoint
        post_events = [e for e in events[cp_idx + 1:self.event_log.cursor]
                       if not isinstance(e, CheckpointEvent)]
        if not post_events:
            return f"No changes since checkpoint '{cp_name}'."

        lines = [f"Changes since checkpoint '{cp_name}' ({len(post_events)}):"]
        for ev in post_events:
            lines.append(f"  {ev.type}: {_format_event_summary(ev)}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Session handlers
    # ------------------------------------------------------------------

    def _session_new(self, args: list[str]) -> str:
        # First positional arg is the title (may be quoted)
        title = "Untitled"
        tempo = 120.0
        time_sig = (4, 4)
        key: str | None = None
        ppqn = 480

        positional: list[str] = []
        for arg in args:
            if ":" in arg and not arg.startswith('"') and not arg.startswith("'"):
                k, _, v = arg.partition(":")
                k = k.lower()
                if k == "tempo":
                    try:
                        tempo = float(v)
                    except ValueError:
                        return format_result(False, f"Invalid tempo: {v!r}")
                elif k == "time-sig":
                    m = re.match(r"^(\d+)/(\d+)$", v)
                    if m:
                        time_sig = (int(m.group(1)), int(m.group(2)))
                    else:
                        return format_result(False, f"Invalid time-sig: {v!r}")
                elif k == "key":
                    key = v
                elif k == "ppqn":
                    try:
                        ppqn = int(v)
                    except ValueError:
                        return format_result(False, f"Invalid ppqn: {v!r}")
            else:
                positional.append(arg)

        if positional:
            title = positional[0]

        self.song = Song.create(title=title, tempo=tempo, time_sig=time_sig, key=key, ppqn=ppqn)
        self.event_log = EventLog()
        self.registry = Registry()

        parts = [f"tempo:{tempo:.0f}", f"{time_sig[0]}/{time_sig[1]}"]
        if key:
            parts.append(key)
        return format_result(True, f"New song '{title}' ({', '.join(parts)}, ppqn:{ppqn})")

    def _session_open(self, args: list[str]) -> str:
        if not args:
            return format_result(False, "Missing file path", "open ./file.mid")

        path = args[0]

        try:
            from fcp_midi.serialization import deserialize
            self.song = deserialize(path)
            self.event_log = EventLog()
            self.registry = Registry()
            self.registry.rebuild(self.song)
            return format_result(True, f"Opened '{path}'")
        except ImportError:
            return format_result(
                False,
                "Serialization module not available yet (import/export in progress)",
            )
        except Exception as e:
            return format_result(False, f"Failed to open '{path}': {e}")

    def _session_save(self, args: list[str]) -> str:
        if self.song is None:
            return format_result(False, "No song to save")

        path = None
        for arg in args:
            if arg.startswith("as:"):
                path = arg[3:]
            elif not arg.startswith("-"):
                path = arg

        if path:
            self.song.file_path = path
        elif not self.song.file_path:
            return format_result(False, "No file path set", 'save as:./my-song.mid')

        try:
            from fcp_midi.serialization import serialize
            serialize(self.song, self.song.file_path)
            return format_result(True, f"Saved to '{self.song.file_path}'")
        except ImportError:
            return format_result(
                False,
                "Serialization module not available yet (import/export in progress)",
            )
        except Exception as e:
            return format_result(False, f"Failed to save: {e}")

    def _session_checkpoint(self, args: list[str]) -> str:
        if not args:
            return format_result(False, "Missing checkpoint name", "checkpoint v1")

        name = args[0]
        self.event_log.checkpoint(name)
        return format_result(True, f"Checkpoint '{name}' created (at event #{self.event_log.cursor})")

    def _session_undo(self, args: list[str]) -> str:
        if self.song is None:
            return format_result(False, "No song loaded")

        # Check for "to:NAME"
        to_name = None
        for arg in args:
            if arg.startswith("to:"):
                to_name = arg[3:]

        try:
            if to_name:
                reversed_events = self.event_log.undo_to(to_name)
            else:
                reversed_events = self.event_log.undo()
        except KeyError as e:
            return format_result(False, str(e))

        if not reversed_events:
            return format_result(False, "Nothing to undo")

        # Reverse the events on the model
        for ev in reversed_events:
            self._reverse_event(ev)

        self.registry.rebuild(self.song)
        count = len(reversed_events)
        if to_name:
            return format_result(True, f"Undone {count} event(s) to checkpoint '{to_name}'")
        return format_result(True, f"Undone {count} event(s)")

    def _session_redo(self, args: list[str]) -> str:
        if self.song is None:
            return format_result(False, "No song loaded")

        replayed = self.event_log.redo()
        if not replayed:
            return format_result(False, "Nothing to redo")

        for ev in replayed:
            self._replay_event(ev)

        self.registry.rebuild(self.song)
        return format_result(True, f"Redone {len(replayed)} event(s)")

    # ------------------------------------------------------------------
    # Undo / Redo event reversal + replay
    # ------------------------------------------------------------------

    def _reverse_event(self, ev: object) -> None:
        """Reverse a single event on the model."""
        assert self.song is not None

        if isinstance(ev, NoteAdded):
            self.song.remove_note(ev.track_id, ev.note_id)
        elif isinstance(ev, NoteRemoved):
            # NoteRemoved undo requires re-adding; we stored in stash
            # For now, just log that reversal is imperfect
            pass
        elif isinstance(ev, NoteModified):
            # Restore old value
            for track in self.song.tracks.values():
                note = track.notes.get(ev.note_id)
                if note:
                    setattr(note, ev.field_name, ev.old_value)
                    break
        elif isinstance(ev, TrackAdded):
            self.song.remove_track(ev.track_id)
        elif isinstance(ev, TrackRemoved):
            pass  # Would need stashed track data
        elif isinstance(ev, CCAdded):
            track = self.song.tracks.get(ev.track_id)
            if track:
                track.control_changes.pop(ev.cc_id, None)
        elif isinstance(ev, PitchBendAdded):
            track = self.song.tracks.get(ev.track_id)
            if track:
                track.pitch_bends.pop(ev.pb_id, None)
        elif isinstance(ev, TempoChanged):
            # Remove the tempo entry that was added
            self.song.tempo_map = [
                t for t in self.song.tempo_map
                if not (t.absolute_tick == ev.absolute_tick and t.bpm == ev.new_bpm)
            ]
            if not self.song.tempo_map:
                from fcp_midi.model.song import TempoChange
                self.song.tempo_map = [TempoChange(absolute_tick=0, bpm=ev.old_bpm)]
        elif isinstance(ev, TimeSignatureChanged):
            self.song.time_signatures = [
                ts for ts in self.song.time_signatures
                if not (ts.absolute_tick == ev.absolute_tick
                        and ts.numerator == ev.new_numerator
                        and ts.denominator == ev.new_denominator)
            ]
            if not self.song.time_signatures:
                from fcp_midi.model.song import TimeSignature
                self.song.time_signatures = [
                    TimeSignature(absolute_tick=0,
                                  numerator=ev.old_numerator,
                                  denominator=ev.old_denominator)
                ]
        elif isinstance(ev, MarkerAdded):
            self.song.markers = [
                m for m in self.song.markers
                if not (m.absolute_tick == ev.absolute_tick and m.text == ev.text)
            ]

    def _replay_event(self, ev: object) -> None:
        """Replay a single event forward on the model."""
        assert self.song is not None

        if isinstance(ev, NoteAdded):
            # We need the note data -- for redo after undo of a NoteAdded,
            # the note was removed. We need to have stored it.
            # For a simple redo, we just note that the event_log cursor advanced.
            # Full redo requires a snapshot approach; for now we handle the common case.
            pass
        elif isinstance(ev, NoteRemoved):
            self.song.remove_note(ev.track_id, ev.note_id)
        elif isinstance(ev, NoteModified):
            for track in self.song.tracks.values():
                note = track.notes.get(ev.note_id)
                if note:
                    setattr(note, ev.field_name, ev.new_value)
                    break
        elif isinstance(ev, TrackAdded):
            pass  # Would need stashed track data
        elif isinstance(ev, TrackRemoved):
            self.song.remove_track(ev.track_id)
        elif isinstance(ev, CCAdded):
            pass  # Would need stashed CC data
        elif isinstance(ev, PitchBendAdded):
            pass  # Would need stashed PB data
        elif isinstance(ev, TempoChanged):
            self.song.add_tempo(ev.new_bpm, ev.absolute_tick)
        elif isinstance(ev, TimeSignatureChanged):
            self.song.add_time_signature(
                ev.new_numerator, ev.new_denominator, ev.absolute_tick
            )
        elif isinstance(ev, MarkerAdded):
            self.song.add_marker(ev.text, ev.absolute_tick)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _pitch_from_midi(midi_number: int) -> Pitch:
    """Create a Pitch from a raw MIDI number (uses sharps for black keys)."""
    from fcp_midi.parser.pitch import _MIDI_TO_NOTE
    note_in_octave = midi_number % 12
    octave = (midi_number // 12) - 1
    name, accidental = _MIDI_TO_NOTE[note_in_octave]
    return Pitch(
        name=name,
        accidental=accidental,
        octave=octave,
        midi_number=midi_number,
    )


def _format_event_summary(ev: object) -> str:
    """One-line summary of an event for history/diff output."""
    if hasattr(ev, "note_id"):
        track_id = getattr(ev, "track_id", "?")
        note_id = getattr(ev, "note_id", "?")
        return f"track={track_id[:6]} note={note_id[:6]}"
    if hasattr(ev, "track_id"):
        return f"track={getattr(ev, 'track_id', '?')[:6]}"
    if hasattr(ev, "new_bpm"):
        return f"{getattr(ev, 'new_bpm', 0):.0f} BPM"
    if hasattr(ev, "text"):
        return f"'{getattr(ev, 'text', '')}'"
    if hasattr(ev, "new_numerator"):
        return f"{getattr(ev, 'new_numerator')}/{getattr(ev, 'new_denominator')}"
    return ""


def _tokenize_session(action: str) -> list[str]:
    """Tokenize a session action string, respecting quotes."""
    import shlex
    try:
        return shlex.split(action)
    except ValueError:
        return action.split()
