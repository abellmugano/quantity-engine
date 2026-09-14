"""
quantities.py — Quantity Engine MVP
Estado: NÃO VALIDADO. A validação é correr os testes 1-8.
Fonte única: SPECS-Core + F2.1 + decisões (a)(b)(c) + Afinações Finais + T8.
"""

from fractions import Fraction
from decimal import Decimal, getcontext, ROUND_HALF_EVEN
import hashlib, json, uuid

REGISTRY = {
    "kg":          ((Fraction(1), Fraction(0), Fraction(0)), Fraction(1)),
    "m":           ((Fraction(0), Fraction(1), Fraction(0)), Fraction(1)),
    "s":           ((Fraction(0), Fraction(0), Fraction(1)), Fraction(1)),
    "N":           ((Fraction(1), Fraction(1), Fraction(-2)), Fraction(1)),
    "lbf":         ((Fraction(1), Fraction(1), Fraction(-2)),
                    Fraction(44482216152605, 10**13)),
    "L":           ((Fraction(0), Fraction(3), Fraction(0)), Fraction(1, 1000)),
    "L/(100*km)":  ((Fraction(0), Fraction(2), Fraction(0)), Fraction(1, 10**8)),
}

# Bridges: (source_dim, target_dim) -> (missing_dim, suggested_unit, human_name)
# A bridge exists when the operation is completable via exactly one additional operand.
# If a bridge is not listed, the mismatch is unbridgeable.
BRIDGES = {
    ((Fraction(0), Fraction(3), Fraction(0)),
     (Fraction(0), Fraction(2), Fraction(0))):
        ((Fraction(0), Fraction(1), Fraction(0)), "km", "distance (Length)"),
}

CURRENCIES = {"USD", "EUR", "MZN", "GBP", "JPY"}
ENGINE_VERSION = "1.0.0"


class QError(Exception):
    def __init__(self, code, message):
        self.code = code; self.message = message
        super().__init__(message)


class DimensionMismatch(Exception):
    def __init__(self, source_dim, target_dim, source_unit, target_unit):
        self.source_dim = source_dim
        self.target_dim = target_dim
        self.source_unit = source_unit
        self.target_unit = target_unit
        super().__init__(
            f"Dimension mismatch: {source_unit} -> {target_unit}"
        )


def parse_unit(s, registry=None):
    registry = registry or REGISTRY
    if s in registry:
        return registry[s]
    if any(c in s for c in "\u00b2\u00b3\u00b7\u00b5"):
        raise QError("INVALID_UNIT_NOTATION", f"Unicode not allowed: {s!r}")
    for i, c in enumerate(s):
        if c.isdigit() and (i == 0 or s[i-1] != "^"):
            raise QError("INVALID_UNIT_NOTATION", f"Digit requires ^: {s!r}")
    tokens = s.replace("*", " * ").replace("/", " / ").split()
    dim = [Fraction(0)] * 3
    factor = Fraction(1)
    sign = 1
    for t in tokens:
        if t == "*": sign = 1; continue
        if t == "/": sign = -1; continue
        if "^" in t:
            name, exp_s = t.rsplit("^", 1)
            try: exp = int(exp_s)
            except ValueError:
                raise QError("INVALID_UNIT_NOTATION", f"Bad exponent: {t!r}")
        else:
            name, exp = t, 1
        if name not in registry:
            raise QError("UNKNOWN_UNIT", f"Unknown unit: {name!r}")
        u_dim, u_factor = registry[name]
        e = exp * sign
        for k in range(3):
            dim[k] += u_dim[k] * e
        factor *= u_factor ** e
    return tuple(dim), factor


class Quantity:
    def __init__(self, value_si, dim, display_unit):
        self.value_si = value_si
        self.dim = dim
        self.display_unit = display_unit

    def mul(self, other):
        return Quantity(
            self.value_si * other.value_si,
            tuple(a + b for a, b in zip(self.dim, other.dim)),
            f"{self.display_unit}*{other.display_unit}",
        )

    def value_in_display(self, registry=None):
        _, f = parse_unit(self.display_unit, registry)
        return self.value_si / f


def make_quantity(value, unit, registry=None):
    dim, factor = parse_unit(unit, registry)
    return Quantity(Fraction(value) * factor, dim, unit)


def cast_to(q, target_unit, registry=None):
    t_dim, _ = parse_unit(target_unit, registry)
    if t_dim != q.dim:
        raise DimensionMismatch(q.dim, t_dim, q.display_unit, target_unit)
    return Quantity(q.value_si, t_dim, target_unit)


def is_finite_decimal(frac):
    d = frac.denominator
    while d % 2 == 0: d //= 2
    while d % 5 == 0: d //= 5
    return d == 1


def to_decimal_string(frac, scale):
    getcontext().prec = 80
    d = Decimal(frac.numerator) / Decimal(frac.denominator)
    q = Decimal(1).scaleb(-scale)
    return str(d.quantize(q, rounding=ROUND_HALF_EVEN))


