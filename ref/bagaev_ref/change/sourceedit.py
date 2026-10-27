"""SourceEdit CHANGE-1 (spec/protocol/agent-protocol.md §3; обобщение FixCandidate, diagnostics.md §4).

Правка — набор файлов; у каждого `base_sha256` (иначе STALE_SOURCE) и одно из:
- `edits`: замены `{start, end, text}` (байтовый полуинтервал на границах UTF-8) или `{old_text, text}`
  (ровно одно вхождение, иначе AMBIGUOUS_EDIT);
- `whole_file`: новый текст целиком;
- `delete: true` — удалить файл.
Новый файл — `{path, create: text}` без base_sha256. Правки файла не пересекаются (OVERLAPPING_EDITS) и
применяются по убыванию start. Байты вне правок не меняются — это сверяет отдельный сравнитель.
"""
from __future__ import annotations

import hashlib
import re


class EditError(Exception):
    def __init__(self, code: str, **data):
        super().__init__(code)
        self.code, self.data = code, data


SEGMENT_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")


def valid_path(path, exts=(".bag",)) -> bool:
    """Относительный путь исходника языка проекта (`*.bag`; у TypeScript — `*.ts`, `*.json`) в нормальной форме:
    без пустых сегментов, `.`, `..` и скрытых имён — иначе один файл получил бы несколько имён (`a//b.bag`)."""
    if not isinstance(path, str) or not any(path.endswith(x) and len(path.rsplit("/", 1)[-1]) > len(x) for x in exts):
        return False
    return all(SEGMENT_RE.fullmatch(x) for x in path.split("/"))


def _boundary(data: bytes, i: int) -> bool:
    """Граница скалярного значения UTF-8: не байт-продолжение 10xxxxxx."""
    return i == len(data) or (0 <= i < len(data) and (data[i] & 0xC0) != 0x80)


def _text(x) -> bool:
    """Строка, представимая в UTF-8 (одиночный суррогат — нет)."""
    if not isinstance(x, str):
        return False
    try:
        x.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def occurrences(data: bytes, sub: bytes) -> list:
    """Все вхождения, включая перекрывающиеся (`aa` в `aaa` — два)."""
    out, i = [], data.find(sub)
    while i >= 0:
        out.append(i)
        i = data.find(sub, i + 1)
    return out


def check_form(edits: list, path: str):
    """Шаг 1 CHG-04 для правок файла: форма."""
    if not isinstance(edits, list) or not edits:
        raise EditError("REQUEST_INVALID", path=path, detail="edits — непустой список")
    for k, e in enumerate(edits):
        if not isinstance(e, dict) or not _text(e.get("text")):
            raise EditError("REQUEST_INVALID", path=path, edit=k, detail="правка — {start,end,text} или {old_text,text}")
        if "old_text" in e:
            if not _text(e["old_text"]) or e["old_text"] == "" or set(e) - {"old_text", "text"}:
                raise EditError("REQUEST_INVALID", path=path, edit=k, detail="old_text — непустая строка")
        elif set(e) != {"start", "end", "text"} or not all(isinstance(e[x], int) and not isinstance(e[x], bool)
                                                           for x in ("start", "end")):
            raise EditError("REQUEST_INVALID", path=path, edit=k, detail="start и end — целые")


def spans_of(data: bytes, edits: list, path: str, stage=None) -> list:
    """Нормализовать правки файла в [(start, end, replacement_bytes, k)] с проверками CHG-04, шаги 3–5.
    `stage` — выполнить только шаг 3 (`old_text`) или 4 (диапазоны): этапы идут по всем файлам по очереди."""
    out = []
    for k, e in enumerate(edits):
        if "old_text" in e:
            if stage == "ranges":
                continue
            ob = e["old_text"].encode("utf-8")
            found = occurrences(data, ob)
            if len(found) != 1:
                raise EditError("AMBIGUOUS_EDIT", path=path, edit=k, occurrences=len(found))
            out.append((found[0], found[0] + len(ob), e["text"].encode("utf-8"), k))
        else:
            if stage == "old_text":
                continue
            s, t = e["start"], e["end"]
            if not (0 <= s <= t <= len(data)) or not _boundary(data, s) or not _boundary(data, t):
                raise EditError("RANGE_INVALID", path=path, edit=k, start=s, end=t, size=len(data))
            out.append((s, t, e["text"].encode("utf-8"), k))
    if stage is not None:
        return out
    out.sort(key=lambda x: (x[0], x[1]))
    for a, b in zip(out, out[1:]):
        # пересечение; две вставки в одну точку и вставка на краю замены — тоже неоднозначный порядок
        if b[0] < a[1] or (b[0] == a[1] and (a[0] == a[1] or b[0] == b[1])) or (a[0], a[1]) == (b[0], b[1]):
            raise EditError("OVERLAPPING_EDITS", path=path, edits=[a[3], b[3]])
    return out


