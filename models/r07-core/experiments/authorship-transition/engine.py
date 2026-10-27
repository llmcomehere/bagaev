"""AUTH-TX-0.1: immutable finite machine for an abstract durable boundary.

There is no database, physical crash, bagaev runtime, or external exactly-once
claim here.  Transition.actual_commit is harness truth; caller knowledge is
represented separately by Observation.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace as dc_replace
from hashlib import sha256
import json
from typing import Any


PROFILE_REVISION = "authorship-transition/r05-v1"
OPERATION_ID = "ReplaceAuthorship/v1"
HANDLER_ID = "authorship-index"
EVENT_TYPE = "ArticleAuthorshipChanged"
EVENT_SCHEMA = "AuthorshipEventV2"
MAX_VERSION = 2**63 - 1
MAX_ENTITIES, MAX_MEMBERS, MAX_RECORDS = 32, 32, 512
CUTS = ("none", "before_commit", "after_commit_before_reply")


class ModelError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code, self.detail = code, detail
        super().__init__(code + (": " + detail if detail else ""))


def _text(value, *, derived=False):
    if type(value) is not str or not value:
        raise ModelError("INVALID_ID")
    if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ModelError("INVALID_UNICODE_SCALAR")
    if len(value) > (512 if derived else 256):
        raise ModelError("ID_LIMIT")
    return value


def _version(value):
    if type(value) is not int or not 1 <= value <= MAX_VERSION:
        raise ModelError("INVALID_VERSION")
    return value


def _tuple(values, limit):
    if isinstance(values, (str, bytes)):
        raise ModelError("INVALID_COLLECTION")
    try:
        iterator = iter(values)
    except TypeError as error:
        raise ModelError("INVALID_COLLECTION") from error
    result = []
    for item in iterator:
        if len(result) >= limit:
            raise ModelError("CAPACITY_LIMIT")
        result.append(item)
    return tuple(result)


def _ids(values, *, ordered=True, unique=False, limit=MAX_MEMBERS):
    values = _tuple(values, limit)
    for value in values:
        _text(value)
    if unique and len(set(values)) != len(values):
        raise ModelError("DUPLICATE_ID")
    return values if ordered else tuple(sorted(values))


def canonical(value):
    if is_dataclass(value):
        return {f.name: canonical(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        if not all(type(k) is str for k in value):
            raise ModelError("NON_CANONICAL_VALUE")
        return {key: canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [canonical(item) for item in value]
    if value is None or type(value) in (bool, int, str):
        return value
    raise ModelError("NON_CANONICAL_VALUE", type(value).__name__)


def _json(value):
    return json.dumps(canonical(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def digest(value):
    return sha256(_json(value).encode("utf-8")).hexdigest()


def _same(left, right):
    return _json(left) == _json(right)


@dataclass(frozen=True)
class Article:
    article_id: str
    article_revision: int
    author_ids: tuple[str, ...]
    editor_ids: tuple[str, ...]

    def __post_init__(self):
        _text(self.article_id)
        _version(self.article_revision)
        authors = _ids(self.author_ids, unique=True)
        if not authors:
            raise ModelError("EMPTY_ARTICLE_AUTHORS")
        object.__setattr__(self, "author_ids", authors)
        object.__setattr__(self, "editor_ids", _ids(self.editor_ids, ordered=False, unique=True))


@dataclass(frozen=True)
class ReplaceAuthorship:
    command_id: str
    actor_id: str
    article_id: str
    expected_article_version: int
    author_ids: tuple[str, ...]

    def __post_init__(self):
        for value in (self.command_id, self.actor_id, self.article_id):
            _text(value)
        _version(self.expected_article_version)
        object.__setattr__(self, "author_ids", _ids(self.author_ids))


@dataclass(frozen=True)
class Event:
    event_id: str
    store_id: str
    causation_id: str
    causation_actor_id: str
    article_id: str
    article_revision: int
    author_ids: tuple[str, ...]
    event_type: str = EVENT_TYPE
    schema_revision: str = EVENT_SCHEMA

    def __post_init__(self):
        _text(self.event_id, derived=True)
        for value in (self.store_id, self.causation_id, self.causation_actor_id,
                      self.article_id, self.event_type, self.schema_revision):
            _text(value)
        _version(self.article_revision)
        object.__setattr__(self, "author_ids", _ids(self.author_ids))


@dataclass(frozen=True)
class CommandReceipt:
    store_id: str
    request: ReplaceAuthorship
    request_binding: str
    status: str
    article_revision: int
    event_id: str | None
    committed_state_version: int

    def __post_init__(self):
        for value in (self.store_id, self.request_binding, self.status):
            _text(value)
        if not isinstance(self.request, ReplaceAuthorship):
            raise ModelError("INVALID_REQUEST")
        if self.event_id is not None:
            _text(self.event_id, derived=True)
        _version(self.article_revision)
        _version(self.committed_state_version)


@dataclass(frozen=True)
class Projection:
    article_id: str
    article_revision: int
    author_ids: tuple[str, ...]

    def __post_init__(self):
        _text(self.article_id)
        _version(self.article_revision)
        authors = _ids(self.author_ids, unique=True)
        if not authors:
            raise ModelError("EMPTY_PROJECTION_AUTHORS")
        object.__setattr__(self, "author_ids", authors)


@dataclass(frozen=True)
class AuthorIndexEntry:
    person_id: str
    article_ids: tuple[str, ...]

    def __post_init__(self):
        _text(self.person_id)
        object.__setattr__(self, "article_ids", _ids(self.article_ids, ordered=False, unique=True))


@dataclass(frozen=True)
class InboxEntry:
    handler_id: str
    event_id: str
    event_binding: str

    def __post_init__(self):
        _text(self.handler_id)
        _text(self.event_id, derived=True)
        _text(self.event_binding)


@dataclass(frozen=True)
class ProjectionReceipt:
    store_id: str
    handler_id: str
    event: Event
    event_binding: str
    status: str
    projected_article_revision: int
    committed_state_version: int

    def __post_init__(self):
        for value in (self.store_id, self.handler_id, self.event_binding, self.status):
            _text(value)
        if not isinstance(self.event, Event):
            raise ModelError("INVALID_EVENT")
        _version(self.projected_article_revision)
        _version(self.committed_state_version)


@dataclass(frozen=True)
class AckReceipt:
    store_id: str
    handler_id: str
    event_id: str
    event_binding: str
    projection_receipt_binding: str
    committed_state_version: int

    def __post_init__(self):
        for value in (self.store_id, self.handler_id, self.event_binding, self.projection_receipt_binding):
            _text(value)
        _text(self.event_id, derived=True)
        _version(self.committed_state_version)


def _records(values, record_type, key, limit=MAX_RECORDS):
    values = _tuple(values, limit)
    if not all(isinstance(item, record_type) for item in values):
        raise ModelError("INVALID_RECORD_TYPE", record_type.__name__)
    if len({key(item) for item in values}) != len(values):
        raise ModelError("DUPLICATE_RECORD_KEY", record_type.__name__)
    return tuple(sorted(values, key=key))


@dataclass(frozen=True)
class DurableState:
    store_id: str
    state_version: int
    people: tuple[str, ...]
    articles: tuple[Article, ...]
    outbox: tuple[Event, ...] = ()
    command_receipts: tuple[CommandReceipt, ...] = ()
    projections: tuple[Projection, ...] = ()
    author_index: tuple[AuthorIndexEntry, ...] = ()
    inbox: tuple[InboxEntry, ...] = ()
    projection_receipts: tuple[ProjectionReceipt, ...] = ()
    acknowledgements: tuple[AckReceipt, ...] = ()

    def __post_init__(self):
        _text(self.store_id)
        _version(self.state_version)
        object.__setattr__(self, "people", _ids(self.people, ordered=False, unique=True, limit=MAX_ENTITIES))
        specifications = (
            ("articles", Article, lambda r: r.article_id, MAX_ENTITIES),
            ("outbox", Event, lambda r: r.event_id, MAX_RECORDS),
            ("command_receipts", CommandReceipt, lambda r: (r.request.actor_id, r.request.command_id), MAX_RECORDS),
            ("projections", Projection, lambda r: r.article_id, MAX_ENTITIES),
            ("author_index", AuthorIndexEntry, lambda r: r.person_id, MAX_ENTITIES),
            ("inbox", InboxEntry, lambda r: (r.handler_id, r.event_id), MAX_RECORDS),
            ("projection_receipts", ProjectionReceipt, lambda r: (r.handler_id, r.event.event_id), MAX_RECORDS),
            ("acknowledgements", AckReceipt, lambda r: r.event_id, MAX_RECORDS))
        for name, record_type, key, limit in specifications:
            object.__setattr__(self, name, _records(getattr(self, name), record_type, key, limit))


@dataclass(frozen=True)
class Observation:
    status: str
    code: str
    receipt: CommandReceipt | ProjectionReceipt | AckReceipt | None = None
    observed_state_version: int | None = None
    replayed: bool = False


@dataclass(frozen=True)
class Transition:
    state: DurableState
    actual_commit: bool
    observation: Observation


@dataclass(frozen=True)
class TransitionStatus:
    state_version: int
    pending_event_ids: tuple[str, ...]
    lagging_article_ids: tuple[str, ...]
    complete: bool


def request_binding(state, request):
    return digest({"binding": "authorship-command/r05-v1", "profile_revision": PROFILE_REVISION,
                   "operation_id": OPERATION_ID, "event_schema": EVENT_SCHEMA,
                   "store_id": state.store_id, "request": canonical(request)})


def event_binding(event):
    return digest({"binding": "authorship-event/r05-v1", "profile_revision": PROFILE_REVISION,
                   "event": canonical(event)})


def projection_receipt_binding(receipt):
    return digest({"binding": "authorship-projection-receipt/r05-v1", "profile_revision": PROFILE_REVISION,
                   "receipt": canonical(receipt)})


def event_id(article_id, revision):
    return "ev_" + article_id + "_r" + str(revision)


def _index(people, projections):
    rows = {person: set() for person in people}
    for projection in projections:
        for person in projection.author_ids:
            if person not in rows:
                raise ModelError("STATE_CORRUPTION", "unknown projection person")
            rows[person].add(projection.article_id)
    return tuple(AuthorIndexEntry(person, tuple(sorted(rows[person]))) for person in sorted(rows))


def _state_error(condition, detail):
    if not condition:
        raise ModelError("STATE_CORRUPTION", detail)


def validate_state(state):
    if not isinstance(state, DurableState):
        raise ModelError("INVALID_STATE")
    articles = {a.article_id: a for a in state.articles}
    projections = {p.article_id: p for p in state.projections}
    people = set(state.people)
    _state_error(set(articles) == set(projections), "projection article keys")
    for article in state.articles:
        _state_error(set(article.author_ids) <= people, "unknown article person")
    for projection in state.projections:
        article = articles[projection.article_id]
        _state_error(projection.article_revision <= article.article_revision, "projection ahead of source")
        if projection.article_revision == article.article_revision:
            _state_error(projection.author_ids == article.author_ids, "same revision has different authors")
    _state_error(_same(state.author_index, _index(state.people, state.projections)), "index differs from projections")
    events = {e.event_id: e for e in state.outbox}
    commands = {(r.request.actor_id, r.request.command_id): r for r in state.command_receipts}
    for receipt in state.command_receipts:
        request = receipt.request
        article = articles.get(request.article_id)
        _state_error(article is not None, "receipt article absent")
        _state_error(receipt.store_id == state.store_id, "command store mismatch")
        _state_error(receipt.request_binding == request_binding(state, request), "command binding mismatch")
        _state_error(1 < receipt.committed_state_version <= state.state_version, "command receipt StateVersion")
        _state_error(bool(request.author_ids) and len(set(request.author_ids)) == len(request.author_ids)
                     and set(request.author_ids) <= people, "invalid committed authors")
        _state_error(receipt.article_revision <= article.article_revision, "receipt ahead of article")
        if receipt.status == "UPDATED":
            _state_error(receipt.article_revision == request.expected_article_version + 1,
                         "updated receipt article revision")
            _state_error(receipt.event_id == event_id(request.article_id, receipt.article_revision), "receipt event ID")
            expected = Event(receipt.event_id, state.store_id, request.command_id, request.actor_id,
                             request.article_id, receipt.article_revision, request.author_ids)
            _state_error(receipt.event_id in events and _same(events[receipt.event_id], expected),
                         "command event missing/different")
        elif receipt.status == "NOOP":
            _state_error(receipt.article_revision == request.expected_article_version and receipt.event_id is None,
                         "noop receipt changed article/event")
        else:
            raise ModelError("STATE_CORRUPTION", "unknown command receipt status")
        if receipt.article_revision == article.article_revision:
            _state_error(request.author_ids == article.author_ids, "current receipt authors differ")
    for event in state.outbox:
        _state_error(event.store_id == state.store_id and event.event_type == EVENT_TYPE
                     and event.schema_revision == EVENT_SCHEMA, "outbox profile mismatch")
        receipt = commands.get((event.causation_actor_id, event.causation_id))
        _state_error(receipt is not None and receipt.status == "UPDATED" and receipt.event_id == event.event_id,
                     "outbox has no exact command receipt")
    receipts = {(r.handler_id, r.event.event_id): r for r in state.projection_receipts}
    inbox = {(i.handler_id, i.event_id): i for i in state.inbox}
    _state_error(set(inbox) == set(receipts), "inbox/receipt atomicity")
    for key, receipt in receipts.items():
        event = events.get(receipt.event.event_id)
        _state_error(receipt.store_id == state.store_id and receipt.handler_id == HANDLER_ID,
                     "projection namespace mismatch")
        _state_error(event is not None and _same(event, receipt.event), "projection source event mismatch")
        binding = event_binding(event)
        _state_error(receipt.event_binding == binding and inbox[key].event_binding == binding,
                     "projection event binding mismatch")
        source_receipt = commands[(event.causation_actor_id, event.causation_id)]
        _state_error(source_receipt.committed_state_version < receipt.committed_state_version <= state.state_version,
                     "projection receipt StateVersion")
        current = projections[event.article_id]
        _state_error(receipt.projected_article_revision <= current.article_revision, "projection regressed")
        if receipt.status in {"APPLIED", "ALREADY_CURRENT"}:
            _state_error(receipt.projected_article_revision == event.article_revision, "applied revision mismatch")
            if current.article_revision == event.article_revision:
                _state_error(current.author_ids == event.author_ids, "applied authors mismatch")
        elif receipt.status == "SUPERSEDED":
            _state_error(receipt.projected_article_revision > event.article_revision, "not superseded")
        else:
            raise ModelError("STATE_CORRUPTION", "unknown projection receipt status")
    for ack in state.acknowledgements:
        event = events.get(ack.event_id)
        receipt = receipts.get((ack.handler_id, ack.event_id))
        _state_error(ack.store_id == state.store_id and ack.handler_id == HANDLER_ID, "ack namespace")
        _state_error(event is not None and receipt is not None, "ack before completed processing")
        _state_error(ack.event_binding == event_binding(event)
                     and ack.projection_receipt_binding == projection_receipt_binding(receipt), "ack binding")
        _state_error(receipt.committed_state_version < ack.committed_state_version <= state.state_version,
                     "ack StateVersion")


def make_initial_state(store_id, people, articles):
    articles = _records(articles, Article, lambda a: a.article_id, MAX_ENTITIES)
    people = _ids(people, ordered=False, unique=True, limit=MAX_ENTITIES)
    projections = tuple(Projection(a.article_id, a.article_revision, a.author_ids) for a in articles)
    state = DurableState(store_id, 1, people, articles, projections=projections,
                         author_index=_index(people, projections))
    validate_state(state)
    return state


def _options(expected_state_version, cut):
    if expected_state_version is not None:
        _version(expected_state_version)
    if type(cut) is not str or cut not in CUTS:
        raise ModelError("UNSUPPORTED_CUT")


def _reject(state, code):
    return Transition(state, False, Observation("REJECTED", code, observed_state_version=state.state_version))


def _result(state, receipt, *, replayed=False):
    code = "ACKNOWLEDGED" if isinstance(receipt, AckReceipt) else receipt.status
    return Observation("RESULT", code, receipt, state.state_version, replayed)


def _commit(old, new, receipt, cut):
    # Both snapshots are immutable.  Construct/check the whole candidate before
    # exposing a single abstract durable commit; no partial state is published.
    validate_state(new)
    if cut == "before_commit":
        return Transition(old, False, Observation("UNKNOWN", "REPLY_LOST"))
    if cut == "after_commit_before_reply":
        return Transition(new, True, Observation("UNKNOWN", "REPLY_LOST"))
    return Transition(new, True, _result(new, receipt))


def _command_access(state, request):
    if not isinstance(request, ReplaceAuthorship):
        raise ModelError("INVALID_REQUEST")
    article = next((a for a in state.articles if a.article_id == request.article_id), None)
    if article is None:
        return None, "UNKNOWN_ARTICLE"
    if request.actor_id not in article.editor_ids:
        return None, "PERMISSION_DENIED"
    return article, None


def _command_receipt(state, request):
    return next((r for r in state.command_receipts
                 if r.request.actor_id == request.actor_id and r.request.command_id == request.command_id), None)


def replace_authorship(state, request, *, expected_state_version=None, cut="none"):
    _options(expected_state_version, cut)
    validate_state(state)
    article, denied = _command_access(state, request)
    if denied:
        return _reject(state, denied)
    previous = _command_receipt(state, request)
    if previous is not None:
        if not _same(previous.request, request) or previous.request_binding != request_binding(state, request):
            return _reject(state, "IDEMPOTENCY_CONFLICT")
        return Transition(state, False, _result(state, previous, replayed=True))
    if expected_state_version is not None and expected_state_version != state.state_version:
        return _reject(state, "STATE_CONFLICT")
    if not request.author_ids:
        return _reject(state, "EMPTY_AUTHORS")
    if len(set(request.author_ids)) != len(request.author_ids):
        return _reject(state, "DUPLICATE_AUTHOR")
    if not set(request.author_ids) <= set(state.people):
        return _reject(state, "UNKNOWN_PERSON")
    if request.expected_article_version != article.article_revision:
        return _reject(state, "ARTICLE_CONFLICT")
    changed = request.author_ids != article.author_ids
    if state.state_version == MAX_VERSION or (changed and article.article_revision == MAX_VERSION):
        return _reject(state, "VERSION_EXHAUSTED")
    revision = article.article_revision + int(changed)
    new_event_id = event_id(article.article_id, revision) if changed else None
    receipt = CommandReceipt(state.store_id, request, request_binding(state, request),
                             "UPDATED" if changed else "NOOP", revision, new_event_id, state.state_version + 1)
    replacements = {"state_version": state.state_version + 1,
                    "command_receipts": state.command_receipts + (receipt,)}
    if changed:
        updated = dc_replace(article, article_revision=revision, author_ids=request.author_ids)
        event = Event(new_event_id, state.store_id, request.command_id, request.actor_id,
                      article.article_id, revision, request.author_ids)
        replacements["articles"] = tuple(updated if a.article_id == article.article_id else a for a in state.articles)
        replacements["outbox"] = state.outbox + (event,)
    new = dc_replace(state, **replacements)
    return _commit(state, new, receipt, cut)


def _event_access(state, event):
    if not isinstance(event, Event):
        raise ModelError("INVALID_EVENT")
    source = next((e for e in state.outbox if e.event_id == event.event_id), None)
    return source is not None and _same(source, event)


def _projection_receipt(state, event_id_value):
    return next((r for r in state.projection_receipts
                 if r.handler_id == HANDLER_ID and r.event.event_id == event_id_value), None)


def deliver_event(state, event, *, expected_state_version=None, cut="none"):
    _options(expected_state_version, cut)
    validate_state(state)
    if not _event_access(state, event):
        return _reject(state, "EVENT_CORRUPTION")
    previous = _projection_receipt(state, event.event_id)
    if previous is not None:
        if not _same(previous.event, event) or previous.event_binding != event_binding(event):
            return _reject(state, "EVENT_CORRUPTION")
        return Transition(state, False, _result(state, previous, replayed=True))
    if expected_state_version is not None and expected_state_version != state.state_version:
        return _reject(state, "STATE_CONFLICT")
    current = next(p for p in state.projections if p.article_id == event.article_id)
    if event.article_revision > current.article_revision:
        outcome = "APPLIED"
        projection = Projection(event.article_id, event.article_revision, event.author_ids)
    elif event.article_revision < current.article_revision:
        outcome, projection = "SUPERSEDED", current
    elif event.author_ids == current.author_ids:
        outcome, projection = "ALREADY_CURRENT", current
    else:
        return _reject(state, "PROJECTION_VERSION_CONFLICT")
    if state.state_version == MAX_VERSION:
        return _reject(state, "VERSION_EXHAUSTED")
    binding = event_binding(event)
    receipt = ProjectionReceipt(state.store_id, HANDLER_ID, event, binding, outcome,
                                projection.article_revision, state.state_version + 1)
    projections = tuple(projection if p.article_id == event.article_id else p for p in state.projections)
    new = dc_replace(state, state_version=state.state_version + 1,
                     projections=projections, author_index=_index(state.people, projections),
                     inbox=state.inbox + (InboxEntry(HANDLER_ID, event.event_id, binding),),
                     projection_receipts=state.projection_receipts + (receipt,))
    return _commit(state, new, receipt, cut)


def acknowledge_event(state, event_id, *, expected_state_version=None, cut="none"):
    _options(expected_state_version, cut)
    _text(event_id, derived=True)
    validate_state(state)
    event = next((e for e in state.outbox if e.event_id == event_id), None)
    if event is None:
        return _reject(state, "UNKNOWN_EVENT")
    projection_receipt = _projection_receipt(state, event_id)
    if projection_receipt is None:
        return _reject(state, "EVENT_NOT_PROCESSED")
    previous = next((r for r in state.acknowledgements if r.event_id == event_id), None)
    if previous is not None:
        return Transition(state, False, _result(state, previous, replayed=True))
    if expected_state_version is not None and expected_state_version != state.state_version:
        return _reject(state, "STATE_CONFLICT")
    if state.state_version == MAX_VERSION:
        return _reject(state, "VERSION_EXHAUSTED")
    receipt = AckReceipt(state.store_id, HANDLER_ID, event_id, event_binding(event),
                         projection_receipt_binding(projection_receipt), state.state_version + 1)
    new = dc_replace(state, state_version=state.state_version + 1,
                     acknowledgements=state.acknowledgements + (receipt,))
    return _commit(state, new, receipt, cut)


def _available(available):
    if type(available) is not bool:
        raise ModelError("INVALID_AVAILABILITY_FLAG")


def recover_command(state, request, *, available=True):
    _available(available)
    if not isinstance(request, ReplaceAuthorship):
        raise ModelError("INVALID_REQUEST")
    if not available:
        return Observation("UNKNOWN", "READ_UNAVAILABLE")
    validate_state(state)
    _, denied = _command_access(state, request)
    if denied:
        return _reject(state, denied).observation
    receipt = _command_receipt(state, request)
    if receipt is None:
        return Observation("ABSENT_AT_READ", "NO_RECEIPT", observed_state_version=state.state_version)
    if not _same(receipt.request, request) or receipt.request_binding != request_binding(state, request):
        return _reject(state, "IDEMPOTENCY_CONFLICT").observation
    return _result(state, receipt, replayed=True)


def recover_event(state, event, *, available=True):
    _available(available)
    if not isinstance(event, Event):
        raise ModelError("INVALID_EVENT")
    if not available:
        return Observation("UNKNOWN", "READ_UNAVAILABLE")
    validate_state(state)
    if not _event_access(state, event):
        return _reject(state, "EVENT_CORRUPTION").observation
    receipt = _projection_receipt(state, event.event_id)
    if receipt is None:
        return Observation("ABSENT_AT_READ", "NO_RECEIPT", observed_state_version=state.state_version)
    return _result(state, receipt, replayed=True)


def search(state, person_id):
    _text(person_id)
    validate_state(state)
    row = next((r for r in state.author_index if r.person_id == person_id), None)
    if row is None:
        raise ModelError("UNKNOWN_PERSON")
    return row.article_ids


def status(state):
    validate_state(state)
    acknowledged = {r.event_id for r in state.acknowledgements}
    pending = tuple(sorted(e.event_id for e in state.outbox if e.event_id not in acknowledged))
    projections = {p.article_id: p for p in state.projections}
    lagging = tuple(a.article_id for a in state.articles
                    if (projections[a.article_id].article_revision != a.article_revision
                        or projections[a.article_id].author_ids != a.author_ids))
    return TransitionStatus(state.state_version, pending, lagging, not pending and not lagging)
