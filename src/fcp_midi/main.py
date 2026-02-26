"""MIDI FCP — File Context Protocol for MIDI composition."""

from fastmcp import FastMCP

mcp = FastMCP(
    name="midi-fcp",
    instructions="MIDI File Context Protocol. Call midi_help for the reference card.",
)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
