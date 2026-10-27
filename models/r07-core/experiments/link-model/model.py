"""Finite engineering model. No bagaev parsing, execution, or real proofs.

Facts and completeness certificates are trusted synthetic fixture inputs.
The observation model treats named facets as independent atomic coordinates.
Names are non-reflective aliases in this profile; references use stable IDs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from hashlib import sha256
import json
from typing import Iterable


class ModelError(ValueError):
    pass


def canonical(value):
    if is_dataclass(value):
        return canonical(asdict(value))
    if isinstance(value, dict):
        return {str(k): canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (set, frozenset)):
        return sorted(canonical(v) for v in value)
    if isinstance(value, (tuple, list)):
        return [canonical(v) for v in value]
    return value


def digest(value) -> str:
    payload = json.dumps(canonical(value), sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class Registry:
    registry_id: str
    facets: frozenset[str]
    observation_model: str = "synthetic independent atomic observation coordinates"


REGISTRY = Registry("synthetic-authorship-v1", frozenset({
    "values", "order", "cardinality", "errors", "effects"}))


@dataclass(frozen=True)
class Certificate:
    facets: frozenset[str]
    complete: bool = True
    registry_id: str = REGISTRY.registry_id
    provenance: str = "trusted synthetic fixture assumption; not a real proof"

    def __post_init__(self):
        if type(self.complete) is not bool:
            raise ModelError("INVALID_CERTIFICATE_COMPLETENESS")


@dataclass(frozen=True)
class FacetClaim:
    declared: frozenset[str] | None
    certificate: Certificate | None = None


def certified(*facets: str, complete: bool = True) -> FacetClaim:
    items = frozenset(facets)
    return FacetClaim(items, Certificate(items, complete))


def resolve_claim(claim: FacetClaim, registry: Registry, *, unsafe=False):
    """Return a safe upper bound, or TOP=None. Unsafe is a deliberate mutant."""
    if claim.declared is not None and not claim.declared <= registry.facets:
        raise ModelError("UNKNOWN_DECLARED_FACET")
    if unsafe:
        return claim.declared, "UNSAFE_TRUST_DECLARATION"
    cert = claim.certificate
    if cert is None or not cert.complete or claim.declared is None:
        return None, "NO_COMPLETE_SYNTHETIC_CERTIFICATE"
    if cert.registry_id != registry.registry_id:
        return None, "OBSERVATION_REGISTRY_MISMATCH"
    if not cert.facets <= registry.facets:
        raise ModelError("UNKNOWN_CERTIFIED_FACET")
    if not cert.facets <= claim.declared:
        raise ModelError("UNDERDECLARED_FACETS")
    return claim.declared, "SYNTHETIC_COMPLETE_UPPER_BOUND"


@dataclass(frozen=True)
class Node:
    entity_id: str
    revision: str = "r1"
    alias: str = ""
    kind: str = "operation"


@dataclass(frozen=True)
class Guard:
    kind: str = "always"
    config_key: str | None = None
    expected: bool = True
    runtime_observation: bool | None = None


@dataclass(frozen=True)
class Fact:
    fact_id: str
    source: str
    target: str | None
    kind: str = "reads"
    guard: Guard = Guard()
    footprint: FacetClaim = FacetClaim(None)


@dataclass(frozen=True)
class Graph:
    generation: str
    nodes: tuple[Node, ...]
    facts: tuple[Fact, ...]
    compile_config: tuple[tuple[str, bool], ...] = ()
    config_pinned: bool = True
    extractor_version: str = "synthetic-extractor-v1"
    scope_complete: bool = True
    registry_id: str = REGISTRY.registry_id

    def __post_init__(self):
        nodes = {n.entity_id: n for n in self.nodes}
        if len(nodes) != len(self.nodes):
            raise ModelError("DUPLICATE_NODE")
        if len({f.fact_id for f in self.facts}) != len(self.facts):
            raise ModelError("DUPLICATE_FACT")
        kinds = {"reads": "resource", "calls": "operation", "requires": "contract",
                 "emits": "event", "consumes": "event"}
        for f in self.facts:
            if f.source not in nodes or (f.target is not None and f.target not in nodes):
                raise ModelError("DANGLING_FACT")
            if f.kind not in kinds or nodes[f.source].kind != "operation":
                raise ModelError("INVALID_RELATION_KIND")
            if f.target is not None and nodes[f.target].kind != kinds[f.kind]:
                raise ModelError("INVALID_RELATION_ENDPOINT")
            if f.guard.kind not in {"always", "compile", "runtime"}:
                raise ModelError("UNSUPPORTED_GUARD")
            if (type(f.guard.expected) is not bool or
                    (f.guard.runtime_observation is not None and
                     type(f.guard.runtime_observation) is not bool)):
                raise ModelError("INVALID_GUARD_VALUE")
        if type(self.config_pinned) is not bool or type(self.scope_complete) is not bool:
            raise ModelError("INVALID_GRAPH_COMPLETENESS")
        if any(type(value) is not bool for _, value in self.compile_config):
            raise ModelError("INVALID_CONFIG_VALUE")
        if len(dict(self.compile_config)) != len(self.compile_config):
            raise ModelError("DUPLICATE_CONFIG_KEY")

    def structural_key(self) -> str:
        # Generation and aliases are not semantic content in this finite profile.
        return digest({
            "nodes": sorted((n.entity_id, n.revision, n.kind) for n in self.nodes),
            "facts": sorted(self.facts, key=lambda f: f.fact_id),
            "config": sorted(self.compile_config), "pinned": self.config_pinned,
            "extractor": self.extractor_version, "coverage": self.scope_complete,
            "registry": self.registry_id})


def guard_state(guard: Guard, graph: Graph) -> str:
    if guard.kind == "always":
        return "TRUE"
    if guard.kind == "runtime":
        return "UNKNOWN"  # A false observation is not a global exclusion.
    config = dict(graph.compile_config)
    if not graph.config_pinned or guard.config_key not in config:
        return "UNKNOWN"
    return "TRUE" if config[guard.config_key] == guard.expected else "FALSE"


@dataclass(frozen=True)
class Index:
    direction: str
    generation: str
    structural_key: str
    rows: tuple[tuple[str, tuple[str, ...]], ...]
    unknown_fact_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class IndexPair:
    forward: Index
    reverse: Index


def build_indexes(graph: Graph) -> IndexPair:
    forward, reverse, unknown = {}, {}, []
    for f in graph.facts:
        forward.setdefault(f.source, []).append(f.fact_id)
        if f.target is None:
            unknown.append(f.fact_id)
        else:
            reverse.setdefault(f.target, []).append(f.fact_id)
    def rows(mapping):
        return tuple((k, tuple(sorted(v))) for k, v in sorted(mapping.items()))
    key = graph.structural_key()
    return IndexPair(Index("forward", graph.generation, key, rows(forward)),
                     Index("reverse", graph.generation, key, rows(reverse),
                           tuple(sorted(unknown))))


def validate_indexes(graph: Graph, indexes: IndexPair):
    # This finite model reconstructs canonical contents. Metadata alone cannot
    # authenticate rows or prove that unknown targets have not been dropped.
    # A production integrity scheme would need its own explicit invariant.
    expected_pair = build_indexes(graph)
    for expected, index in ((expected_pair.forward, indexes.forward),
                            (expected_pair.reverse, indexes.reverse)):
        if index.direction != expected.direction or index.generation != graph.generation:
            raise ModelError("GENERATION_MISMATCH")
        if index.structural_key != expected.structural_key:
            raise ModelError("INDEX_CONTENT_MISMATCH")
        if (index.rows != expected.rows or
                index.unknown_fact_ids != expected.unknown_fact_ids):
            raise ModelError("INDEX_ROWS_MISMATCH")


def scope_ids(graph: Graph, scope: Iterable[str] | None) -> tuple[str, ...]:
    ids = {n.entity_id for n in graph.nodes}
    result = ids if scope is None else set(scope)
    if not result <= ids:
        raise ModelError("UNKNOWN_SCOPE_MEMBER")
    return tuple(sorted(result))


def membership_key(graph: Graph, target: str, scope=None) -> str:
    members = scope_ids(graph, scope)
    if target not in {n.entity_id for n in graph.nodes}:
        raise ModelError("UNKNOWN_QUERY_TARGET")
    return digest({
        "query": ["may_consumers", target],
        "members": sorted((n.entity_id, n.revision, n.kind) for n in graph.nodes
                          if n.entity_id in members),
        # Includes nonmatching and inactive facts: future membership matters.
        "candidate_facts": sorted((f for f in graph.facts if f.source in members),
                                  key=lambda f: f.fact_id),
        "config": sorted(graph.compile_config), "pinned": graph.config_pinned,
        "extractor": graph.extractor_version, "coverage": graph.scope_complete,
        "registry": graph.registry_id})


@dataclass(frozen=True)
class QueryResult:
    items: tuple[str, ...]
    fact_ids: tuple[str, ...]
    complete_in_declared_scope: bool
    unknown_targets: tuple[str, ...]
    membership_fingerprint: str


def _query_result(graph: Graph, target: str, candidates, scope=None) -> QueryResult:
    members = scope_ids(graph, scope)
    active = [f for f in candidates if f.source in members
              and (f.target == target or f.target is None)
              and guard_state(f.guard, graph) != "FALSE"]
    unknown = tuple(sorted(f.fact_id for f in active if f.target is None))
    return QueryResult(tuple(sorted({f.source for f in active})),
                       tuple(sorted(f.fact_id for f in active)),
                       graph.scope_complete and not unknown, unknown,
                       membership_key(graph, target, members))


def full_query(graph: Graph, target: str, scope=None) -> QueryResult:
    return _query_result(graph, target, graph.facts, scope)


def indexed_query(graph: Graph, indexes: IndexPair, target: str, scope=None) -> QueryResult:
    validate_indexes(graph, indexes)
    ids = set(dict(indexes.reverse.rows).get(target, ())) | set(indexes.reverse.unknown_fact_ids)
    return _query_result(graph, target, (f for f in graph.facts if f.fact_id in ids), scope)


class ReverseCache:
    def __init__(self):
        self.entries = {}

    def query(self, graph: Graph, target: str, scope=None):
        # Normalize a potentially one-shot Iterable exactly once, before any
        # cache-key, fingerprint, or indexed-query consumer can exhaust it.
        normalized_scope = None if scope is None else scope_ids(graph, scope)
        key = (target, normalized_scope)
        fingerprint = membership_key(graph, target, normalized_scope)
        old = self.entries.get(key)
        if old is not None and old.membership_fingerprint == fingerprint:
            return old, True
        result = indexed_query(graph, build_indexes(graph), target, normalized_scope)
        self.entries[key] = result
        return result, False


class ReturnedItemsOnlyCache:
    """Intentionally wrong variant used only as a distinguishing mutant."""
    def __init__(self):
        self.entries = {}

    @staticmethod
    def _key(graph, items):
        return digest({"nodes": [(n.entity_id, n.revision) for n in graph.nodes
                                 if n.entity_id in items],
                       "facts": [f for f in graph.facts if f.source in items],
                       "config": graph.compile_config,
                       "pinned": graph.config_pinned,
                       "extractor": graph.extractor_version})

    def query(self, graph: Graph, target: str):
        old = self.entries.get(target)
        if old is not None and self._key(graph, old[0].items) == old[1]:
            return old[0], True
        result = full_query(graph, target)
        self.entries[target] = (result, self._key(graph, result.items))
        return result, False


@dataclass(frozen=True)
class ImpactReport:
    decisions: tuple[tuple[str, str], ...]
    unknown_causes: tuple[str, ...]
    inspected_edges: tuple[tuple[str, str, str], ...]
    complete_in_declared_scope: bool


def impact(base: Graph, candidate: Graph, target: str, delta: FacetClaim,
           registry: Registry = REGISTRY, *, unsafe_declared_facets=False) -> ImpactReport:
    changed, cause = resolve_claim(delta, registry, unsafe=unsafe_declared_facets)
    unknown = set()
    if changed is None:
        unknown.add("DELTA:" + cause)
    if not base.scope_complete or not candidate.scope_complete:
        unknown.add("INCOMPLETE_DECLARED_SCOPE")
    if base.registry_id != registry.registry_id or candidate.registry_id != registry.registry_id:
        changed = None
        unknown.add("GRAPH_OBSERVATION_REGISTRY_MISMATCH")
    queue, visited, decisions, inspected = [(target, changed)], set(), {}, set()
    rank = {"EXCLUDED": 0, "IN_SCOPE": 1, "UNKNOWN": 2}
    while queue:
        current, facets = queue.pop(0)
        visit = (current, None if facets is None else tuple(sorted(facets)))
        if visit in visited:
            continue
        visited.add(visit)
        for side, graph in (("base", base), ("candidate", candidate)):
            for fact in graph.facts:
                if fact.target not in (current, None):
                    continue
                inspected.add((side, fact.fact_id, current))
                if guard_state(fact.guard, graph) == "FALSE":
                    decision = "EXCLUDED"
                else:
                    footprint, why = resolve_claim(fact.footprint, registry,
                                                   unsafe=unsafe_declared_facets)
                    if fact.target is None:
                        decision = "UNKNOWN"
                        unknown.add("UNKNOWN_TARGET:" + fact.fact_id)
                    elif facets is None or footprint is None:
                        decision = "UNKNOWN"
                        unknown.add("OPEN_FACETS:" + fact.fact_id + ":" + why)
                    elif facets.isdisjoint(footprint):
                        decision = "EXCLUDED"
                    else:
                        decision = "IN_SCOPE"
                previous = decisions.get(fact.source, "EXCLUDED")
                decisions[fact.source] = max((previous, decision), key=rank.get)
                if decision != "EXCLUDED":
                    # No verified output transfer function is modelled.
                    queue.append((fact.source, None))
    return ImpactReport(tuple(sorted(decisions.items())), tuple(sorted(unknown)),
                        tuple(sorted(inspected)), not unknown)


class HeadStore:
    """Pointer CAS for assumed prevalidated candidates, not acceptance policy.

    Sequential interleavings do not prove durability or real concurrency.
    """
    def __init__(self, head: str):
        self.head = head
        self.accepted = []

    def accept(self, expected_base: str, candidate: str):
        if self.head != expected_base:
            return "STALE_BASE"
        self.head = candidate
        self.accepted.append(candidate)
        return "ACCEPTED"
