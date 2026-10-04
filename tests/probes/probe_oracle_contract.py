"""Literal comparison only. No CLI, file access, import of candidate or evaluator.

The caller supplies pinned raw bytes, complete frozen literal plan and required
profiles from outside observed candidate data. This source is not executed by
its presence. A match is finite equality, never full language conformance.
"""
import hashlib
import json
import math

MAX_BYTES = 24 * 1024 * 1024
MAX_VALUES = 524288
MAX_DEPTH = 1024
FAMILIES = ("kernel", "forms", "context")
KEY_FIELDS = {"case", "family", "profile", "fixture", "input", "applicability"}


class ComparisonError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise ComparisonError(message)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def _constant(_value):
    raise ComparisonError("nonfinite JSON token")


def _load(raw, pin):
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, "finite raw bytes required")
    _require(type(pin) is str and len(pin) == 71 and pin.startswith("sha256:")
             and all(c in "0123456789abcdef" for c in pin[7:]), "external exact pin required")
    _require("sha256:" + hashlib.sha256(raw).hexdigest() == pin, "raw pin mismatch")
    try:
        text = raw.decode("utf-8")
        _require(not text.startswith("\ufeff"), "BOM")
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ComparisonError("invalid complete JSON") from exc
    pending = [(value, 1)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _require(count <= MAX_VALUES and depth <= MAX_DEPTH, "finite payload limit")
        kind = type(item)
        _require(kind in (dict, list, str, int, float, bool, type(None)), "JSON type")
        if kind is float:
            _require(math.isfinite(item), "nonfinite number")
        elif kind is dict:
            pending.extend((v, depth + 1) for v in item.values())
        elif kind is list:
            pending.extend((v, depth + 1) for v in item)
    return value


def _equal(a, b):
    """No bool/int/float coercion, missing/null repair or order normalization."""
    pending = [(a, b)]
    while pending:
        left, right = pending.pop()
        if type(left) is not type(right):
            return False
        if type(left) is dict:
            if left.keys() != right.keys():
                return False
            pending.extend((left[k], right[k]) for k in left)
        elif type(left) is list:
            if len(left) != len(right):
                return False
            pending.extend(zip(left, right))
        elif left != right:
            return False
    return True


def compare(fixtures, fixture_pins, plan_bytes, plan_pin,
            observation_bytes, observation_pin, required_profiles):
    """Return first failure/unknown, or an honest complete finite comparison.

fixtures: exactly family -> raw oracle bytes; fixture_pins: caller exact pins.
required_profiles: caller exact family -> nonempty ordered distinct strings.
Plan: {schema:probe-comparison-plan/1, observations:[key fields + expected]}.
Observations: {schema:probe-observations/1, observations:[key fields + status
and payload]}. Known means complete payload; every other status is unknown.
Full event traces, raw stdout bytes (hex), ABI bytes (hex), actual byte counts,
nonmutation/aliasing evidence and applicable pins must be in the caller's
literal expected payload when required. This function cannot attest them.
"""
    matched = 0
    try:
        _require(type(fixtures) is dict and set(fixtures) == set(FAMILIES), "all fixture families")
        _require(type(fixture_pins) is dict and set(fixture_pins) == set(FAMILIES), "external fixture pins")
        _require(type(required_profiles) is dict and set(required_profiles) == set(FAMILIES), "external profiles")
        coverage = set()
        required_keys = []
        seen_ids = set()
        literals = {}
        total_cases = total_mutations = 0
        for family in FAMILIES:
            profiles = required_profiles[family]
            _require(type(profiles) is list and profiles and
                     all(type(p) is str and p for p in profiles) and
                     len(set(profiles)) == len(profiles), "nonempty exact profiles")
            fixture = _load(fixtures[family], fixture_pins[family])
            _require(type(fixture) is dict and fixture.get("schema") == "probe-literal-oracle/1"
                     and fixture.get("family") == family, "fixture identity")
            cases, mutations = fixture.get("cases"), fixture.get("mutations")
            _require(type(cases) is list and cases and type(mutations) is list, "complete fixture cases")
            total_cases += len(cases)
            total_mutations += len(mutations)
            for case in cases:
                _require(type(case) is dict and type(case.get("id")) is str and
                         case["id"] not in seen_ids and "expected" in case and
                         "input" in case and type(case.get("rule")) is str, "literal case")
                seen_ids.add(case["id"])
                literals[(family, case["id"])] = case["expected"]
                coverage.update((family, case["id"], p) for p in profiles)
                required_keys.extend((family, case["id"], p) for p in profiles)
        _require(0 < total_cases <= 128 and total_mutations <= 40, "finite fixture horizon")
        plan = _load(plan_bytes, plan_pin)
        actual = _load(observation_bytes, observation_pin)
        _require(type(plan) is dict and set(plan) == {"schema", "observations"}
                 and plan["schema"] == "probe-comparison-plan/1", "plan envelope")
        _require(type(actual) is dict and set(actual) == {"schema", "observations"}
                 and actual["schema"] == "probe-observations/1", "observation envelope")
        expected_rows, rows = plan["observations"], actual["observations"]
        _require(type(expected_rows) is list and type(rows) is list and expected_rows,
                 "nonempty complete observations")
        _require(len(expected_rows) == len(rows), "partial or excess observations")
        plan_coverage = set()
        for index, expected in enumerate(expected_rows):
            _require(type(expected) is dict and set(expected) == KEY_FIELDS | {"expected"}, "plan row shape")
            family, case, profile = expected["family"], expected["case"], expected["profile"]
            _require(all(type(x) is str for x in (family, case, profile)), "plan key type")
            key = (family, case, profile)
            _require(key in coverage and key not in plan_coverage, "plan duplicate/unknown/profile")
            _require(index < len(required_keys) and key == required_keys[index],
                     "reordered case/family/profile plan")
            _require(expected["fixture"] == fixture_pins[family], "wrong fixture pin")
            _require(type(expected["input"]) is str and len(expected["input"]) == 71 and
                     expected["input"].startswith("sha256:") and
                     all(c in "0123456789abcdef" for c in expected["input"][7:]), "exact input pin")
            applicable = expected["applicability"]
            _require(type(applicable) is dict and set(applicable) == {"state", "pins"}
                     and applicable["state"] == "applicable"
                     and type(applicable["pins"]) is dict and applicable["pins"]
                     and all(type(k) is str and type(v) is str and len(v) == 71
                             and v.startswith("sha256:")
                             and all(c in "0123456789abcdef" for c in v[7:])
                             for k, v in applicable["pins"].items()), "unknown/wrong applicability")
            _require(type(expected["expected"]) is dict and
                     "literal" in expected["expected"] and
                     _equal(expected["expected"]["literal"], literals[(family, case)]),
                     "plan expectation differs from frozen literal")
            plan_coverage.add(key)
        _require(plan_coverage == coverage, "incomplete required case/profile plan")
        for index, (expected, observed) in enumerate(zip(expected_rows, rows)):
            _require(type(observed) is dict and set(observed) == KEY_FIELDS | {"status", "payload"}, "observation row shape")
            _require(all(_equal(expected[k], observed[k]) for k in KEY_FIELDS), "reordered or wrong observation key")
            if observed["status"] != "known":
                return {"claim":"unknown", "matched":matched, "first":index,
                        "reason":"incomplete/environment/unsupported evidence", "full_conformance":False}
            _require(_equal(expected["expected"], observed["payload"]), "literal payload mismatch")
            matched += 1
        return {"claim":"finite-literal-match", "matched":matched, "first":None,
                "reason":None, "full_conformance":False}
    except ComparisonError as exc:
        return {"claim":"mismatch", "matched":matched, "first":matched,
                "reason":str(exc), "full_conformance":False}