def apply_spans(data: bytes, spans: list) -> bytes:
    out = data
    for s, t, rep, _ in sorted(spans, key=lambda x: -x[0]):
        out = out[:s] + rep + out[t:]
    return out


def untouched_preserved(old: bytes, new: bytes, spans: list) -> bool:
    """Независимый сравнитель (T03-C04): проход вперёд по отрезкам без правок — они идут в new в том же порядке,
    а между ними ровно тексты замен."""
    pos_old, pos_new = 0, 0
    for s, t, rep, _ in sorted(spans, key=lambda x: x[0]):
        keep = old[pos_old:s]
        if new[pos_new:pos_new + len(keep)] != keep:
            return False
        pos_new += len(keep)
        if new[pos_new:pos_new + len(rep)] != rep:
            return False
        pos_new += len(rep)
        pos_old = t
    return new[pos_new:] == old[pos_old:]


def apply_source_edit(files: dict, edit: dict, exts=(".bag",)) -> tuple[dict, dict]:
    """(новые файлы, затронутые диапазоны {path: [[start, end] в новом тексте]}) или EditError.
    Шаги CHG-04 идут по всей правке: сначала форма всех файлов, затем base_sha256 всех, затем old_text,
    диапазоны и пересечения — первый отказ по этому порядку и сообщается."""
    if not isinstance(edit, dict) or not isinstance(edit.get("files"), list) or not edit["files"]:
        raise EditError("REQUEST_INVALID", detail="SourceEdit: непустой список files")
    if set(edit) - {"files", "identity_ops", "assign_ids"}:
        raise EditError("REQUEST_INVALID", detail=f"лишние поля {sorted(set(edit) - {'files', 'identity_ops', 'assign_ids'})}")
    if not isinstance(edit.get("assign_ids", False), bool):
        raise EditError("REQUEST_INVALID", detail="assign_ids — true или false")
    seen, modes = set(), []
    for f in edit["files"]:                              # шаг 1: форма
        path = f.get("path") if isinstance(f, dict) else None
        if not valid_path(path, exts):
            raise EditError("REQUEST_INVALID", path=path if isinstance(path, str) else None,
                            detail="путь — относительный *.bag в нормальной форме, без `.`, `..` и пустых сегментов")
        if path in seen:
            raise EditError("REQUEST_INVALID", path=path, detail="файл указан дважды")
        seen.add(path)
        if "create" in f:
            if set(f) - {"path", "create"} or not _text(f["create"]):
                raise EditError("REQUEST_INVALID", path=path, detail="create — текст нового файла")
            modes.append("create")
            continue
        ms = [m for m in ("edits", "whole_file", "delete") if m in f]
        if len(ms) != 1 or set(f) - {"path", "base_sha256", ms[0]} or not isinstance(f.get("base_sha256"), str):
            raise EditError("REQUEST_INVALID", path=path, detail="base_sha256 и ровно одно из edits, whole_file, delete")
        if ms[0] == "delete" and f["delete"] is not True:
            raise EditError("REQUEST_INVALID", path=path, detail="delete: true")
        if ms[0] == "whole_file" and not _text(f["whole_file"]):
            raise EditError("REQUEST_INVALID", path=path, detail="whole_file — текст")
        if ms[0] == "edits":
            check_form(f["edits"], path)
        modes.append(ms[0])
    for f, mode in zip(edit["files"], modes):            # шаг 2: база
        path = f["path"]
        if mode == "create":
            if path in files:
                raise EditError("FILE_EXISTS", path=path)
        elif path not in files:
            raise EditError("STALE_SOURCE", path=path, detail="файла нет в кандидате")
        elif f["base_sha256"] != hashlib.sha256(files[path]).hexdigest():
            raise EditError("STALE_SOURCE", path=path, expected=f["base_sha256"],
                            actual=hashlib.sha256(files[path]).hexdigest())
    for stage in ("old_text", "ranges"):                 # шаги 3 и 4
        for f, mode in zip(edit["files"], modes):
            if mode == "edits":
                spans_of(files[f["path"]], f["edits"], f["path"], stage)
    new, touched = dict(files), {}
    for f, mode in zip(edit["files"], modes):            # шаг 5 и применение
        path = f["path"]
        if mode == "create":
            data = f["create"].encode("utf-8")
            new[path] = data
            touched[path] = [[0, len(data)]]
        elif mode == "delete":
            del new[path]
            touched[path] = []
        elif mode == "whole_file":
            data = f["whole_file"].encode("utf-8")
            new[path] = data
            touched[path] = [[0, len(data)]]
        else:
            cur = files[path]
            spans = spans_of(cur, f["edits"], path)
            data = apply_spans(cur, spans)
            if not untouched_preserved(cur, data, spans):
                raise EditError("EDIT_INVARIANT", path=path)          # защита реализации
            new[path] = data
            shift, rng = 0, []
            for s, t, rep, _ in sorted(spans, key=lambda x: x[0]):
                rng.append([s + shift, s + shift + len(rep)])
                shift += len(rep) - (t - s)
            touched[path] = rng
    return new, touched
