# DIAG-1 — единый реестр кодов

**r26 · контракт V1 (D80).** Канонический источник — [registry.json](registry.json). Реестр заменяет разнобой кодов разных документов (ledger CL-103).

## Состав записи

| Поле | Значение |
| --- | --- |
| `code` | UPPER_SNAKE; стабилен, язык сообщения его не меняет |
| `phase` | `lex`, `parse`, `resolve`, `type`, `effect`, `run`, `host`, `edit`, `accept` или `any`. Порядок фаз задаёт выбор первой (канонической) диагностики (SURF-58) |
| `kind` | `diagnostic` (PRELAUNCH), `fault`, `semantic_stop`, `implementation_stop` ([outcomes.md](../kernel/outcomes.md)) или `refusal` (отказ хоста или протокола до действия) |
| `rule` | правило-источник: `LEX-nn`, `SURF-nn`, `EFF-nn`, `CANON-nn`, `OUT-nn`, раздел TYPES-0.1 или решение |
| `message_ru` | шаблон сообщения с полями `{…}` |
| `fix` | вид машинного исправления: `none`, `insert`, `replace`, `delete`, `assign_id`, `annotate`. Предложение исправления — FixCandidate ([diagnostics.md](../toolchain/diagnostics.md) §4) |

Запись диагностики в выводе инструментов:

```json
{"code":"NON_EXHAUSTIVE_MATCH","data":{"missing":["Err"]},"file":"main.bag","phase":"type","span":["120","168"]}
```

Поле `span` — `[начало, конец)` в байтах (LEX-15). В каноническом выводе числа — строки (CANON-02). В `case.json` корпуса они записываются обычными числами.

## Псевдонимы и выведенные коды

- **`aliases`** — прежние имена из TYPES, DATA, R16–R24 и API моделей и их код DIAG-1. Инструменты принимают псевдоним во входе, но выдают только основной код.
- **`retired`** — коды, которые решения r25 сделали ненужными. Например, `RecursiveGroupRequired` (D74) и `PendingRecursiveData` (D69). В V1 они не выдаются и не принимаются.

## Правила

- Новый код появляется в реестре **до** того, как его выдаёт реализация.
- `tools/check.py` сверяет:
  - уникальность кодов;
  - коды, используемые в `ref/`;
  - коды в ожиданиях `conformance/`.
- Изменение смысла кода — новый код. Старый уходит в `retired`.
