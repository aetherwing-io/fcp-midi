"""MIDI FCP — File Context Protocol for MIDI composition."""

from fastmcp import FastMCP

from fcp_midi.server.intent import IntentLayer
from fcp_midi.server.tools import register_tools

mcp = FastMCP(
    name="midi-fcp",
    instructions="MIDI File Context Protocol. Call midi_help for the reference card.",
)

intent = IntentLayer()
register_tools(mcp, intent)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