def resolve(x, steps, registry=None):
    if "ref" in x:
        if "as" not in x:
            raise QError("MISSING_UNIT_DECLARATION",
                         f"Reference '{x['ref']}' used without 'as'")
        try:
            return cast_to(steps[x["ref"]], x["as"], registry)
        except DimensionMismatch:
            q = steps[x["ref"]]
            raise QError("INVALID_UNIT_CAST",
                         f"Cannot cast {q.display_unit} -> {x['as']}")
    return make_quantity(x["value"], x["unit"], registry)


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def operation_hash(ops, precision):
    payload = canonical_json({"ops": ops, "precision": precision})
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def unit_definition_hash(name, registry):
    dim, factor = registry[name]
    payload = canonical_json({
        "name": name,
        "dim": [str(x) for x in dim],
        "factor": str(factor),
    })
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def collect_used_units(ops):
    used = set()
    for op in ops:
        for side in ("a", "b"):
            x = op.get(side)
            if isinstance(x, dict) and "unit" in x:
                if x["unit"] in REGISTRY:
                    used.add(x["unit"])
                else:
                    for tok in x["unit"].replace("*", " ").replace("/", " ").split():
                        if "^" in tok: tok = tok.rsplit("^", 1)[0]
                        if tok in REGISTRY: used.add(tok)
        if "to" in op and op["to"] in REGISTRY:
            used.add(op["to"])
        if isinstance(op.get("a"), dict) and "as" in op["a"]:
            if op["a"]["as"] in REGISTRY:
                used.add(op["a"]["as"])
    return sorted(used)


def full_evidence_hash(ops, precision, registry, refdata=None):
    used = collect_used_units(ops)
    used_hashes = {u: unit_definition_hash(u, registry) for u in used}
    payload = canonical_json({
        "operation_hash": operation_hash(ops, precision),
        "engine_version": ENGINE_VERSION,
        "used_unit_definitions": used_hashes,
        "reference_data_snapshot": refdata,
        "precision_policy": precision,
    })
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def execute(ops, precision=None, registry=None, refdata=None):
    registry = registry or REGISTRY
    precision = precision or {"source": "consumer",
                              "mode": "HALF_EVEN", "scale": 10}
    steps = {}
    for op in ops:
        try:
            if op["op"] == "convert":
                target = op["to"]
                a_unit = None
                if isinstance(op["a"], dict) and "unit" in op["a"]:
                    a_unit = op["a"]["unit"]

                if a_unit and a_unit.upper() in CURRENCIES:
                    if "at" not in op:
                        return {"status": "NEEDS_REFERENCE_DATA",
                                "error_code": "MISSING_TEMPORAL_CONTEXT",
                                "required_params": [
                                    {"name": "at", "type": "ISO8601_timestamp"}]}
                    raise QError("NOT_IMPLEMENTED", "FX not implemented")

                if target.upper() in CURRENCIES:
                    if "at" not in op:
                        return {"status": "NEEDS_REFERENCE_DATA",
                                "error_code": "MISSING_TEMPORAL_CONTEXT",
                                "required_params": [
                                    {"name": "at", "type": "ISO8601_timestamp"}]}
                    raise QError("NOT_IMPLEMENTED", "FX not implemented")

                a = resolve(op["a"], steps, registry)
                steps[op["id"]] = cast_to(a, target, registry)

            elif op["op"] == "mul":
                a = resolve(op["a"], steps, registry)
                b = resolve(op["b"], steps, registry)
                steps[op["id"]] = a.mul(b)

            else:
                raise QError("UNKNOWN_OP", op["op"])

        except DimensionMismatch as dm:
            key = (dm.source_dim, dm.target_dim)
            if key in BRIDGES:
                missing_dim, suggestion, human_name = BRIDGES[key]
                return {
                    "status": "NEEDS_CLARIFICATION",
                    "error_code": "DIMENSION_MISMATCH_REQUIRES_CONTEXT",
                    "message": (f"Cannot convert '{dm.source_unit}' to "
                                f"'{dm.target_unit}'. Missing {human_name} "
                                f"to bridge dimensions."),
                    "clarification_needed": {
                        "missing_dimension": [str(x) for x in missing_dim],
                        "suggested_unit": suggestion,
                    },
                }
            return {
                "status": "ERROR",
                "error_code": "DIMENSION_MISMATCH_UNBRIDGEABLE",
                "message": (f"Cannot convert '{dm.source_unit}' to "
                            f"'{dm.target_unit}'."),
            }

        except QError as e:
            return {"status": "ERROR", "error_code": e.code, "message": e.message}

    q = steps[ops[-1]["id"]]
    val = q.value_in_display(registry)
    scale = precision["scale"]
    used = collect_used_units(ops)
    used_hashes = {u: unit_definition_hash(u, registry) for u in used}
    envelope = {
        "status": "SUCCESS",
        "result_id": str(uuid.uuid4()),
        "value": to_decimal_string(val, scale),
        "unit": q.display_unit,
        "evidence": {
            "operation_hash": operation_hash(ops, precision),
            "full_evidence_hash": full_evidence_hash(ops, precision, registry, refdata),
            "engine_version": ENGINE_VERSION,
            "used_unit_definitions": used_hashes,
            "reference_data": refdata,
            "precision_policy": precision,
        },
    }
    if is_finite_decimal(val):
        envelope["exactness"] = "EXACT"
    else:
        envelope["exactness"] = "APPROXIMATED"
        envelope["approximation"] = {
            "rounding_mode": precision["mode"],
            "precision_scale": scale,
            "error_bound": f"5e-{scale+1}",
        }
    return envelope


