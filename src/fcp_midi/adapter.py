"""FcpDomainAdapter implementation for MIDI — bridges fcp-core to fcp-midi domain.

This adapter satisfies the ``FcpDomainAdapter[Song, Event]`` protocol
from fcp-core, delegating to the existing MIDI domain logic.
"""

from __future__ import annotations

import re

from fcp_core import EventLog as CoreEventLog
from fcp_core import OpResult, ParsedOp as GenericParsedOp

from fcp_midi.errors import FcpError
from fcp_midi.lib.instrument_registry import InstrumentRegistry
from fcp_midi.model.event_log import Event
from fcp_midi.model.registry import Registry
from fcp_midi.model.song import Song
from fcp_midi.parser.ops import ParsedOp as DomainParsedOp, ParseError, parse_op as domain_parse_op
from fcp_midi.parser.selector import Selector, parse_selectors
from fcp_midi.server.formatter import format_result
from fcp_midi.server.ops_editing import detect_gaps
from fcp_midi.server.resolvers import OpContext
from fcp_midi.server.sessions import reverse_event, replay_event


class MidiAdapter:
    """FcpDomainAdapter implementation for MIDI composition.

    Satisfies the ``FcpDomainAdapter[Song, Event]`` protocol required
    by ``create_fcp_server()``.
    """

    def __init__(self) -> None:
        self.registry: Registry = Registry()
        self.instrument_registry: InstrumentRegistry = InstrumentRegistry()
        self._last_tick: int = 0

    # -- FcpDomainAdapter protocol methods --

    def create_empty(self, title: str, params: dict[str, str]) -> Song:
        """Create a new empty Song from session params."""
        tempo = 120.0
        time_sig = (4, 4)
        key: str | None = None
        ppqn = 480

        if "tempo" in params:
            try:
                tempo = float(params["tempo"])
            except ValueError:
                pass  # will use default

        if "time-sig" in params:
            m = re.match(r"^(\d+)/(\d+)$", params["time-sig"])
            if m:
                time_sig = (int(m.group(1)), int(m.group(2)))

        if "key" in params:
            key = params["key"]

        if "ppqn" in params:
            try:
                ppqn = int(params["ppqn"])
            except ValueError:
                pass

        song = Song.create(title=title, tempo=tempo, time_sig=time_sig, key=key, ppqn=ppqn)
        self.registry = Registry()
        return song

    def serialize(self, model: Song, path: str) -> None:
        """Serialize the song to a MIDI file."""
        from fcp_midi.serialization.serialize import serialize
        serialize(model, path)

    def deserialize(self, path: str) -> Song:
        """Deserialize a Song from a MIDI file."""
        from fcp_midi.serialization.deserialize import deserialize
        return deserialize(path)

    def rebuild_indices(self, model: Song) -> None:
        """Rebuild the note registry from the song model."""
        self.registry.rebuild(model)

    def get_digest(self, model: Song) -> str:
        """Return a compact state fingerprint."""
        return model.get_digest()

    def dispatch_op(
        self,
        op: GenericParsedOp,
        model: Song,
        log: CoreEventLog,
    ) -> OpResult:
        """Execute a parsed operation on the song.

        Converts generic ParsedOp from fcp-core into the domain-specific
        ParsedOp, then delegates to the existing op handler pipeline.
        """
        # Re-parse through our domain parser to get domain-specific ParsedOp
        domain_parsed = domain_parse_op(op.raw)
        if isinstance(domain_parsed, ParseError):
            return OpResult(success=False, message=f"Parse error: {domain_parsed.error}")

        # Build an OpContext and dispatch
        ctx = self._make_context(model, log)
        try:
            result_str = self._dispatch_domain_op(domain_parsed, ctx)
            self._sync_from_context(ctx)
        except (FcpError, ValueError) as exc:
            return OpResult(success=False, message=f"Error: {exc}")

        # Parse the result string into OpResult
        if result_str.startswith("!"):
            return OpResult(success=False, message=result_str.lstrip("! "))
        prefix = ""
        if len(result_str) > 1 and result_str[1] == " ":
            prefix = result_str[0]
        message = result_str[2:] if prefix else result_str
        return OpResult(success=True, message=message, prefix=prefix)

    def dispatch_query(self, query: str, model: Song) -> str:
        """Execute a read-only query against the song."""
        from fcp_midi.server.queries import dispatch_query
        ctx = self._make_context(model)
        return dispatch_query(query, ctx)

    def reverse_event(self, event: Event, model: Song) -> None:
        """Reverse a single event (for undo)."""
        reverse_event(event, model)

    def replay_event(self, event: Event, model: Song) -> None:
        """Replay a single event (for redo)."""
        replay_event(event, model)

    # -- Internal helpers --

    def _make_context(self, song: Song, log: CoreEventLog | None = None) -> OpContext:
        """Build an OpContext from current state."""
        # Create a shim EventLog that wraps the core EventLog
        from fcp_midi.model.event_log import EventLog as DomainEventLog
        if log is not None:
            event_log = _CoreEventLogShim(log)
        else:
            event_log = DomainEventLog()
        return OpContext(
            song=song,
            event_log=event_log,
            registry=self.registry,
            last_tick=self._last_tick,
            instrument_registry=self.instrument_registry,
        )

    def _sync_from_context(self, ctx: OpContext) -> None:
        """Sync mutable state back from OpContext."""
        self._last_tick = ctx.last_tick

    def _dispatch_domain_op(self, op: DomainParsedOp, ctx: OpContext) -> str:
        """Route a domain-parsed op to the appropriate handler."""
        from fcp_midi.server.ops_music import (
            op_note, op_chord, op_track, op_cc, op_bend,
            op_mute, op_solo, op_program,
        )
        from fcp_midi.server.ops_meta import (
            op_tempo, op_time_sig, op_key_sig, op_marker, op_title,
        )
        from fcp_midi.server.ops_editing import (
            op_remove, op_move, op_copy, op_transpose, op_velocity,
            op_quantize, op_modify, op_repeat, op_crescendo,
        )

        handlers = {
            "note": op_note,
            "chord": op_chord,
            "track": op_track,
            "cc": op_cc,
            "bend": op_bend,
            "tempo": op_tempo,
            "time-sig": op_time_sig,
            "key-sig": op_key_sig,
            "marker": op_marker,
            "title": op_title,
            "remove": op_remove,
            "move": op_move,
            "copy": op_copy,
            "transpose": op_transpose,
            "velocity": op_velocity,
            "quantize": op_quantize,
            "mute": op_mute,
            "solo": op_solo,
            "program": op_program,
            "modify": op_modify,
            "repeat": op_repeat,
            "crescendo": op_crescendo,
            "decrescendo": op_crescendo,
        }
        handler = handlers.get(op.verb)
        if handler is None:
            return format_result(False, f"Unknown verb: {op.verb!r}")

        return handler(op, ctx)


class _CoreEventLogShim:
    """Wraps a fcp-core EventLog to satisfy the domain EventLog interface.

    The domain code (op handlers, resolvers) uses the EventLog interface with
    methods like .append(), .checkpoint(), .undo(), .redo(), .recent(), .cursor,
    and .events. This shim delegates to the core EventLog while maintaining
    compatibility with domain event types.
    """

    def __init__(self, core_log: CoreEventLog) -> None:
        self._core = core_log

    @property
    def cursor(self) -> int:
        return self._core.cursor

    @property
    def events(self) -> list:
        return self._core.recent(self._core.cursor)

    def append(self, event: Event) -> None:
        self._core.append(event)

    def checkpoint(self, name: str) -> None:
        self._core.checkpoint(name)

    def undo(self, count: int = 1) -> list:
        return self._core.undo(count)

    def undo_to(self, name: str) -> list:
        result = self._core.undo_to(name)
        if result is None:
            raise KeyError(f"No checkpoint named {name!r}")
        return result

    def redo(self, count: int = 1) -> list:
        return self._core.redo(count)

    def recent(self, count: int = 5) -> list:
        return self._core.recent(count)
