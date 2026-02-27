# fcp-midi

## Project Overview
MCP server that lets LLMs compose MIDI music through semantic operation strings.
See `docs/` for design documents and specifications.

## Architecture
3-layer architecture:
1. **MCP Server (Intent Layer)** - `src/fcp_midi/server/` - Parses op strings, resolves refs, dispatches
2. **Semantic Model (Domain)** - `src/fcp_midi/model/` - In-memory track/note/chord graph, event sourcing
3. **Serialization** - `src/fcp_midi/serialization/` - Semantic model → MIDI binary via pretty-midi

## Key Directories
- `src/fcp_midi/model/` - Semantic model, timing, instrument resolution
- `src/fcp_midi/parser/` - Operation string parser, position parsing
- `src/fcp_midi/serialization/` - MIDI serialization/deserialization
- `src/fcp_midi/server/` - MCP server, tools, intent layer, verb registry
- `src/fcp_midi/adapter.py` - FcpAdapter bridging fcp-core to the domain model

## Commands
- `uv run pytest` - Run tests
- `uv run python -m fcp_midi` - Start the MCP server

## Conventions
- Python 3.11+
- uv for package management
- Tests co-located in `tests/`
- pytest for testing
- pretty-midi for MIDI I/O
