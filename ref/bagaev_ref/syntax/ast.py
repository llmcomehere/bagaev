"""AST исходника bagaev. Каждый узел знает байтовый диапазон [start, end) в файле.
Лексическая полнота (trivia) хранится в потоке токенов файла; AST + токены образуют lossless CST.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass
class Node:
    start: int
    end: int


@dataclass
class Name(Node):
    text: str


# ---------------------------------------------------------------- атрибуты, модуль, импорт
@dataclass
class Attr(Node):
    name: Name
    args: list  # list[tuple[kind, value, start, end]]


@dataclass
class ModuleHeader(Node):
    attrs: list[Attr]
    path: list[Name]
    doc: list[str] = field(default_factory=list)


@dataclass
class UseName(Node):
    name: Name
    alias: Optional[Name]


@dataclass
class UseDecl(Node):
    path: list[Name]
    group: Optional[list[UseName]]
    alias: Optional[Name]


# ---------------------------------------------------------------- типы
@dataclass
class TypePath(Node):
    path: list[Name]
    args: list["TypeExpr"]


@dataclass
class FnType(Node):
    params: list["TypeExpr"]
    ret: "TypeExpr"
    row: Optional["EffectRow"]


@dataclass
class UnitType(Node):
    pass


TypeExpr = Union[TypePath, FnType, UnitType]


@dataclass
class EffectItem(Node):
    kind: str  # reads writes emits host
    path: list[Name]


@dataclass
class EffectRow(Node):
    items: list[EffectItem]
    var: Optional[Name]          # «| e» или голое имя «uses e»


# ---------------------------------------------------------------- декларации
@dataclass
class GenericParam(Node):
    name: Name
    bounds: list[Name]
    is_effect: bool


@dataclass
class Param(Node):
    name: Name
    type: TypeExpr


@dataclass
class LinkClause(Node):
    kind: str                    # implements requires checks supersedes
    targets: list                # list[list[Name]] или list[tuple[str, start, end]] для supersedes


@dataclass
class FieldDecl(Node):
    attrs: list[Attr]
    name: Name
    type: TypeExpr


@dataclass
class VariantDecl(Node):
    attrs: list[Attr]
    name: Name
    payload: Optional[TypeExpr]


@dataclass
class FnDecl(Node):
    name: Name
    generics: list[GenericParam]
    params: list[Param]
    ret: TypeExpr
    uses: Optional[EffectRow]
    links: list[LinkClause]
    body: "Block"


@dataclass
class EntryDecl(Node):
    kind: str                    # command query
    name: Name
    params: list[Param]
    ret: TypeExpr
    uses: Optional[EffectRow]
    links: list[LinkClause]
    body: "Block"


@dataclass
class HandlerDecl(Node):
    name: Name
    param: Param
    uses: Optional[EffectRow]
    links: list[LinkClause]
    body: "Block"


@dataclass
class MigrationDecl(Node):
    name: Name
    table: list[Name]
    param: Param
    ret: TypeExpr
    body: "Block"


@dataclass
class TestDecl(Node):
    name: Name
    uses: Optional[EffectRow]
    links: list[LinkClause]
    body: "Block"


@dataclass
class TypeDecl(Node):
    name: Name
    params: list[GenericParam]
    kind: str                    # record enum opaque
    fields: list[FieldDecl]
    variants: list[VariantDecl]
    rep: Optional[TypeExpr]


@dataclass
class EntityDecl(Node):
    name: Name
    purpose: Optional[str]
    terms: list[str]
    not_about: list[str]


@dataclass
class RuleDecl(Node):
    attrs: list[Attr]
    name: Name
    text: str


@dataclass
class ContractDecl(Node):
    name: Name
    about: list[Name]
    rules: list[RuleDecl]


@dataclass
class TableDecl(Node):
    attrs: list[Attr]
    name: Name
    type: TypeExpr
    derived_from: Optional[list[Name]]


@dataclass
class StoreDecl(Node):
    name: Name
    tables: list[TableDecl]


@dataclass
class EventDecl(Node):
    name: Name
    fields: list[FieldDecl]


@dataclass
class Item(Node):
    attrs: list[Attr]
    pub: bool
    doc: list[str]
    decl: Node
    pub_at: int = -1             # смещение слова pub


@dataclass
class File(Node):
    module: ModuleHeader
    uses: list[UseDecl]
    items: list[Item]


# ---------------------------------------------------------------- выражения
@dataclass
class Lit(Node):
    kind: str                    # int string bytes bool unit
    value: object


@dataclass
class Var(Node):
    name: Name


@dataclass
class FieldAccess(Node):
    target: "Expr"
    name: Name


@dataclass
class Call(Node):
    fn: "Expr"
    args: list["Expr"]


@dataclass
class RecordEntry(Node):
    kind: str                    # field base pair
    name: Optional[Name]
    key: Optional["Expr"]
    value: "Expr"


@dataclass
class RecordLit(Node):
    type: "Expr"                 # Var / FieldAccess — путь типа
    entries: list[RecordEntry]
    brace: int                   # смещение «{»


@dataclass
class SeqLit(Node):
    items: list["Expr"]


@dataclass
class Unary(Node):
    op: str
    operand: "Expr"


@dataclass
class Binary(Node):
    op: str
    left: "Expr"
    right: "Expr"
    op_start: int


@dataclass
class Try(Node):
    operand: "Expr"


@dataclass
class Paren(Node):
    inner: "Expr"


@dataclass
class If(Node):
    cond: "Expr"
    then: "Block"
    else_: Optional["Expr"]      # Block или If


@dataclass
class Pattern(Node):
    path: list[Name]
    binder: Optional[Name]       # None — нет «(…)»; Name("_") — пустое связывание


@dataclass
class Arm(Node):
    pattern: Pattern
    body: "Expr"


@dataclass
class Match(Node):
    scrutinee: "Expr"
    arms: list[Arm]


@dataclass
class Return(Node):
    value: Optional["Expr"]


@dataclass
class Emit(Node):
    event: list[Name]
    entries: list[RecordEntry]
    brace: int = -1              # смещение «{»


@dataclass
class LambdaParam(Node):
    name: Name
    type: Optional[TypeExpr]


@dataclass
class Lambda(Node):
    params: list[LambdaParam]
    body: "Expr"


@dataclass
class Let(Node):
    name: Name                   # text "_" — без связывания
    type: Optional[TypeExpr]
    value: "Expr"


@dataclass
class ExprStmt(Node):
    expr: "Expr"
    semi: bool


@dataclass
class Block(Node):
    stmts: list
    tail: Optional["Expr"]


Expr = Union[Lit, Var, FieldAccess, Call, RecordLit, SeqLit, Unary, Binary, Try, Paren, If, Match,
             Return, Emit, Lambda, Block]
