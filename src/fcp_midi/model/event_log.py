"""Event log with undo/redo and named checkpoints.

Domain event types are defined here (tagged union via ``type`` discriminant).
The EventLog class wraps ``fcp_core.EventLog`` with domain-specific
behaviour (KeyError on missing checkpoint, ``.events`` property).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fcp_core import EventLog as _CoreEventLog

if TYPE_CHECKING:
    from fcp_midi.model.song import ControlChange, Note, PitchBend, Track


# ---------------------------------------------------------------------------
# Event types (tagged union via ``type`` discriminant)
# ---------------------------------------------------------------------------

@dataclass
class NoteAdded:
    type: str = field(default="note_added", init=False)
    track_id: str = ""
    note_id: str = ""
    note_snapshot: Note | None = None


@dataclass
class NoteRemoved:
    type: str = field(default="note_removed", init=False)
    track_id: str = ""
    note_id: str = ""
    note_snapshot: Note | None = None


@dataclass
class NoteModified:
    type: str = field(default="note_modified", init=False)
    track_id: str = ""
    note_id: str = ""
    field_name: str = ""
    old_value: object = None
    new_value: object = None


@dataclass
class TrackAdded:
    type: str = field(default="track_added", init=False)
    track_id: str = ""
    track_snapshot: Track | None = None


@dataclass
class TrackRemoved:
    type: str = field(default="track_removed", init=False)
    track_id: str = ""
    track_snapshot: Track | None = None


@dataclass
class TrackRenamed:
    type: str = field(default="track_renamed", init=False)
    track_id: str = ""
    old_name: str = ""
    new_name: str = ""


@dataclass
class CCAdded:
    type: str = field(default="cc_added", init=False)
    track_id: str = ""
    cc_id: str = ""
    cc_snapshot: ControlChange | None = None


@dataclass
class PitchBendAdded:
    type: str = field(default="pitch_bend_added", init=False)
    track_id: str = ""
    pb_id: str = ""
    pb_snapshot: PitchBend | None = None


@dataclass
class TempoChanged:
    type: str = field(default="tempo_changed", init=False)
    old_bpm: float = 120.0
    new_bpm: float = 120.0
    absolute_tick: int = 0


@dataclass
class TimeSignatureChanged:
    type: str = field(default="time_signature_changed", init=False)
    old_numerator: int = 4
    old_denominator: int = 4
    new_numerator: int = 4
    new_denominator: int = 4
    absolute_tick: int = 0


@dataclass
class KeySignatureChanged:
    type: str = field(default="key_signature_changed", init=False)
    old_key: str = "C"
    old_mode: str = "major"
    new_key: str = "C"
    new_mode: str = "major"
    absolute_tick: int = 0


@dataclass
class MarkerAdded:
    type: str = field(default="marker_added", init=False)
    text: str = ""
    absolute_tick: int = 0


@dataclass
class CheckpointEvent:
    """Sentinel stored in the log so checkpoints survive serialisation."""
    type: str = field(default="checkpoint", init=False)
    name: str = ""


# Convenience alias
Event = (
    NoteAdded
    | NoteRemoved
    | NoteModified
    | TrackAdded
    | TrackRemoved
    | TrackRenamed
    | CCAdded
    | PitchBendAdded
    | TempoChanged
    | TimeSignatureChanged
    | KeySignatureChanged
    | MarkerAdded
    | CheckpointEvent
)


# ---------------------------------------------------------------------------
# EventLog — wraps fcp_core.EventLog with domain compatibility
# ---------------------------------------------------------------------------

class EventLog:
    """Linear event log with cursor-based undo/redo and named checkpoints.

    Wraps ``fcp_core.EventLog`` and adds:
    - ``.events`` property returning the full event list up to cursor
    - ``undo_to()`` raises ``KeyError`` on missing checkpoint (vs returning None)
    """

    def __init__(self) -> None:
        self._core = _CoreEventLog()
        # Keep a parallel list for the .events property since the core
        # EventLog doesn't expose its internal list.
        self._events: list[Event] = []

    @property
    def cursor(self) -> int:
        return self._core.cursor

    @property
    def events(self) -> list[Event]:
        return list(self._events[:self._core.cursor])

    def append(self, event: Event) -> None:
        """Add *event* at cursor position, truncating any redo tail."""
        cursor = self._core.cursor
        if cursor < len(self._events):
            self._events = self._events[:cursor]
        self._events.append(event)
        self._core.append(event)

    def checkpoint(self, name: str) -> None:
        """Record the current cursor position under *name* and append a
        ``CheckpointEvent`` so the log is self-describing."""
        cp_event = CheckpointEvent(name=name)
        cursor = self._core.cursor
        if cursor < len(self._events):
            self._events = self._events[:cursor]
        self._events.append(cp_event)
        self._core.checkpoint(name)

    def undo(self, count: int = 1) -> list[Event]:
        """Move cursor back by *count* applied events (skipping checkpoints)
        and return the events that should be reversed, most-recent-first."""
        return self._core.undo(count)

    def undo_to(self, name: str) -> list[Event]:
        """Undo back to the named checkpoint, returning events most-recent-first.

        Raises ``KeyError`` if the checkpoint is not found.
        """
        result = self._core.undo_to(name)
        if result is None:
            raise KeyError(f"No checkpoint named {name!r}")
        return result

    def redo(self, count: int = 1) -> list[Event]:
        """Replay up to *count* events forward from cursor (skipping
        checkpoint sentinels). Returns events in forward order."""
        return self._core.redo(count)

    def recent(self, count: int = 5) -> list[Event]:
        """Return the last *count* non-checkpoint events up to the cursor,
        in chronological (oldest-first) order."""
        return self._core.recent(count)
