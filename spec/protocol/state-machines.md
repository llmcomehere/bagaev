# Конечные автоматы CHANGE-1

**r34 (с поправками ревью m6).** Состояния работ, обязательств, квитанций и head протокола агента ([agent-protocol.md](agent-protocol.md)). Переход вне таблицы невозможен: операция, которая его требует, отказывает с указанным кодом и ничего не пишет.

## Работа

| Из | Операция | В | Условие | Отказ |
| --- | --- | --- | --- | --- |
| — | `change_begin` | `open`, ревизия 1 | head есть | `PROJECT_NOT_INITIALIZED` |
| `open` (r) | `contract_update` | `open` (r + 1) | ожидаемая ревизия = r; форма операций контракта | `WORK_CONFLICT`, `REQUEST_INVALID` |
| `open` (r) | `apply` | `open` (r + 1) | ожидаемая ревизия = r; правка проходит CHG-04 и CHG-06 | `WORK_CONFLICT`, `REQUEST_INVALID`, `STALE_SOURCE`, `FILE_EXISTS`, `AMBIGUOUS_EDIT`, `RANGE_INVALID`, `OVERLAPPING_EDITS`, `CANDIDATE_UNPARSABLE`, `DUPLICATE_ENTITY_ID`, `ENTITY_ID_RETIRED`, `ENTITY_KIND_CHANGED`, `ENTITY_REMOVED_WITHOUT_INTENT`, `IDENTITY_OP_MISMATCH` |
| `open` (r) | `verify` | `open` (r + 1) | ожидаемая ревизия = r; кандидат проходит CHECK-1 | `WORK_CONFLICT`, `CANDIDATE_INVALID` |
| `open` (r) | `rebase` | `open` (r + 1) | ожидаемая ревизия = r; head ≠ база; журнал правок переносится | `WORK_CONFLICT`, `REBASE_NOT_NEEDED`, `REBASE_CONFLICT`, `CANDIDATE_UNPARSABLE` |
| `open` (r) | `accept` | `accepted` (r + 1) | head = база, блокеров нет | `STALE_BASE`, `OPEN_OBLIGATIONS` |
| `open` (r) | `abandon` | `abandoned` (r + 1) | причина | `REQUEST_INVALID` |
| `accepted`, `abandoned` | любая запись | — | — | `WORK_CONFLICT` |

Любая операция: `REQUEST_INVALID`, `UNKNOWN_OPERATION`, `UNKNOWN_CHANGE`, `ACCESS_DENIED`, `IDEMPOTENCY_CONFLICT`, `POLICY_INVALID`, `INTERNAL` — без записи. Чтения (`work_resume` и др.) состояние не меняют; единственная запись — производный кэш графа (CHG-01).

## Обязательство (производное, CHG-13)

| Состояние | Когда |
| --- | --- |
| `excluded_with_basis` | D83(b); D83(a), если политика допускает его для вида (LNK-08-15…17); цель удалена объявленным `delete` |
| `unknown` | декларация unknown или во frontier, анализ неполон |
| `open` | выбывший тест базы без `replace_test`, методов нет, нет допустимого основания, свидетельство отсутствует или устарело |
| `supported` | допустимое основание политики: применимый PASS каждого метода правила (CHG-13), методы преемников при split/merge или принятое предположение |
| `contradicted` | применимый FAIL метода |

Состояние не хранится: смена кандидата, свидетельств, контракта или политики сразу даёт новое. `unknown`, `open` и `contradicted` блокируют приёмку; так же блокеры `EVIDENCE_CONTRADICTED`, `TESTS_NOT_RUN`, `POLICY_CHANGED` и прочие CHG-13.

## Квитанция операции записи

| Состояние | Переход |
| --- | --- |
| нет | операция дошла до фиксации → `stored` (вместе с изменением) |
| нет | отказ до фиксации → нет (ключ свободен) |
| `stored` | тот же дайджест → ответ из квитанции, `replayed: true` |
| `stored` | другой дайджест → `IDEMPOTENCY_CONFLICT` |

Ключи не истекают (CANON-10).

## Head

| Из | Переход | Условие |
| --- | --- | --- |
| нет | `project init` → S0, ревизия 1 | проект пуст |
| H (n) | `accept` работы с базой H → кандидат (n + 1) | в одной транзакции с записью приёмки |
| H (n) | `accept` работы с базой ≠ H | `STALE_BASE`, head = H |
