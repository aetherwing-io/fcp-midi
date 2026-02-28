"""FcpDomainAdapter implementation for mido-native MIDI — bridges fcp-core to MidiModel.

Satisfies ``FcpDomainAdapter[MidiModel, SnapshotEvent]``. Uses byte snapshots
for undo/redo instead of fine-grained event sourcing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fcp_core import EventLog as CoreEventLog
from fcp_core import OpResult, ParsedOp as GenericParsedOp

from fcp_midi.lib.instrument_registry import InstrumentRegistry
from fcp_midi.model.midi_model import MidiModel, NoteIndex
from fcp_midi.parser.ops import ParsedOp as DomainParsedOp, ParseError, parse_op as domain_parse_op
from fcp_midi.server.formatter import format_result
from fcp_midi.server.ops_context_v2 import MidiOpContext
from fcp_midi.server.queries_v2 import dispatch_query_v2


# ---------------------------------------------------------------------------
# SnapshotEvent — simple event type for byte-snapshot undo/redo
# ---------------------------------------------------------------------------

@dataclass
class SnapshotEvent:
    """Event type for byte-snapshot undo/redo."""

    type: str = "snapshot"
    before: bytes = b""
    after: bytes = b""
    summary: str = ""


# ---------------------------------------------------------------------------
# MidiAdapterV2
# ---------------------------------------------------------------------------

class MidiAdapterV2:
    """FcpDomainAdapter implementation for mido-native MIDI composition.

    Satisfies ``FcpDomainAdapter[MidiModel, SnapshotEvent]``.
    """

    def __init__(self) -> None:
        self.note_index: NoteIndex = NoteIndex()
        self.instrument_registry: InstrumentRegistry = InstrumentRegistry()
        self._last_tick: int = 0

    # -- FcpDomainAdapter protocol methods --

    def create_empty(self, title: str, params: dict[str, str]) -> MidiModel:
        """Create a new empty MidiModel from session params."""
        tempo = 120.0
        time_sig = (4, 4)
        key: str | None = None
        ppqn = 480

        if "tempo" in params:
            try:
                tempo = float(params["tempo"])
            except ValueError:
                pass

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

        model = MidiModel(
            title=title,
            ppqn=ppqn,
            tempo=tempo,
            time_sig=time_sig,
            key=key,
        )
        self.note_index = NoteIndex()
        self._last_tick = 0
        return model

    def serialize(self, model: MidiModel, path: str) -> None:
        """Serialize — model.save(path)."""
        model.save(path)

    def deserialize(self, path: str) -> MidiModel:
        """Deserialize — MidiModel.load(path)."""
        model = MidiModel.load(path)
        self.note_index.rebuild(model)
        return model

    def rebuild_indices(self, model: MidiModel) -> None:
        """Rebuild NoteIndex."""
        self.note_index.rebuild(model)

    def get_digest(self, model: MidiModel) -> str:
        """Return a compact state fingerprint."""
        return model.get_digest()

    def dispatch_op(
        self,
        op: GenericParsedOp,
        model: MidiModel,
        log: CoreEventLog,
    ) -> OpResult:
        """Execute a parsed operation on the model.

        1. Take byte snapshot (for undo)
        2. Build MidiOpContext
        3. Re-parse through domain parser
        4. Dispatch to v2 handler
        5. Rebuild note index
        6. Log snapshot event
        7. Return OpResult
        """
        # Take pre-op snapshot
        before = model.snapshot()

        # Build context
        ctx = MidiOpContext(
            model=model,
            note_index=self.note_index,
            instrument_registry=self.instrument_registry,
            last_tick=self._last_tick,
        )

        # Re-parse through domain parser
        domain_parsed = domain_parse_op(op.raw)
        if isinstance(domain_parsed, ParseError):
            return OpResult(success=False, message=f"Parse error: {domain_parsed.error}")

        # Dispatch to v2 handler
        try:
            result_str = self._dispatch_v2(domain_parsed, ctx)
        except (ValueError, KeyError) as exc:
            return OpResult(success=False, message=f"Error: {exc}")

        # Sync state back
        self._last_tick = ctx.last_tick

        # Rebuild index
        self.note_index.rebuild(model)

        # Log snapshot for undo
        after = model.snapshot()
        log.append(SnapshotEvent(before=before, after=after, summary=op.raw))

        # Parse the result string into OpResult
        if result_str.startswith("!"):
            return OpResult(success=False, message=result_str.lstrip("! "))
        prefix = ""
        if len(result_str) > 1 and result_str[1] == " ":
            prefix = result_str[0]
        message = result_str[2:] if prefix else result_str
        return OpResult(success=True, message=message, prefix=prefix)

    def dispatch_query(self, query: str, model: MidiModel) -> str:
        """Execute query via dispatch_query_v2."""
        ctx = MidiOpContext(
            model=model,
            note_index=self.note_index,
            instrument_registry=self.instrument_registry,
            last_tick=self._last_tick,
        )
        return dispatch_query_v2(query, ctx)

    def reverse_event(self, event: SnapshotEvent, model: MidiModel) -> None:
        """Undo — restore from before-snapshot."""
        model.restore(event.before)
        self.note_index.rebuild(model)

    def replay_event(self, event: SnapshotEvent, model: MidiModel) -> None:
        """Redo — restore from after-snapshot."""
        model.restore(event.after)
        self.note_index.rebuild(model)

    # -- Internal dispatch --

    def _dispatch_v2(self, op: DomainParsedOp, ctx: MidiOpContext) -> str:
        """Route a domain-parsed op to the appropriate v2 handler."""
        from fcp_midi.server.ops_music_v2 import (
            op_note, op_chord, op_track, op_cc, op_bend,
            op_mute, op_solo, op_program,
        )
        from fcp_midi.server.ops_meta_v2 import (
            op_tempo, op_time_sig, op_key_sig, op_marker, op_title,
        )
        from fcp_midi.server.ops_editing_v2 import (
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
