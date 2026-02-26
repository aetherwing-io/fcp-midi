"""FastMCP tool registrations for MIDI FCP."""

from __future__ import annotations

from fastmcp import FastMCP

from fcp_midi.server.intent import IntentLayer


def register_tools(mcp: FastMCP, intent: IntentLayer) -> None:
    """Register the 4 MIDI FCP tools on the given MCP server."""

    @mcp.tool
    def midi(ops: list[str]) -> str:
        """Execute MIDI operations. Each op: VERB TARGET [key:value ...]
        Call midi_help for the full reference card."""
        results = intent.execute_ops(ops)
        return "\n".join(results)

    @mcp.tool
    def midi_query(q: str) -> str:
        """Query song state: 'map', 'tracks', 'events Piano',
        'events Piano 1.1-4.4', 'stats', 'describe Piano',
        'piano-roll Piano 1.1-8.4', 'find C4', 'history 5'"""
        return intent.execute_query(q)

    @mcp.tool
    def midi_session(action: str) -> str:
        """Session: 'new "Title" tempo:120', 'open ./file.mid',
        'save', 'save as:./out.mid', 'checkpoint v1', 'undo', 'redo'"""
        return intent.execute_session(action)

    @mcp.tool
    def midi_help() -> str:
        """Returns the MIDI FCP reference card with all syntax."""
        from fcp_midi.server.reference_card import REFERENCE_CARD
        return REFERENCE_CARD
