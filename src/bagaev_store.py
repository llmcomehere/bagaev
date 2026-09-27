"""Bounded local L2 revisions. Stored assertions never grant execution rights."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat

from . import bagaev_l2 as L2

LIMIT = 16_777_216
OBJECT_LIMIT = 512
LEDGER_LIMIT = 128
SCHEMA = "bagaev-store/1"
PACKAGE = "bagaev-store-package/1"
POLICY = "bagaev-store-policy/1"
CONTRACT = "bagaev-store-contract/1"
CONTINUATION = "bagaev-store-continuation/1"
EVIDENCE = "bagaev-store-evidence/1"
CHECKER = "bagaev-store-checker/1"
SQL = "CREATE TABLE state (id INTEGER PRIMARY KEY CHECK (id = 1), payload BLOB NOT NULL)"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")
MESSAGES = {
    "STORE_FORMAT": "Invalid store document or unresolved reference",
    "STORE_BOUND": "Store bound exceeded",
    "STORE_POLICY": "Receiver policy mismatch",
    "STORE_STALE": "Admission base does not match current head",
    "STORE_CHECK": "Required evidence is missing, failed or inapplicable",
    "STORE_OPERATION": "Operation identity is already bound to another request",
    "STORE_PATH": "Store requires an exclusive private local directory",
    "STORE_CORRUPT": "Store integrity verification failed",
    "STORE_BUSY": "Store is busy; reconcile before retrying",
}


class StoreError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(MESSAGES[code])


def _need(value, code="STORE_FORMAT"):
    if not value:
        raise StoreError(code)


def canonical(value):
    """Bounded JSON tree, including exact JSON scalar types; no custom objects."""
    count, pending = 0, [(value, 1)]
    while pending:
        item, depth = pending.pop()
        count += 1
        _need(depth <= 128 and count <= 1_000_000, "STORE_BOUND")
        kind = type(item)
        _need(kind in (dict, list, str, int, float, bool, type(None)))
        if kind is dict:
            _need(all(type(k) is str for k in item))
            pending.extend((v, depth + 1) for v in item.values())
        elif kind is list:
            pending.extend((v, depth + 1) for v in item)
        elif kind is int:
            _need(item.bit_length() <= 256, "STORE_BOUND")
        elif kind is float:
            _need(math.isfinite(item))
    try:
        data = json.dumps(value, ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (ValueError, UnicodeError, RecursionError):
        raise StoreError("STORE_FORMAT") from None
    _need(len(data) <= LIMIT, "STORE_BOUND")
    return data


def digest(value):
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def decode(data, *, exact=False):
    _need(type(data) is bytes)
    _need(len(data) <= LIMIT, "STORE_BOUND")
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result)
            result[key] = value
        return result
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(StoreError("STORE_FORMAT")))
    except (ValueError, UnicodeError, RecursionError):
        raise StoreError("STORE_FORMAT") from None
    encoded = canonical(value)
    _need(not exact or encoded == data)
    return value


def _fields(value, names):
    _need(type(value) is dict and set(value) == set(names.split()))


def _identifier(value):
    _need(type(value) is str and _ID.fullmatch(value) is not None)


def _hash(value):
    _need(type(value) is str and _HASH.fullmatch(value) is not None)


def _text(value):
    _need(type(value) is str and 0 < len(value.encode("utf-8")) <= 4096)


def _strings(values):
    _need(type(values) is list and len(values) <= 128)
    for value in values:
        _text(value)


def _head(value):
    _fields(value, "generation source")
    _need(type(value["generation"]) is int and 0 <= value["generation"] <= LEDGER_LIMIT)
    if value["source"] is not None:
        _hash(value["source"])
    _need((value["generation"] == 0) == (value["source"] is None))


def _observation(value):
    _need(type(value) is dict and (set(value) == {"value"} or set(value) == {"error"}))
    if "error" in value:
        _need(type(value["error"]) is str and value["error"] in {"L2_TYPE", "L2_FIELD", "L2_BOUNDS"})


def _contract(value):
    _fields(value, "schema cases assumptions")
    _need(value["schema"] == CONTRACT)
    _strings(value["assumptions"])
    _need(type(value["cases"]) is list and 1 <= len(value["cases"]) <= 32)
    names = set()
    for case in value["cases"]:
        _fields(case, "id input expected")
        _identifier(case["id"])
        _need(case["id"] not in names)
        names.add(case["id"])
        _observation(case["expected"])
        _need(len(canonical(case)) <= 1_048_576, "STORE_BOUND")


def _policy(value):
    _fields(value, "schema contract")
    _need(value["schema"] == POLICY, "STORE_POLICY")
    _contract(value["contract"])


def _object(state, identity, kind):
    _hash(identity)
    record = state["objects"].get(identity)
    _need(record is not None)
    # A forward reference can precede its record's turn in validation order.
    _fields(record, "kind value")
    _need(record["kind"] == kind)
    if kind == "contract":
        _contract(record["value"])
    return record["value"]


def _put(state, kind, value):
    identity = digest(value)
    record = {"kind": kind, "value": value}
    if identity in state["objects"]:
        _need(canonical(state["objects"][identity]) == canonical(record))
    else:
        state["objects"][identity] = record
    return identity


def _checker():
    # Version includes exact checker and reference source, not a caller's label.
    return {"version": CHECKER, "implementation": digest({
        name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in ("bagaev_store.py", "bagaev_l2.py")})}


def _observe(program, argument):
    try:
        return {"value": L2.evaluate(program, argument)}
    except L2.L2Error as error:
        return {"error": error.code}


def _checks(state, source, contract):
    program = L2.check_program(_object(state, source, "source"))
    definition = _object(state, contract, "contract")
    checker = _checker()
    records = []
    for case in definition["cases"]:
        actual = _observe(program, case["input"])
        records.append({"schema": EVIDENCE, "source": source, "contract": contract,
                        "case": case["id"], "input": digest(case["input"]),
                        "checker": checker, "assumptions": definition["assumptions"],
                        "result": {"status": "passed" if canonical(actual) == canonical(case["expected"])
                                   else "failed", "actual": actual}})
    return records


def _continuation(state, value):
    _fields(value, "schema task intent base target changes contract required evidence unresolved effects hypotheses")
    _need(value["schema"] == CONTINUATION)
    _identifier(value["task"])
    _text(value["intent"])
    _head(value["base"])
    _object(state, value["target"], "source")
    contract = _object(state, value["contract"], "contract")
    _need(type(value["required"]) is list and value["required"] == sorted(c["id"] for c in contract["cases"]))
    _strings(value["unresolved"])
    for key in ("changes", "evidence", "effects", "hypotheses"):
        _need(type(value[key]) is list and len(value[key]) <= 128)
    for reference in value["evidence"]:
        _object(state, reference, "evidence")
    _need(len(value["evidence"]) == len(set(value["evidence"])))
    base = value["base"]["source"]
    if base is None:
        _need(not value["changes"])
    else:
        current = L2.check_program(_object(state, base, "source"))
        for reference in value["changes"]:
            current = L2.apply_patch(current, _object(state, reference, "change"))
        _need(current.digest == value["target"])
    seen = set()
    for effect in value["effects"]:
        _fields(effect, "id status detail")
        _identifier(effect["id"])
        _need(effect["id"] not in seen and effect["status"] in ("unknown", "succeeded", "failed"))
        seen.add(effect["id"])
        _text(effect["detail"])
    for hypothesis in value["hypotheses"]:
        _fields(hypothesis, "text sources")
        _text(hypothesis["text"])
        _need(type(hypothesis["sources"]) is list and 1 <= len(hypothesis["sources"]) <= 32)
        for reference in hypothesis["sources"]:
            _hash(reference)
            _need(reference in state["objects"])


def _eligible(state, continuation, policy, *, replay):
    contract = digest(policy["contract"])
    _need(continuation["contract"] == contract, "STORE_POLICY")
    _need(not continuation["unresolved"] and
          all(e["status"] == "succeeded" for e in continuation["effects"]), "STORE_CHECK")
    expected = {c["id"]: c for c in policy["contract"]["cases"]}
    seen = set()
    for identity in continuation["evidence"]:
        value = _object(state, identity, "evidence")
        _need(value["source"] == continuation["target"] and value["contract"] == contract,
              "STORE_CHECK")
        _need(value["case"] not in seen and value["case"] in expected, "STORE_CHECK")
        seen.add(value["case"])
        _need(value["result"]["status"] == "passed", "STORE_CHECK")
    _need(seen == set(expected), "STORE_CHECK")
    if replay:
        actual = _checks(state, continuation["target"], contract)
        _need(all(e["result"]["status"] == "passed" for e in actual), "STORE_CHECK")
        _need(sorted(digest(e) for e in actual) == sorted(continuation["evidence"]), "STORE_CHECK")


def _ledger(state, ledger):
    _fields(ledger, "policy head admissions operations")
    _policy(ledger["policy"])
    _object(state, digest(ledger["policy"]["contract"]), "contract")
    _head(ledger["head"])
    _need(type(ledger["admissions"]) is list and len(ledger["admissions"]) <= LEDGER_LIMIT,
          "STORE_BOUND")
    _need(type(ledger["operations"]) is dict and len(ledger["operations"]) == len(ledger["admissions"]))
    head, seen = {"generation": 0, "source": None}, set()
    for receipt in ledger["admissions"]:
        _fields(receipt, "operation request continuation head")
        _head(receipt["head"])
        operation = receipt["operation"]
        _identifier(operation)
        _need(operation not in seen)
        seen.add(operation)
        continuation = _object(state, receipt["continuation"], "continuation")
        _need(continuation["base"] == head)
        _eligible(state, continuation, ledger["policy"], replay=False)
        head = {"generation": head["generation"] + 1, "source": continuation["target"]}
        _need(receipt["head"] == head and receipt["request"] == digest({"continuation": receipt["continuation"]}))
        _need(ledger["operations"].get(operation) == receipt)
    _need(ledger["head"] == head)


def _validate(state):
    # Reserve the full transport envelope too: every committed state exports.
    canonical({"schema": PACKAGE, "snapshot": digest(state), "state": state})
    _fields(state, "schema policy objects head admissions operations historical")
    _need(state["schema"] == SCHEMA)
    _policy(state["policy"])
    _need(type(state["objects"]) is dict and len(state["objects"]) <= OBJECT_LIMIT, "STORE_BOUND")
    for identity, record in state["objects"].items():
        _fields(record, "kind value")
        value, kind = record["value"], record["kind"]
        _need(identity == digest(value))
        if kind == "source":
            _need(L2.check_program(value).digest == identity)
        elif kind == "contract":
            _contract(value)
        elif kind == "change":
            _fields(value, "schema base target add replace")
            source = L2.check_program(_object(state, value["base"], "source"))
            target = L2.apply_patch(source, value)
            _need(target.digest == value["target"])
            _object(state, target.digest, "source")
        elif kind == "evidence":
            _fields(value, "schema source contract case input checker assumptions result")
            _need(value["schema"] == EVIDENCE)
            _object(state, value["source"], "source")
            contract = _object(state, value["contract"], "contract")
            cases = {c["id"]: c for c in contract["cases"]}
            _identifier(value["case"])
            _need(value["case"] in cases)
            _need(value["input"] == digest(cases[value["case"]]["input"]))
            _need(value["assumptions"] == contract["assumptions"])
            _fields(value["checker"], "version implementation")
            _text(value["checker"]["version"])
            _hash(value["checker"]["implementation"])
            _fields(value["result"], "status actual")
            status = value["result"]["status"]
            _need(status in ("passed", "failed", "unknown"))
            _observation(value["result"]["actual"])
            if status == "passed":
                _need(canonical(value["result"]["actual"]) == canonical(cases[value["case"]]["expected"]))
        elif kind == "continuation":
            _continuation(state, value)
        else:
            raise StoreError("STORE_FORMAT")
    _ledger(state, {k: state[k] for k in ("policy", "head", "admissions", "operations")})
    _need(type(state["historical"]) is list and len(state["historical"]) <= 8, "STORE_BOUND")
    for historical in state["historical"]:
        _fields(historical, "origin ledger")
        _hash(historical["origin"])
        _ledger(state, historical["ledger"])


def _new(policy):
    policy = decode(canonical(policy))
    _policy(policy)
    state = {"schema": SCHEMA, "policy": policy, "objects": {},
             "head": {"generation": 0, "source": None}, "admissions": [],
             "operations": {}, "historical": []}
    _put(state, "contract", policy["contract"])
    return state


def _private(path, directory=False):
    info = path.lstat()
    _need((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
          and info.st_uid == os.getuid() and not info.st_mode & 0o077
          and (directory or info.st_nlink == 1), "STORE_PATH")


def _connect(path):
    connection = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True,
                                 timeout=1.0, isolation_level=None)
    try:
        connection.enable_load_extension(False)
        for command, expected in (("journal_mode=DELETE", "delete"), ("synchronous=EXTRA", 3),
                                  ("trusted_schema=OFF", 0), ("temp_store=MEMORY", 2)):
            connection.execute("PRAGMA " + command)
            actual = connection.execute("PRAGMA " + command.split("=")[0]).fetchone()
            _need(actual == (expected,), "STORE_CORRUPT")
        _need(connection.execute("PRAGMA page_size").fetchone() == (4096,), "STORE_CORRUPT")
        _need(connection.execute("PRAGMA max_page_count=16384").fetchone() == (16384,), "STORE_BOUND")
        return connection
    except BaseException:
        connection.close()
        raise


def _sqlite_error(error):
    code = getattr(error, "sqlite_errorcode", 0) & 255
    if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
        raise StoreError("STORE_BUSY") from None
    if code in (sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB):
        raise StoreError("STORE_CORRUPT") from None
    raise error


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _install(path, state):
    _validate(state)  # All package checks precede any destination creation.
    path = Path(os.path.abspath(path))
    try:
        path.mkdir(mode=0o700)
    except OSError:
        raise StoreError("STORE_PATH") from None
    connection = None
    try:
        db = path / "state.sqlite"
        fd = os.open(db, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        connection = _connect(db)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(SQL)
        connection.execute("INSERT INTO state VALUES (1, ?)", (canonical(state),))
        connection.commit()
        connection.close()
        connection = None
        _sync_directory(path)
        _sync_directory(path.parent)
    except BaseException:
        if connection is not None:
            connection.close()
        shutil.rmtree(path)
        raise
    return digest(state)


def create(path, policy):
    """Explicit receiver selection of the immutable policy in a new directory."""
    return _install(path, _new(policy))


class Store:
    def __init__(self, path):
        path = Path(os.path.abspath(path))
        try:
            _private(path, directory=True)
            db = path / "state.sqlite"
            _private(db)
            for name in ("state.sqlite-journal", "state.sqlite-wal", "state.sqlite-shm"):
                if os.path.lexists(path / name):
                    _private(path / name)
            _need(db.stat().st_size <= 67_108_864, "STORE_BOUND")
            self.connection = _connect(db)
        except OSError:
            raise StoreError("STORE_PATH") from None
        except sqlite3.Error as error:
            _sqlite_error(error)
        try:
            with self._transaction(False):
                pass
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.connection.close()

    @contextmanager
    def _transaction(self, write):
        try:
            self.connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            schema = self.connection.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall()
            _need(schema == [("table", "state", SQL)], "STORE_CORRUPT")
            _need(self.connection.execute("PRAGMA quick_check").fetchall() == [("ok",)], "STORE_CORRUPT")
            size = self.connection.execute("SELECT id, length(payload), typeof(payload) FROM state").fetchall()
            _need(len(size) == 1 and size[0][0] == 1 and size[0][2] == "blob", "STORE_CORRUPT")
            _need(size[0][1] <= LIMIT, "STORE_BOUND")
            state = decode(self.connection.execute("SELECT payload FROM state WHERE id=1").fetchone()[0], exact=True)
            _validate(state)
            yield state
            if write:
                _validate(state)
                self.connection.execute("UPDATE state SET payload=? WHERE id=1", (canonical(state),))
            self.connection.commit()
        except sqlite3.Error as error:
            self.connection.rollback()
            _sqlite_error(error)
        except BaseException:
            self.connection.rollback()
            raise

    def put(self, kind, value):
        """Store one immutable candidate object. This does not evaluate L2."""
        value = decode(canonical(value))
        with self._transaction(True) as state:
            identity = _put(state, kind, value)
        return identity

    def check(self, source):
        """Evaluate every receiver-policy case and retain bound observations."""
        with self._transaction(True) as state:
            contract = digest(state["policy"]["contract"])
            identities = [_put(state, "evidence", e) for e in _checks(state, source, contract)]
        return identities

    def admit(self, operation_id, continuation_id):
        _identifier(operation_id)
        _hash(continuation_id)
        request = digest({"continuation": continuation_id})
        with self._transaction(True) as state:
            previous = state["operations"].get(operation_id)
            if previous is not None:
                _need(previous["request"] == request, "STORE_OPERATION")
                return previous
            continuation = _object(state, continuation_id, "continuation")
            _need(continuation["base"] == state["head"], "STORE_STALE")
            _eligible(state, continuation, state["policy"], replay=True)
            head = {"generation": state["head"]["generation"] + 1, "source": continuation["target"]}
            receipt = {"operation": operation_id, "request": request,
                       "continuation": continuation_id, "head": head}
            state["head"] = head
            state["admissions"].append(receipt)
            state["operations"][operation_id] = receipt
        return receipt

    def inspect(self, operation_id=None):
        with self._transaction(False) as state:
            if operation_id is not None:
                _identifier(operation_id)
                receipt = state["operations"].get(operation_id)
                return {"operation": operation_id, "status": "absent" if receipt is None else "committed",
                        "receipt": receipt, "head": state["head"]}
            return {"snapshot": digest(state), "policy": digest(state["policy"]),
                    "contract": digest(state["policy"]["contract"]), "head": state["head"],
                    "objects": {key: value["kind"] for key, value in state["objects"].items()},
                    "admissions": state["admissions"], "historical": len(state["historical"])}

    def get(self, identity):
        with self._transaction(False) as state:
            _hash(identity)
            _need(identity in state["objects"])
            return state["objects"][identity]

    def export(self):
        """One consistent, deterministic portable backup; no SQL is exported."""
        with self._transaction(False) as state:
            return canonical({"schema": PACKAGE, "snapshot": digest(state), "state": state})


def _package(data):
    package = decode(data, exact=True)
    _fields(package, "schema snapshot state")
    _need(package["schema"] == PACKAGE and package["snapshot"] == digest(package["state"]), "STORE_CORRUPT")
    _validate(package["state"])
    return package


def import_package(path, data, policy):
    """Import to a new destination. Imported admissions have no active authority."""
    package = _package(data)
    old, state = package["state"], _new(policy)
    state["objects"].update(old["objects"])
    state["historical"] = old["historical"] + [{"origin": package["snapshot"], "ledger": {
        k: old[k] for k in ("policy", "head", "admissions", "operations")}}]
    return _install(path, state)


def restore(path, data, policy, expected_snapshot):
    """Explicit recovery of an externally pinned whole backup, after local replay."""
    package = _package(data)
    _hash(expected_snapshot)
    _need(package["snapshot"] == expected_snapshot, "STORE_CORRUPT")
    _policy(policy)
    state = package["state"]
    _need(canonical(state["policy"]) == canonical(policy), "STORE_POLICY")
    for receipt in state["admissions"]:
        _eligible(state, _object(state, receipt["continuation"], "continuation"), policy, replay=True)
    return _install(path, state)


def backup(path, data):
    """Verify and durably create a new package file, never overwrite a backup."""
    _package(data)
    path = Path(path)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    except OSError:
        raise StoreError("STORE_PATH") from None
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _sync_directory(path.absolute().parent)
    except BaseException:
        path.unlink()
        raise
