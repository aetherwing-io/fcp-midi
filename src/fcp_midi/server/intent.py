"""Intent dispatch layer — thin facade delegating to focused handler modules."""

from __future__ import annotations

from fcp_midi.lib.instrument_registry import InstrumentRegistry
from fcp_midi.model.event_log import EventLog
from fcp_midi.model.registry import Registry
from fcp_midi.model.song import Song
from fcp_midi.errors import FcpError
from fcp_midi.parser.ops import ParsedOp, ParseError, parse_op
from fcp_midi.server.formatter import format_result
from fcp_midi.server.ops_editing import detect_gaps
from fcp_midi.server.resolvers import OpContext
from fcp_midi.server.sessions import dispatch_session, reverse_event


class IntentLayer:
    """Core orchestration: parse ops, dispatch to model, format responses."""

    def __init__(self) -> None:
        self.song: Song | None = None
        self.event_log: EventLog = EventLog()
        self.registry: Registry = Registry()
        self.instrument_registry: InstrumentRegistry = InstrumentRegistry()
        self._last_tick: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_ops(self, ops: list[str]) -> list[str]:
        """Execute a batch of mutation ops, return formatted results.

        If any op fails (returns a "!" error), all preceding ops in the
        batch are rolled back to maintain atomicity.
        """
        if self.song is None:
            return [self._execute_single_op(op) for op in ops]

        batch_cp = f"__batch_{id(ops)}"
        self.event_log.checkpoint(batch_cp)

        results: list[str] = []
        failed = False
        for op_str in ops:
            result = self._execute_single_op(op_str)
            results.append(result)
            if result.startswith("!"):
                failed = True
                break

        if failed:
            try:
                reversed_evts = self.event_log.undo_to(batch_cp)
                for ev in reversed_evts:
                    reverse_event(ev, self.song)
                self.registry.rebuild(self.song)
            except KeyError:
                pass

        if self.song:
            results.append(self.song.get_digest())
            gaps = detect_gaps(self.song)
            if gaps:
                results.extend(gaps)
        return results

    def execute_query(self, q: str) -> str:
        """Execute a read-only query and return formatted output."""
        if self.song is None:
            return "! No song loaded. Use midi_session to create or open one."

        from fcp_midi.server.queries import dispatch_query
        ctx = self._make_context()
        return dispatch_query(q, ctx)

    def execute_session(self, action: str) -> str:
        """Execute a session lifecycle action."""
        return dispatch_session(action, self)

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
        except (FcpError, ValueError) as exc:
            return format_result(False, f"Error: {exc}")

    def _dispatch_op(self, op: ParsedOp) -> str:
        """Route a parsed op to the appropriate handler."""
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

        ctx = self._make_context()
        result = handler(op, ctx)
        self._sync_from_context(ctx)
        return result

    # ------------------------------------------------------------------
    # Context bridge
    # ------------------------------------------------------------------

    def _make_context(self) -> OpContext:
        """Build an OpContext from current state."""
        assert self.song is not None
        return OpContext(
            song=self.song,
            event_log=self.event_log,
            registry=self.registry,
            last_tick=self._last_tick,
            instrument_registry=self.instrument_registry,
        )

    def _sync_from_context(self, ctx: OpContext) -> None:
        """Sync mutable state back from OpContext after a handler runs."""
        self._last_tick = ctx.last_tick
