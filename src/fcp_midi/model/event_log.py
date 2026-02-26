"""Event log with undo/redo and named checkpoints.

Events form a tagged union via a ``type`` string discriminant on each
dataclass.  The log is cursor-based: ``cursor`` always points one past
the last *applied* event.  Appending a new event when cursor < len
truncates the redo tail.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Event types (tagged union via ``type`` discriminant)
# ---------------------------------------------------------------------------

@dataclass
class NoteAdded:
    type: str = field(default="note_added", init=False)
    track_id: str = ""
    note_id: str = ""


@dataclass
class NoteRemoved:
    type: str = field(default="note_removed", init=False)
    track_id: str = ""
    note_id: str = ""


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


@dataclass
class TrackRemoved:
    type: str = field(default="track_removed", init=False)
    track_id: str = ""


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


@dataclass
class PitchBendAdded:
    type: str = field(default="pitch_bend_added", init=False)
    track_id: str = ""
    pb_id: str = ""


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
# EventLog
# ---------------------------------------------------------------------------

class EventLog:
    """Linear event log with cursor-based undo/redo and named checkpoints."""

    def __init__(self) -> None:
        self._events: list[Event] = []
        self._cursor: int = 0  # points past last applied event
        self._checkpoints: dict[str, int] = {}

    # -- properties ----------------------------------------------------------

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def events(self) -> list[Event]:
        return list(self._events)

    # -- mutation ------------------------------------------------------------

    def append(self, event: Event) -> None:
        """Add *event* at cursor position, truncating any redo tail."""
        # Truncate redo history
        if self._cursor < len(self._events):
            self._events = self._events[: self._cursor]
            # Invalidate checkpoints beyond the new end
            self._checkpoints = {
                name: pos
                for name, pos in self._checkpoints.items()
                if pos <= self._cursor
            }
        self._events.append(event)
        self._cursor += 1

    def checkpoint(self, name: str) -> None:
        """Record the current cursor position under *name* and append a
        ``CheckpointEvent`` so the log is self-describing."""
        self._checkpoints[name] = self._cursor
        self.append(CheckpointEvent(name=name))

    # -- undo / redo ---------------------------------------------------------

    def undo(self, count: int = 1) -> list[Event]:
        """Move cursor back by *count* applied events (skipping checkpoints)
        and return the events that should be reversed, most-recent-first."""
        reversed_events: list[Event] = []
        remaining = count
        while remaining > 0 and self._cursor > 0:
            self._cursor -= 1
            ev = self._events[self._cursor]
            if isinstance(ev, CheckpointEvent):
                # skip checkpoint sentinels — they don't count
                continue
            reversed_events.append(ev)
            remaining -= 1
        return reversed_events

    def undo_to(self, name: str) -> list[Event]:
        """Undo back to the named checkpoint, returning events most-recent-first.

        The cursor lands at the checkpoint position (i.e. the checkpoint's
        ``CheckpointEvent`` itself is *not* undone).
        """
        target = self._checkpoints.get(name)
        if target is None:
            raise KeyError(f"No checkpoint named {name!r}")
        reversed_events: list[Event] = []
        while self._cursor > target:
            self._cursor -= 1
            ev = self._events[self._cursor]
            if not isinstance(ev, CheckpointEvent):
                reversed_events.append(ev)
        return reversed_events

    def redo(self, count: int = 1) -> list[Event]:
        """Replay up to *count* events forward from cursor (skipping
        checkpoint sentinels).  Returns events in forward order."""
        replayed: list[Event] = []
        remaining = count
        while remaining > 0 and self._cursor < len(self._events):
            ev = self._events[self._cursor]
            self._cursor += 1
            if isinstance(ev, CheckpointEvent):
                continue
            replayed.append(ev)
            remaining -= 1
        return replayed

    # -- queries -------------------------------------------------------------

    def recent(self, count: int = 5) -> list[Event]:
        """Return the last *count* non-checkpoint events up to the cursor,
        in chronological (oldest-first) order."""
        result: list[Event] = []
        idx = self._cursor - 1
        while len(result) < count and idx >= 0:
            ev = self._events[idx]
            if not isinstance(ev, CheckpointEvent):
                result.append(ev)
            idx -= 1
        result.reverse()
        return result
