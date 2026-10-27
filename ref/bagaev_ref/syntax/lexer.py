"""Лексер bagaev по spec/language/lexical.md (LEX-01…LEX-17).

Поток токенов с trivia: у каждого токена — ведущие пробелы и комментарии, у EOF — хвост файла.
Конкатенация trivia и текстов всех токенов побайтно равна исходнику (LEX-15).
Ошибки собираются все (режим редактора); каноническая — первая по смещению (LEX-16).
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from bagaev_ref.diag import Diagnostic

RESERVED = frozenset("module use as pub fn let if else match return emit and or not true false".split())
PUNCT = ("..", "->", "=>", "==", "!=", "<=", ">=", "++",
         "{", "}", "(", ")", "[", "]", ",", ";", ":", ".", "=", "<", ">",
         "+", "-", "*", "/", "%", "?", "@", "|", "!")
BIDI = frozenset({0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)})
INT_MAX_MAGNITUDE = 2**63          # 2^63 допустим лексически только для записи Int64::MIN (LEX-11)
LEX_RULE = {"SOURCE_BOM": 1, "INVALID_UTF8": 1, "SOURCE_NOT_NFC": 2, "FORBIDDEN_CHARACTER": 3,
            "BIDI_CONTROL_IN_SOURCE": 3, "STRAY_CR": 4}


@dataclass
class Trivia:
    kind: str          # "ws" | "comment" | "doc" | "error" (ошибочный символ вне токена)
    text: str
    start: int
    end: int


@dataclass
class Token:
    kind: str          # IDENT KW INT STRING BYTES PUNCT EOF
    text: str
    start: int
    end: int
    value: object = None
    leading: list[Trivia] = field(default_factory=list)

    def is_(self, text: str) -> bool:
        """Совпадает с терминалом: пунктуация, зарезервированное или контекстное слово."""
        return self.text == text and self.kind in ("PUNCT", "KW", "IDENT")


class _Lex:
    def __init__(self, src: str, file: str):
        self.src, self.file, self.n = src, file, len(src)
        self.off = [0]
        for ch in src:
            self.off.append(self.off[-1] + len(ch.encode("utf-8")))
        self.diags: list[Diagnostic] = []
        self.toks: list[Token] = []
        self.trivia: list[Trivia] = []

    def diag(self, code: str, a: int, b: int, **data):
        self.diags.append(Diagnostic(code, "lex", self.file, self.off[a], self.off[min(b, self.n)], data))

    def bad_char(self, k: int, in_literal: bool) -> bool:
        """LEX-03/04: проверить символ в позиции k; True — символ ошибочен (диагностика выдана)."""
        ch = self.src[k]
        cp = ord(ch)
        if cp in BIDI:
            self.diag("BIDI_CONTROL_IN_SOURCE", k, k + 1)
            return True
        if ch == "\r":
            if k + 1 < self.n and self.src[k + 1] == "\n":
                return False
            self.diag("STRAY_CR", k, k + 1)
            return True
        if (unicodedata.category(ch) == "Cc" and ch not in "\t\n") or cp in (0x2028, 0x2029):
            self.diag("FORBIDDEN_CHARACTER", k, k + 1)
            return True
        return False

    def emit(self, kind: str, i: int, j: int, value=None):
        self.toks.append(Token(kind, self.src[i:j], self.off[i], self.off[j], value, self.trivia))
        self.trivia = []

    def run(self) -> None:
        src, n, i = self.src, self.n, 0
        while i < n:
            c = src[i]
            if c in " \t\n\r":
                j = i
                while j < n and src[j] in " \t\n\r":
                    self.bad_char(j, False)
                    j += 1
                self.trivia.append(Trivia("ws", src[i:j], self.off[i], self.off[j]))
                i = j
                continue
            if src.startswith("//", i):
                j = src.find("\n", i)
                j = n if j < 0 else j
                for k in range(i, j):
                    self.bad_char(k, True)
                kind = "doc" if src.startswith("///", i) else "comment"
                self.trivia.append(Trivia(kind, src[i:j], self.off[i], self.off[j]))
                i = j
                continue
            if c == '"' or (c == "b" and src.startswith('b"', i)):
                i = self.string(i, c == "b")
                continue
            if "0" <= c <= "9":
                i = self.number(i)
                continue
            if c == "_" or c.isidentifier():
                j = i + 1
                while j < n and ("x" + src[j]).isidentifier():
                    j += 1
                text = src[i:j]
                if text == "_":
                    self.emit("PUNCT", i, j)
                else:
                    self.emit("KW" if text in RESERVED else "IDENT", i, j)
                i = j
                continue
            for p in PUNCT:
                if src.startswith(p, i):
                    self.emit("PUNCT", i, i + len(p))
                    i += len(p)
                    break
            else:
                if not self.bad_char(i, False):
                    cat = unicodedata.category(c)
                    code = "FORBIDDEN_CHARACTER" if cat in ("Zs", "Zl", "Zp", "Cf") else "UNEXPECTED_CHARACTER"
                    self.diag(code, i, i + 1)
                self.trivia.append(Trivia("error", c, self.off[i], self.off[i + 1]))   # LEX-15: байты не теряются
                i += 1
        self.toks.append(Token("EOF", "", self.off[n], self.off[n], None, self.trivia))

    def string(self, i: int, is_bytes: bool) -> int:
        src, n = self.src, self.n
        j = i + (2 if is_bytes else 1)
        out: list = []
        ok = True
        while True:
            if j >= n or src[j] == "\n" or src.startswith("\r\n", j):   # одиночный CR — STRAY_CR, не конец строки
                self.diag("UNTERMINATED_STRING", i, j)
                self.emit("BYTES" if is_bytes else "STRING", i, j, None)
                return j
            ch = src[j]
            if self.bad_char(j, True):
                ok = False
                j += 1
                continue
            if ch == '"':
                break
            if ch == "\\":
                j, val = self.escape(j, is_bytes)
                if val is None:
                    ok = False
                else:
                    out.append(val)
                continue
            if is_bytes:
                if not (0x20 <= ord(ch) <= 0x7E):
                    self.diag("INVALID_BYTE_LITERAL", j, j + 1)
                    ok = False
                else:
                    out.append(ord(ch))
            else:
                out.append(ch)
            j += 1
        value = (bytes(out) if is_bytes else "".join(out)) if ok else None
        self.emit("BYTES" if is_bytes else "STRING", i, j + 1, value)
        return j + 1

    def escape(self, j: int, is_bytes: bool):
        src, n = self.src, self.n
        e = src[j + 1] if j + 1 < n else ""
        simple = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "0": "\0"}
        if e in simple and e:
            v = simple[e]
            return j + 2, (ord(v) if is_bytes else v)
        if e == "x" and is_bytes:
            h = src[j + 2:j + 4]
            if len(h) == 2 and all(x in "0123456789abcdefABCDEF" for x in h):
                return j + 4, int(h, 16)
            self.diag("INVALID_ESCAPE", j, min(n, j + 4))
            return min(n, j + 4), None
        if e == "u" and not is_bytes:
            k = j + 2
            if k < n and src[k] == "{":
                close = src.find("}", k)
                eol = src.find("\n", k)
                if close >= 0 and (eol < 0 or close < eol):
                    body = src[k + 1:close]
                    if 1 <= len(body) <= 6 and all(x in "0123456789abcdefABCDEF" for x in body):
                        v = int(body, 16)
                        if v <= 0x10FFFF and not (0xD800 <= v <= 0xDFFF):
                            return close + 1, chr(v)
                    self.diag("INVALID_ESCAPE", j, close + 1)
                    return close + 1, None
            self.diag("INVALID_ESCAPE", j, j + 2)
            return j + 2, None
        self.diag("INVALID_ESCAPE", j, j + 2)
        return j + 2, None

    def number(self, i: int) -> int:
        src, n = self.src, self.n
        hexa = src.startswith("0x", i)
        j = i + 2 if hexa else i
        digits = "0123456789abcdefABCDEF_" if hexa else "0123456789_"
        while j < n and src[j] in digits:
            j += 1
        if not hexa and j + 1 < n and (src[j] == "." and "0" <= src[j + 1] <= "9" or src[j] in "eE"
                                       and (("0" <= src[j + 1] <= "9") or (src[j + 1] in "+-" and j + 2 < n and "0" <= src[j + 2] <= "9"))):
            k = j
            if src[k] == ".":
                k += 1
                while k < n and src[k] in "0123456789_":
                    k += 1
            if k < n and src[k] in "eE":
                k += 1
                if k < n and src[k] in "+-":
                    k += 1
                while k < n and "0" <= src[k] <= "9":
                    k += 1
            self.diag("UNSUPPORTED_FEATURE", i, k, feature_id="V1-P01")
            self.emit("INT", i, k, None)
            return k
        if j < n and ("x" + src[j]).isidentifier():
            k = j
            while k < n and ("x" + src[k]).isidentifier():
                k += 1
            self.diag("MALFORMED_NUMBER", i, k)
            self.emit("INT", i, k, None)
            return k
        text = src[i:j]
        body = text[2:] if hexa else text
        if not hexa and len(text) > 1 and text[0] == "0":
            self.diag("LEADING_ZERO", i, j)
            self.emit("INT", i, j, None)
            return j
        if not body or body[0] == "_" or body[-1] == "_" or "__" in body:
            self.diag("MALFORMED_NUMBER", i, j)
            self.emit("INT", i, j, None)
            return j
        v = int(body.replace("_", ""), 16 if hexa else 10)
        if v > INT_MAX_MAGNITUDE:
            self.diag("INT_LITERAL_OUT_OF_RANGE", i, j)
            v = None
        self.emit("INT", i, j, v)
        return j


def _nfc_diag(src: str, off: list[int], file: str) -> Diagnostic | None:
    nfc = unicodedata.normalize("NFC", src)
    if nfc == src:
        return None
    i = next((k for k, (a, b) in enumerate(zip(src, nfc)) if a != b), min(len(src), len(nfc)))
    s = i
    while s > 0 and unicodedata.combining(src[s]) != 0:
        s -= 1
    e = s + 1
    while e < len(src) and unicodedata.combining(src[e]) != 0:
        e += 1
    return Diagnostic("SOURCE_NOT_NFC", "lex", file, off[s], off[e])


def lex(data: bytes, file: str = "main.bag") -> tuple[list[Token], list[Diagnostic]]:
    """Разобрать байты исходника. Возвращает токены (последний — EOF) и все лексические диагностики."""
    if data.startswith(b"\xef\xbb\xbf"):
        return [Token("EOF", "", len(data), len(data))], [Diagnostic("SOURCE_BOM", "lex", file, 0, 3)]
    try:
        src = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as e:
        return [Token("EOF", "", len(data), len(data))], [Diagnostic("INVALID_UTF8", "lex", file, e.start, e.start + 1)]
    lx = _Lex(src, file)
    lx.run()
    nfc = _nfc_diag(src, lx.off, file)
    diags = lx.diags + ([nfc] if nfc else [])
    diags.sort(key=lambda d: (d.start, LEX_RULE.get(d.code, 9)))
    return lx.toks, diags


def reconstruct(toks: list[Token]) -> str:
    """Исходник из токенов и trivia (LEX-15)."""
    return "".join("".join(t.text for t in tok.leading) + tok.text for tok in toks)
