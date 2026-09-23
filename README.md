# Quantity Engine — MCP Server

An MCP (Model Context Protocol) server that performs dimensional calculation and unit conversion with evidence and reproducibility.

Solves silent unit errors in LLM agent chains. `5 kg × 9.81 m/s^2` returns `49.05 N` with evidence, not a plausible-looking wrong number.

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
```

### Cursor / VS Code / Continue

Same shape — `command`, `args`, no `env` required.

### Manual run

```
pip install -r requirements.txt
python mcp_server.py
```

The server listens on stdio. Ctrl+C to stop.

## Tool contract

`tool.json` defines `quantity_execute` with input and output schemas. The MCP server registers this tool and forwards calls to the engine unchanged — no interpretation, no fallback.

Example call:

```json
{
  "operations": [
    {"id": "s0", "op": "mul",
     "a": {"value": 5, "unit": "kg"},
     "b": {"value": 9.81, "unit": "m/s^2"}},
    {"id": "s1", "op": "convert",
     "a": {"ref": "s0", "as": "N"}, "to": "N"}
  ]
}
```

Returns `49.05 N` with `exactness`, `error_bound` if approximated, and `full_evidence_hash` for replay of the evidence.

Example addition:

```json
{
  "operations": [
    {"id": "s0", "op": "add",
     "a": {"value": 5, "unit": "N"},
     "b": {"value": 3, "unit": "N"}}
  ]
}
```

Returns `8 N` (`EXACT`).

Example division:

```json
{
  "operations": [
    {"id": "s0", "op": "div",
     "a": {"value": 10, "unit": "N"},
     "b": {"value": 2, "unit": "s"}}
  ]
}
```

Returns `5 N/s`. Dimension is derived from operand exponents (M·L·T⁻³).

## What the engine does

- **Closed quantity algebra:** `mul`, `add`, `sub`, `div`, `convert`
- Exact rational arithmetic (no float drift)
- Explicit precision policy (EXACT vs APPROXIMATED with error_bound)
- Provenance hash (`full_evidence_hash`) for replay of the evidence
- Structured failure taxonomy (`MISSING_UNIT_DECLARATION`, `UNKNOWN_UNIT`, `INVALID_UNIT_NOTATION`, `INVALID_UNIT_CAST`, `UNKNOWN_OP`, `DIVISION_BY_ZERO`, `DIMENSION_MISMATCH_UNBRIDGEABLE`, `NEEDS_CLARIFICATION`, `NEEDS_REFERENCE_DATA`)
- No automatic reduction of compound units (`N*m` is reported as `N*m`, not `J`)
- Money as separate domain with temporal context (stub)

Evidence is not correctness. The hash proves what inputs, versions, and reference data were used, and allows the same operation to be replayed against the same evidence. Mathematical correctness rests on the dimensional model, the engine rules, and the test suite — not on the hash.

## Layout

```
quantities.py      engine (zero external dependencies)
tool.json          MCP tool contract
mcp_server.py      MCP stdio transport (uses mcp, jsonschema)
requirements.txt   mcp, jsonschema — only needed for the MCP transport
Dockerfile         container for MCP deployment
```

## Status

MVP. 14 tests passing (`python quantities.py`). Not production. FX rates are stub.

Algebra is closed over the current dimensional model. `cm`, `km`, `h`, `J`, `W` are **not** in the registry — they require an explicit registry extension, not a code change.

## License

Apache 2.0.