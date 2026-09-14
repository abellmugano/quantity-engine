# Quantity Engine

Dimensional calculation and unit conversion with audit evidence.

Solves: silent unit errors in LLM agent chains. `20 m/s × 3 h` returns `216 km` with proof, not a plausible-looking wrong number.

- Exact rational arithmetic (no float drift)
- Explicit precision policy (EXACT vs APPROXIMATED with error_bound)
- Reproducibility hash (full_evidence_hash)
- Agent-native contract (tool.json)
- Money as separate domain with temporal context (stub)

Run tests: `python3 quantities.py`

Status: MVP. Not production. FX rates are stub. See tool.json for the agent contract.