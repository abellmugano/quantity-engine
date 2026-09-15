# Quantity Engine — MCP Server

An MCP (Model Context Protocol) server that performs dimensional calculation and unit conversion with evidence and reproducibility.

Solves silent unit errors in LLM agent chains. `20 m/s × 3 h` returns `216 km` with evidence, not a plausible-looking wrong number.

## MCP usage

The server exposes one MCP tool: `quantity_execute`. It runs over stdio and follows the MCP protocol via the official Python SDK (`mcp`).

Register with any MCP client.

### Claude Desktop

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "quantity-engine": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"]
    }
  }
}
Cursor / VS Code / Continue
Same shape — command, args, no env required.

Manual run
pip install -r requirements.txt
python mcp_server.py
The server listens on stdio. Ctrl+C to stop.

Tool contract
tool.json defines quantity_execute with input and output schemas. The MCP server registers this tool and forwards calls to the engine unchanged — no interpretation, no fallback.

Example call:
{
  "operations": [
    {"id": "s0", "op": "mul",
     "a": {"value": 20, "unit": "m/s"},
     "b": {"value": 3, "unit": "h"}},
    {"id": "s1", "op": "convert",
     "a": {"ref": "s0", "as": "km"}, "to": "km"}
  ]
}

Returns 216 km with exactness, error_bound if approximated, and full_evidence_hash for replay of the evidence.

What the engine does
Exact rational arithmetic (no float drift)

Explicit precision policy (EXACT vs APPROXIMATED with error_bound)

Provenance hash (full_evidence_hash) for replay of the evidence

Structured failure taxonomy (MISSING_UNIT_DECLARATION, NEEDS_CLARIFICATION, NEEDS_REFERENCE_DATA, DIMENSION_MISMATCH_UNBRIDGEABLE, ...)

Money as separate domain with temporal context (stub)

Evidence is not correctness. The hash proves what inputs, versions, and reference data were used, and allows the same operation to be replayed against the same evidence. Mathematical correctness rests on the dimensional model, the engine rules, and the test suite — not on the hash.
Layout
quantities.py      engine (zero external dependencies)
tool.json          MCP tool contract
mcp_server.py      MCP stdio transport (uses mcp, jsonschema)
requirements.txt   mcp, jsonschema — only needed for the MCP transport
Dockerfile         container for MCP deployment
Status
MVP. 8 tests passing (python quantities.py). Not production. FX rates are stub.

License
Apache 2.0.