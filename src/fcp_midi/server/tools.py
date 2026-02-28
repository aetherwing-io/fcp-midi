"""FastMCP tool registrations for MIDI FCP.

This module is a compatibility shim. Tool registration is now handled
by ``create_fcp_server()`` from fcp_core via the adapter pattern.
The ``register_tools()`` function is kept for backward compatibility.
"""

from __future__ import annotations

from fastmcp import FastMCP

from fcp_midi.server.intent import IntentLayer
from fcp_midi.server.reference_card import build_tool_description


def register_tools(mcp: FastMCP, intent: IntentLayer) -> None:
    """Register the 4 MIDI FCP tools on the given MCP server.

    .. deprecated::
        Use ``create_fcp_server()`` from ``fcp_core`` with ``MidiAdapter``
        instead. This function is kept for backward compatibility.
    """

    # Build the full reference card into the midi tool description
    # so the LLM sees it on connect — no extra midi_help() call needed.
    midi_description = build_tool_description()

    @mcp.tool(description=midi_description)
    def midi(ops: list[str]) -> str:
        results = intent.execute_ops(ops)
        return "\n".join(results)

    @mcp.tool
    def midi_query(q: str) -> str:
        """Query song state: 'map', 'tracks', 'events Piano',
        'events Piano 1.1-4.4', 'stats', 'describe Piano',
        'tracker Piano 1.1-8.4', 'find C4', 'history 5'"""
        return intent.execute_query(q)

    @mcp.tool
    def midi_session(action: str) -> str:
        """Session: 'new "Title" tempo:120', 'open ./file.mid',
        'save', 'save as:./out.mid', 'checkpoint v1', 'undo', 'redo'"""
        return intent.execute_session(action)

    @mcp.tool
    def midi_help() -> str:
        """Returns the MIDI FCP reference card with all syntax.
        Use after context truncation or when custom types have been defined."""
        from fcp_midi.server.reference_card import REFERENCE_CARD
        return REFERENCE_CARD