# ==================== TESTES ====================

CASO_4 = [
    {"id": "s0", "op": "mul",
     "a": {"value": 5, "unit": "kg"},
     "b": {"value": 9.81, "unit": "m/s^2"}},
    {"id": "s1", "op": "convert",
     "a": {"ref": "s0", "as": "N"}, "to": "lbf"},
]
PRECISION = {"source": "consumer", "mode": "HALF_EVEN", "scale": 10}


def test_1_mul():
    r = execute([CASO_4[0]])
    assert r["status"] == "SUCCESS", r
    assert r["exactness"] == "EXACT", r
    assert r["value"] == "49.0500000000", r
    print("T1 PASS", r["value"])


def test_2_cast_noop():
    r = execute(CASO_4[:1] + [{"id": "s1", "op": "convert",
                                "a": {"ref": "s0", "as": "N"}, "to": "N"}])
    assert r["status"] == "SUCCESS", r
    assert r["value"] == "49.0500000000", r
    print("T2 PASS", r["value"])


def test_3_convert_lbf():
    r = execute(CASO_4, precision=PRECISION)
    assert r["status"] == "SUCCESS", r
    assert r["exactness"] == "APPROXIMATED", r
    assert r["value"].startswith("11.026878"), r
    assert r["approximation"]["error_bound"] == "5e-11", r
    print("T3 PASS", r["value"])


def test_4_missing_as():
    ops = [{"id": "s0", "op": "mul",
            "a": {"value": 5, "unit": "kg"},
            "b": {"value": 9.81, "unit": "m/s^2"}},
           {"id": "s1", "op": "convert",
            "a": {"ref": "s0"}, "to": "lbf"}]
    r = execute(ops, precision=PRECISION)
    assert r["status"] == "ERROR", r
    assert r["error_code"] == "MISSING_UNIT_DECLARATION", r
    print("T4 PASS", r["error_code"])


def test_5_fx_no_at():
    ops = [{"id": "s0", "op": "convert",
            "a": {"value": 100, "unit": "EUR"}, "to": "USD"}]
    r = execute(ops)
    assert r["status"] == "NEEDS_REFERENCE_DATA", r
    assert r["error_code"] == "MISSING_TEMPORAL_CONTEXT", r
    print("T5 PASS", r["status"])


def test_6_hash_reproducible():
    r1 = execute(CASO_4, precision=PRECISION)
    r2 = execute(CASO_4, precision=PRECISION)
    assert r1["evidence"]["operation_hash"] == r2["evidence"]["operation_hash"], (r1, r2)
    assert r1["evidence"]["full_evidence_hash"] == r2["evidence"]["full_evidence_hash"], (r1, r2)
    assert r1["value"] == r2["value"]
    assert r1["result_id"] != r2["result_id"]
    print("T6 PASS  op_hash==", r1["evidence"]["operation_hash"][:20], "…")


def test_7_registry_change_surgical():
    r1 = execute(CASO_4, precision=PRECISION)
    modified = dict(REGISTRY)
    modified["lbf"] = ((Fraction(1), Fraction(1), Fraction(-2)),
                       Fraction(45, 10))
    r2 = execute(CASO_4, precision=PRECISION, registry=modified)
    h1 = r1["evidence"]
    h2 = r2["evidence"]
    assert h1["operation_hash"] == h2["operation_hash"], "intent mudou"
    assert h1["full_evidence_hash"] != h2["full_evidence_hash"], "hash não mudou"
    keys = set(h1["used_unit_definitions"]) | set(h2["used_unit_definitions"])
    diff = [k for k in keys
            if h1["used_unit_definitions"].get(k) != h2["used_unit_definitions"].get(k)]
    assert diff == ["lbf"], f"esperava só lbf, veio {diff}"
    print("T7 PASS  mudou apenas:", diff)


def test_8_needs_clarification_bridge():
    ops = [{"id": "s0", "op": "convert",
            "a": {"value": 50, "unit": "L"}, "to": "L/(100*km)"}]
    r = execute(ops)
    assert r["status"] == "NEEDS_CLARIFICATION", r
    assert r["error_code"] == "DIMENSION_MISMATCH_REQUIRES_CONTEXT", r
    assert r["clarification_needed"]["suggested_unit"] == "km", r
    print("T8 PASS", r["error_code"])


if __name__ == "__main__":
    test_1_mul()
    test_2_cast_noop()
    test_3_convert_lbf()
    test_4_missing_as()
    test_5_fx_no_at()
    test_6_hash_reproducible()
    test_7_registry_change_surgical()
    test_8_needs_clarification_bridge()
    print("\nALL TESTS PASSED")