"""Session lifecycle handlers: new, open, save, checkpoint, undo, redo."""

from __future__ import annotations

import re
import shlex
from typing import TYPE_CHECKING

from fcp_midi.model.event_log import (
    CCAdded,
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
from fcp_midi.model.song import Song
from fcp_midi.server.formatter import format_result

if TYPE_CHECKING:
    from fcp_midi.server.intent import IntentLayer


def dispatch_session(action: str, intent: IntentLayer) -> str:
    """Route a session action string to the appropriate handler."""
    action = action.strip()
    parts_raw = tokenize_session(action)
    command = parts_raw[0].lower() if parts_raw else ""
    rest = parts_raw[1:]

    if command == "new":
        return _session_new(rest, intent)
    elif command == "open":
        return _session_open(rest, intent)
    elif command == "save":
        return _session_save(rest, intent)
    elif command == "checkpoint":
        return _session_checkpoint(rest, intent)
    elif command == "undo":
        return _session_undo(rest, intent)
    elif command == "redo":
        return _session_redo(rest, intent)
    elif command == "load-soundfont":
        return _session_load_soundfont(rest, intent)
    else:
        return f"! Unknown session action: {command!r}\n  try: new, open, save, checkpoint, undo, redo, load-soundfont"


def _session_new(args: list[str], intent: IntentLayer) -> str:
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

    intent.song = Song.create(title=title, tempo=tempo, time_sig=time_sig, key=key, ppqn=ppqn)
    intent.event_log = EventLog()
    intent.registry = Registry()

    parts = [f"tempo:{tempo:.0f}", f"{time_sig[0]}/{time_sig[1]}"]
    if key:
        parts.append(key)
    return format_result(True, f"New song '{title}' ({', '.join(parts)}, ppqn:{ppqn})")


def _session_open(args: list[str], intent: IntentLayer) -> str:
    if not args:
        return format_result(False, "Missing file path", "open ./file.mid")

    path = args[0]

    try:
        from fcp_midi.serialization.deserialize import deserialize
        intent.song = deserialize(path)
        intent.event_log = EventLog()
        intent.registry = Registry()
        intent.registry.rebuild(intent.song)
        return format_result(True, f"Opened '{path}'")
    except ImportError:
        return format_result(
            False,
            "Serialization module not available yet (import/export in progress)",
        )
    except Exception as e:
        return format_result(False, f"Failed to open '{path}': {e}")


def _session_save(args: list[str], intent: IntentLayer) -> str:
    if intent.song is None:
        return format_result(False, "No song to save")

    path = None
    for arg in args:
        if arg.startswith("as:"):
            path = arg[3:]
        elif not arg.startswith("-"):
            path = arg

    if path:
        intent.song.file_path = path
    elif not intent.song.file_path:
        return format_result(False, "No file path set", 'save as:./my-song.mid')

    try:
        from fcp_midi.serialization.serialize import serialize
        serialize(intent.song, intent.song.file_path)
        return format_result(True, f"Saved to '{intent.song.file_path}'")
    except ImportError:
        return format_result(
            False,
            "Serialization module not available yet (import/export in progress)",
        )
    except Exception as e:
        return format_result(False, f"Failed to save: {e}")


def _session_checkpoint(args: list[str], intent: IntentLayer) -> str:
    if not args:
        return format_result(False, "Missing checkpoint name", "checkpoint v1")

    name = args[0]
    intent.event_log.checkpoint(name)
    return format_result(True, f"Checkpoint '{name}' created (at event #{intent.event_log.cursor})")


def _session_undo(args: list[str], intent: IntentLayer) -> str:
    if intent.song is None:
        return format_result(False, "No song loaded")

    to_name = None
    for arg in args:
        if arg.startswith("to:"):
            to_name = arg[3:]

    try:
        if to_name:
            reversed_events = intent.event_log.undo_to(to_name)
        else:
            reversed_events = intent.event_log.undo()
    except KeyError as e:
        return format_result(False, str(e))

    if not reversed_events:
        return format_result(False, "Nothing to undo")

    for ev in reversed_events:
        reverse_event(ev, intent.song)

    intent.registry.rebuild(intent.song)
    count = len(reversed_events)
    if to_name:
        return format_result(True, f"Undone {count} event(s) to checkpoint '{to_name}'")
    return format_result(True, f"Undone {count} event(s)")


def _session_redo(args: list[str], intent: IntentLayer) -> str:
    if intent.song is None:
        return format_result(False, "No song loaded")

    replayed = intent.event_log.redo()
    if not replayed:
        return format_result(False, "Nothing to redo")

    for ev in replayed:
        replay_event(ev, intent.song)

    intent.registry.rebuild(intent.song)
    return format_result(True, f"Redone {len(replayed)} event(s)")


def _session_load_soundfont(args: list[str], intent: IntentLayer) -> str:
    if not args:
        return format_result(False, "Missing file path", "load-soundfont ./file.sf2")

    path = args[0]
    try:
        count = intent.instrument_registry.load_soundfont(path)
        return format_result(True, f"Loaded {count} presets from {path}")
    except Exception as e:
        return format_result(False, f"Failed to load soundfont: {e}")


def reverse_event(ev: object, song: Song) -> None:
    """Reverse a single event on the model."""
    if isinstance(ev, NoteAdded):
        song.remove_note(ev.track_id, ev.note_id)
    elif isinstance(ev, NoteRemoved):
        if ev.note_snapshot is not None:
            track = song.tracks.get(ev.track_id)
            if track:
                track.notes[ev.note_snapshot.id] = ev.note_snapshot
    elif isinstance(ev, NoteModified):
        for track in song.tracks.values():
            note = track.notes.get(ev.note_id)
            if note:
                setattr(note, ev.field_name, ev.old_value)
                break
    elif isinstance(ev, TrackAdded):
        song.remove_track(ev.track_id)
    elif isinstance(ev, TrackRemoved):
        if ev.track_snapshot is not None:
            song.tracks[ev.track_id] = ev.track_snapshot
            if ev.track_id not in song.track_order:
                song.track_order.append(ev.track_id)
    elif isinstance(ev, CCAdded):
        track = song.tracks.get(ev.track_id)
        if track:
            track.control_changes.pop(ev.cc_id, None)
    elif isinstance(ev, PitchBendAdded):
        track = song.tracks.get(ev.track_id)
        if track:
            track.pitch_bends.pop(ev.pb_id, None)
    elif isinstance(ev, TempoChanged):
        song.tempo_map = [
            t for t in song.tempo_map
            if not (t.absolute_tick == ev.absolute_tick and t.bpm == ev.new_bpm)
        ]
        if not song.tempo_map:
            from fcp_midi.model.song import TempoChange
            song.tempo_map = [TempoChange(absolute_tick=0, bpm=ev.old_bpm)]
    elif isinstance(ev, TimeSignatureChanged):
        song.time_signatures = [
            ts for ts in song.time_signatures
            if not (ts.absolute_tick == ev.absolute_tick
                    and ts.numerator == ev.new_numerator
                    and ts.denominator == ev.new_denominator)
        ]
        if not song.time_signatures:
            from fcp_midi.model.song import TimeSignature
            song.time_signatures = [
                TimeSignature(absolute_tick=0,
                              numerator=ev.old_numerator,
                              denominator=ev.old_denominator)
            ]
    elif isinstance(ev, KeySignatureChanged):
        song.key_signatures = [
            ks for ks in song.key_signatures
            if not (ks.absolute_tick == ev.absolute_tick
                    and ks.key == ev.new_key
                    and ks.mode == ev.new_mode)
        ]
        if not song.key_signatures:
            from fcp_midi.model.song import KeySignature
            song.key_signatures = [
                KeySignature(absolute_tick=0, key=ev.old_key, mode=ev.old_mode)
            ]
    elif isinstance(ev, MarkerAdded):
        song.markers = [
            m for m in song.markers
            if not (m.absolute_tick == ev.absolute_tick and m.text == ev.text)
        ]


def replay_event(ev: object, song: Song) -> None:
    """Replay a single event forward on the model."""
    if isinstance(ev, NoteAdded):
        if ev.note_snapshot is not None:
            track = song.tracks.get(ev.track_id)
            if track:
                track.notes[ev.note_snapshot.id] = ev.note_snapshot
    elif isinstance(ev, NoteRemoved):
        song.remove_note(ev.track_id, ev.note_id)
    elif isinstance(ev, NoteModified):
        for track in song.tracks.values():
            note = track.notes.get(ev.note_id)
            if note:
                setattr(note, ev.field_name, ev.new_value)
                break
    elif isinstance(ev, TrackAdded):
        if ev.track_snapshot is not None:
            song.tracks[ev.track_id] = ev.track_snapshot
            if ev.track_id not in song.track_order:
                song.track_order.append(ev.track_id)
    elif isinstance(ev, TrackRemoved):
        song.remove_track(ev.track_id)
    elif isinstance(ev, CCAdded):
        if ev.cc_snapshot is not None:
            track = song.tracks.get(ev.track_id)
            if track:
                track.control_changes[ev.cc_snapshot.id] = ev.cc_snapshot
    elif isinstance(ev, PitchBendAdded):
        if ev.pb_snapshot is not None:
            track = song.tracks.get(ev.track_id)
            if track:
                track.pitch_bends[ev.pb_snapshot.id] = ev.pb_snapshot
    elif isinstance(ev, TempoChanged):
        song.add_tempo(ev.new_bpm, ev.absolute_tick)
    elif isinstance(ev, TimeSignatureChanged):
        song.add_time_signature(
            ev.new_numerator, ev.new_denominator, ev.absolute_tick
        )
    elif isinstance(ev, KeySignatureChanged):
        song.add_key_signature(ev.new_key, ev.new_mode, ev.absolute_tick)
    elif isinstance(ev, MarkerAdded):
        song.add_marker(ev.text, ev.absolute_tick)


def tokenize_session(action: str) -> list[str]:
    """Tokenize a session action string, respecting quotes."""
    try:
        return shlex.split(action)
    except ValueError:
        return action.split()
