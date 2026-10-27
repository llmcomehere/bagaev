"""Finite, analysis-only law kernel over the frozen R02 research AST.

The original program is never replaced for execution. Ordinary assessment
keeps source edits conservative; a separate API checks common-form evidence.
This is neither a bagaev implementation nor a machine-checked general proof.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys


class LawError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code, self.detail = code, detail
        super().__init__(code + (": " + detail if detail else ""))


ENGINE_PATH = Path(__file__).resolve().parent.parent / "observation-profile" / "engine.py"
EXPECTED_ENGINE_SHA256 = "9406e4faefd01def24d87f2316f0d21546ea971eb99194771d5ce9eafdca48da"
EXPECTED_PROFILE = "authorship-observation-profile/r02-v1"
SEMANTICS_ID = "OBS-0.1/unique-immutable-authorship/pure-common-read-errors"
CATALOG_REVISION = "observation-local-laws/r03-v1"
SUPPORTED_PROVIDER_REVISION = "provider/v1"
OBSERVATION_DOMAIN = "status/value/error/ordered_trace/completeness:OBS-0.1"


def _load_engine():
    if sha256(ENGINE_PATH.read_bytes()).hexdigest() != EXPECTED_ENGINE_SHA256:
        raise LawError("SEMANTICS_SOURCE_MISMATCH")
    name = "_bagaev_r03_frozen_observation_engine"
    if name in sys.modules:
        module = sys.modules[name]
        if Path(module.__file__).resolve() != ENGINE_PATH:
            raise LawError("SEMANTICS_SOURCE_MISMATCH", "module path differs")
        return module
    spec = importlib.util.spec_from_file_location(name, ENGINE_PATH)
    if spec is None or spec.loader is None:
        raise LawError("SEMANTICS_SOURCE_MISMATCH", "cannot load frozen engine")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


engine = _load_engine()
Consumer, ResourceState = engine.Consumer, engine.ResourceState


@dataclass(frozen=True)
class Rule:
    rule_id: str
    operation: str
    source_view: str
    result_view: str
    requires_unique_ids: bool


CATALOG = (
    Rule("SIZE_ORDERED_TO_COUNT", "size", "ordered_members", "count", False),
    Rule("TO_SET_ORDERED_TO_MEMBER_SET", "to_set", "ordered_members", "member_set", False),
    Rule("SIZE_MEMBER_SET_TO_COUNT", "size", "member_set", "count", True),
    Rule("TO_SET_MEMBER_SET_IDENTITY", "to_set", "member_set", "member_set", False),
)
_RULES = {rule.rule_id: rule for rule in CATALOG}
CATALOG_SHA256 = engine.digest({
    "revision": CATALOG_REVISION, "rules": CATALOG,
    "semantics": SEMANTICS_ID, "engine": EXPECTED_ENGINE_SHA256,
    "provider": SUPPORTED_PROVIDER_REVISION, "observed_outcome": OBSERVATION_DOMAIN,
    "context_policy": "exact AST child replacement; no traversal under opaque/unknown",
})


def _environment():
    if sha256(ENGINE_PATH.read_bytes()).hexdigest() != EXPECTED_ENGINE_SHA256:
        raise LawError("SEMANTICS_SOURCE_MISMATCH")
    if engine.PROFILE_REVISION != EXPECTED_PROFILE:
        raise LawError("UNSUPPORTED_PROFILE")


def _validate_consumer(consumer):
    _environment()
    if not isinstance(consumer, Consumer):
        raise LawError("INVALID_CONSUMER", "use laws.Consumer / laws.engine.Consumer")
    return engine.validate_program(consumer.program, consumer.compile_config)


def _provider(consumer):
    if consumer.provider_revision != SUPPORTED_PROVIDER_REVISION:
        raise LawError("UNSUPPORTED_PROVIDER_REVISION", consumer.provider_revision)


def _freeze_ast(ast):
    # Frozen helper belongs to the exact pinned R02 source. It freezes JSON;
    # it does not interpret a subtree or trust a caller-supplied type/use.
    return engine._freeze_json(ast)


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _ast_text(ast):
    # JSON distinguishes true from 1, unlike Python's plain container ==.
    return json.dumps(_plain(ast), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _same_ast(left, right):
    return _ast_text(left) == _ast_text(right)


@dataclass(frozen=True)
class ProofContext:
    stable_id: str
    program_revision: str
    config_stamp: str
    provider_revision: str
    requirements_stamp: str
    profile_revision: str
    semantics_id: str
    engine_sha256: str
    law_kernel_sha256: str
    catalog_revision: str
    catalog_sha256: str


def _context(consumer):
    return ProofContext(
        consumer.stable_id, consumer.program_revision,
        engine.digest(consumer.compile_config), consumer.provider_revision,
        engine.digest(consumer.requirements), EXPECTED_PROFILE, SEMANTICS_ID,
        EXPECTED_ENGINE_SHA256, sha256(Path(__file__).read_bytes()).hexdigest(),
        CATALOG_REVISION, CATALOG_SHA256)


@dataclass(frozen=True)
class RewriteStep:
    rule_id: str
    path: tuple[str | int, ...]
    before: Mapping
    after: Mapping
    guard_stamp: str

    def __post_init__(self):
        if not isinstance(self.path, (tuple, list)):
            raise LawError("INVALID_REWRITE_PATH")
        object.__setattr__(self, "path", tuple(self.path))
        object.__setattr__(self, "before", _freeze_ast(self.before))
        object.__setattr__(self, "after", _freeze_ast(self.after))


@dataclass(frozen=True)
class Derivation:
    context: ProofContext
    original_ast: Mapping
    normalized_ast: Mapping
    steps: tuple[RewriteStep, ...]

    def __post_init__(self):
        if not isinstance(self.context, ProofContext):
            raise LawError("PROOF_CONTEXT_MISMATCH")
        if not isinstance(self.steps, (tuple, list)) or not all(isinstance(s, RewriteStep) for s in self.steps):
            raise LawError("MALFORMED_DERIVATION")
        object.__setattr__(self, "original_ast", _freeze_ast(self.original_ast))
        object.__setattr__(self, "normalized_ast", _freeze_ast(self.normalized_ast))
        object.__setattr__(self, "steps", tuple(self.steps))


@dataclass(frozen=True)
class VerifiedDerivation:
    derivation: Derivation
    summary: engine.UseSummary
    saturated: bool


@dataclass(frozen=True)
class RefinedUse:
    summary: engine.UseSummary
    derivation: Derivation
    saturated: bool


def _children(node, *, include_opaque=False):
    """Relative paths to grammatical AST children, never to arbitrary JSON."""
    op = node["op"]
    names = {
        "let": ("value", "body"), "if": ("condition", "then", "else"),
        "size": ("value",), "to_set": ("value",), "head": ("value",),
        "contains": ("collection", "item"), "eq": ("left", "right"),
        "pair": ("left", "right"),
    }
    if op in names:
        return tuple((name,) for name in names[op])
    if op in {"tuple", "seq"}:
        return tuple(("items", i) for i in range(len(node["items"])))
    if op == "emit":
        return (("value",), ("then",)) if "then" in node else (("value",),)
    if op == "opaque" and include_opaque:
        return tuple(("args", i) for i in range(len(node.get("args", ()))))
    return ()


def _get_raw(tree, path):
    node = tree
    for token in path:
        node = node[token]
    return node


def _set_raw(tree, path, replacement):
    if not path:
        return replacement
    parent = _get_raw(tree, path[:-1])
    parent[path[-1]] = replacement
    return tree


def _resolve(tree, path):
    if not isinstance(path, tuple) or any(type(token) not in (str, int) for token in path):
        raise LawError("INVALID_REWRITE_PATH")
    current, offset = tree, 0
    while offset < len(path):
        selected = None
        for child_path in _children(current):
            fragment = path[offset:offset + len(child_path)]
            if len(fragment) == len(child_path) and all(
                    type(a) is type(b) and a == b for a, b in zip(fragment, child_path)):
                selected = child_path
                break
        if selected is None:
            raise LawError("INVALID_REWRITE_PATH")
        current = _get_raw(current, selected)
        offset += len(selected)
    return current


def _node_count(node, depth=0):
    if depth > engine.MAX_AST_DEPTH:
        raise LawError("REWRITE_LIMIT", "AST depth limit")
    return 1 + sum(_node_count(_get_raw(node, path), depth + 1)
                   for path in _children(node, include_opaque=True))


def _source(rule):
    return {"op": rule.operation, "value": {"op": "read", "view": rule.source_view}}


def _replacement(rule):
    return {"op": "read", "view": rule.result_view}


def _applicable(node):
    return next((rule for rule in CATALOG if _same_ast(node, _source(rule))), None)


def _guard_stamp(rule, context):
    # These premises are fixed by the pinned interpreter and provider, not
    # read from flags supplied in a derivation. In particular ResourceState
    # rejects duplicate IDs in the exact R02 semantics used here.
    return engine.digest({
        "rule": rule, "context": context, "semantics": SEMANTICS_ID,
        "fixed_guards": {
            "immutable_resource": True, "pure_reads": True,
            "common_read_errors": True,
            "unique_ids_required": rule.requires_unique_ids,
            "unique_ids_enforced_by_profile": True,
            "no_observed_runtime_cost": OBSERVATION_DOMAIN,
        }})


def _has_redex(node, depth=0):
    if depth > engine.MAX_AST_DEPTH:
        raise LawError("REWRITE_LIMIT", "AST depth limit")
    return _applicable(node) is not None or any(
        _has_redex(_get_raw(node, path), depth + 1) for path in _children(node))


def normalize(consumer: Consumer) -> Derivation:
    original_type = _validate_consumer(consumer)
    _provider(consumer)
    context = _context(consumer)
    tree = _plain(consumer.program)
    bound = _node_count(tree)
    steps = []

    def visit(node, path, depth):
        if depth > engine.MAX_AST_DEPTH:
            raise LawError("REWRITE_LIMIT", "AST depth limit")
        for child_path in _children(node):
            rewritten = visit(_get_raw(node, child_path), path + child_path, depth + 1)
            _set_raw(node, child_path, rewritten)
        rule = _applicable(node)
        if rule is None:
            return node
        if len(steps) >= bound:
            raise LawError("REWRITE_LIMIT", "node-decreasing step bound")
        result = _replacement(rule)
        steps.append(RewriteStep(rule.rule_id, path, node, result, _guard_stamp(rule, context)))
        return result

    normalized = visit(tree, (), 0)
    if engine.validate_program(normalized, consumer.compile_config) != original_type:
        raise LawError("TYPE_CHANGED_BY_REWRITE")
    return Derivation(context, consumer.program, normalized, tuple(steps))


def replay(consumer: Consumer, derivation: Derivation) -> VerifiedDerivation:
    original_type = _validate_consumer(consumer)
    _provider(consumer)
    if not isinstance(derivation, Derivation):
        raise LawError("MALFORMED_DERIVATION")
    context = _context(consumer)
    if derivation.context != context:
        raise LawError("PROOF_CONTEXT_MISMATCH")
    if not _same_ast(derivation.original_ast, consumer.program):
        raise LawError("ORIGINAL_AST_MISMATCH")
    tree = _plain(consumer.program)
    initial_count = _node_count(tree)
    if len(derivation.steps) > initial_count:
        raise LawError("REWRITE_LIMIT")
    for step in derivation.steps:
        if type(step.rule_id) is not str or step.rule_id not in _RULES:
            raise LawError("UNKNOWN_RULE")
        rule = _RULES[step.rule_id]
        actual = _resolve(tree, step.path)
        if not _same_ast(step.before, actual):
            raise LawError("STEP_BEFORE_MISMATCH")
        if not _same_ast(actual, _source(rule)):
            raise LawError("RULE_NOT_APPLICABLE")
        if step.guard_stamp != _guard_stamp(rule, context):
            raise LawError("GUARD_STAMP_MISMATCH")
        expected = _replacement(rule)
        if not _same_ast(step.after, expected):
            raise LawError("STEP_AFTER_MISMATCH")
        count_before = _node_count(tree)
        tree = _set_raw(tree, step.path, expected)
        if _node_count(tree) != count_before - 1:
            raise LawError("REWRITE_LIMIT", "rule did not remove exactly one node")
    if not _same_ast(tree, derivation.normalized_ast):
        raise LawError("NORMAL_FORM_MISMATCH")
    if engine.validate_program(tree, consumer.compile_config) != original_type:
        raise LawError("TYPE_CHANGED_BY_REWRITE")
    summary = engine.infer_use(tree, consumer.compile_config)
    return VerifiedDerivation(derivation, summary, not _has_redex(tree))


def refined_use(consumer: Consumer, derivation: Derivation | None = None) -> RefinedUse:
    checked = replay(consumer, normalize(consumer) if derivation is None else derivation)
    return RefinedUse(checked.summary, checked.derivation, checked.saturated)


def _conservative(base, reasons=()):
    # Outside the law-provider whitelist we do not promote a baseline result
    # to law-based exclusion, even if its observations happen to be equal.
    return replace(base, decision="UNKNOWN" if base.decision == "UNKNOWN" else "RECHECK",
                   reasons=base.reasons + tuple(reasons), basis="r03_original_analysis")


def _from_summary(base, summary, before_resource, after_resource, reasons, basis):
    delta = engine.exact_delta(before_resource, after_resource)
    changed = summary.required_observations & delta.changed
    why = list(reasons)
    if not summary.complete:
        decision = "UNKNOWN"
        why.extend("INCOMPLETE_USE:" + reason for reason in summary.reasons)
    elif changed:
        decision = "RECHECK"
        why.extend("REQUIRED_OBSERVATION_CHANGED:" + name for name in sorted(changed))
    else:
        decision = "EXCLUDED"
        why.append("ALL_REFINED_OBSERVATIONS_EQUAL")
    return engine.Assessment(base.consumer_id, decision, tuple(why), delta.changed,
                             summary.required_observations, base.requirements, basis)


def assess(before: Consumer | None, after: Consumer | None,
           before_resource: ResourceState | None, after_resource: ResourceState | None,
           *, before_derivation: Derivation | None = None,
           after_derivation: Derivation | None = None) -> engine.Assessment:
    checked = []
    for consumer, derivation in ((before, before_derivation), (after, after_derivation)):
        if consumer is not None:
            _validate_consumer(consumer)
        if derivation is not None:
            if consumer is None:
                raise LawError("PROOF_CONTEXT_MISMATCH", "proof has no consumer")
            checked.append(replay(consumer, derivation))
        else:
            checked.append(None)
    base = engine.assess(before, after, before_resource, after_resource)
    if before is None or after is None or before.input_stamp != after.input_stamp:
        return _conservative(base, ("ORIGINAL_CONSUMER_CHANGED",))
    if before.provider_revision != SUPPORTED_PROVIDER_REVISION:
        return _conservative(base, ("UNSUPPORTED_PROVIDER_REVISION:" + before.provider_revision,))
    first = checked[0] or replay(before, normalize(before))
    second = checked[1] or replay(after, normalize(after))
    summary = engine._merge(first.summary, second.summary)
    reasons = ("REPLAYED_DERIVATION:" + engine.digest(first.derivation),
               "REPLAYED_DERIVATION:" + engine.digest(second.derivation))
    return _from_summary(base, summary, before_resource, after_resource, reasons, "r03_replayed_use")


@dataclass(frozen=True)
class EquivalenceCertificate:
    before_derivation: Derivation
    after_derivation: Derivation
    common_form: Mapping
    observation_domain: str = OBSERVATION_DOMAIN

    def __post_init__(self):
        object.__setattr__(self, "common_form", _freeze_ast(self.common_form))


@dataclass(frozen=True)
class EquivalenceResult:
    status: str
    reasons: tuple[str, ...]
    certificate: EquivalenceCertificate | None = None


@dataclass(frozen=True)
class VerifiedEquivalence:
    certificate: EquivalenceCertificate
    summary: engine.UseSummary
    saturated: bool


def _equivalence_context_reasons(before, after):
    reasons = []
    checks = (
        ("STABLE_ID_MISMATCH", before.stable_id, after.stable_id),
        ("COMPILE_CONFIG_CHANGED", engine.digest(before.compile_config), engine.digest(after.compile_config)),
        ("PROVIDER_REVISION_CHANGED", before.provider_revision, after.provider_revision),
        ("REQUIREMENTS_CHANGED", engine.digest(before.requirements), engine.digest(after.requirements)),
    )
    for code, left, right in checks:
        if left != right:
            reasons.append(f"{code}:{left}->{right}")
    if before.provider_revision != SUPPORTED_PROVIDER_REVISION or after.provider_revision != SUPPORTED_PROVIDER_REVISION:
        reasons.append("UNSUPPORTED_PROVIDER_REVISION")
    return tuple(reasons)


def verify_equivalence(before: Consumer, after: Consumer,
                       certificate: EquivalenceCertificate) -> VerifiedEquivalence:
    _validate_consumer(before)
    _validate_consumer(after)
    if not isinstance(certificate, EquivalenceCertificate):
        raise LawError("MALFORMED_EQUIVALENCE_CERTIFICATE")
    if certificate.observation_domain != OBSERVATION_DOMAIN:
        raise LawError("OBSERVATION_DOMAIN_MISMATCH")
    reasons = _equivalence_context_reasons(before, after)
    if reasons:
        raise LawError("EQUIVALENCE_CONTEXT_MISMATCH", ";".join(reasons))
    first = replay(before, certificate.before_derivation)
    second = replay(after, certificate.after_derivation)
    if not first.summary.complete or not second.summary.complete:
        raise LawError("INCOMPLETE_EQUIVALENCE")
    if (not _same_ast(first.derivation.normalized_ast, second.derivation.normalized_ast)
            or not _same_ast(certificate.common_form, first.derivation.normalized_ast)):
        raise LawError("COMMON_FORM_MISMATCH")
    # Re-infer the common form instead of trusting even a stored summary.
    summary = engine.infer_use(certificate.common_form, before.compile_config)
    return VerifiedEquivalence(certificate, summary, first.saturated and second.saturated)


def derive_equivalence(before: Consumer, after: Consumer, *,
                       before_derivation: Derivation | None = None,
                       after_derivation: Derivation | None = None) -> EquivalenceResult:
    before_type, after_type = _validate_consumer(before), _validate_consumer(after)
    # Supplied chains are never silently accepted or used as declarations.
    if before_derivation is not None:
        replay(before, before_derivation)
    if after_derivation is not None:
        replay(after, after_derivation)
    reasons = _equivalence_context_reasons(before, after)
    if reasons:
        return EquivalenceResult("UNPROVED", reasons)
    if before_type != after_type:
        return EquivalenceResult("UNPROVED", ("RESULT_TYPE_MISMATCH",))
    first = replay(before, normalize(before) if before_derivation is None else before_derivation)
    second = replay(after, normalize(after) if after_derivation is None else after_derivation)
    if not first.summary.complete or not second.summary.complete:
        return EquivalenceResult("UNPROVED", ("INCOMPLETE_USE",))
    if not _same_ast(first.derivation.normalized_ast, second.derivation.normalized_ast):
        return EquivalenceResult("UNPROVED", ("NO_COMMON_VERIFIED_FORM",))
    certificate = EquivalenceCertificate(first.derivation, second.derivation,
                                         first.derivation.normalized_ast)
    verify_equivalence(before, after, certificate)
    return EquivalenceResult("PROVED", ("COMMON_VERIFIED_FORM",), certificate)


def assess_equivalent_edit(before: Consumer, after: Consumer,
                           before_resource: ResourceState | None, after_resource: ResourceState | None,
                           *, certificate: EquivalenceCertificate | None = None) -> engine.Assessment:
    _validate_consumer(before)
    _validate_consumer(after)
    base = engine.assess(before, after, before_resource, after_resource)
    if certificate is not None:
        verified = verify_equivalence(before, after, certificate)
    else:
        result = derive_equivalence(before, after)
        if result.status != "PROVED":
            return _conservative(base, tuple("EQUIVALENCE_UNPROVED:" + reason for reason in result.reasons))
        certificate = result.certificate
        verified = verify_equivalence(before, after, certificate)
    reasons = ("COMMON_FORM_CERTIFICATE:" + engine.digest(certificate),
               "ORIGINAL_REVISIONS:" + before.program_revision + "->" + after.program_revision)
    return _from_summary(base, verified.summary, before_resource, after_resource,
                         reasons, "r03_common_normal_form")
