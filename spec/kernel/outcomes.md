# KERNEL-OUTCOMES-1 — единый словарь исходов и статусов

**r26 · контракт V1 (D78).** Заменяет разнобой словарей исходов и статусов (ledger CL-106, CL-109).

Каждый словарь закрыт. Значение вне словаря — ошибка реализации, а не новый исход. Коды причин берутся из [DIAG-1](../diagnostics/registry.json).

## 1. Исход запуска программы

**OUT-01.** Поле `outcome` наблюдения `bag run` и conformance:

| Исход | Когда | Поля | Исполнялись ли шаги |
| --- | --- | --- | --- |
| `PRELAUNCH` | программа не принята: лексика, разбор, имена, типы, эффекты, неподдерживаемая возможность | `diagnostics` (первая — каноническая) | нет |
| `RETURNED` | получено значение объявленного типа; `Err(…)` — тоже значение | `value` ([canonical.md §4](canonical.md#4-наблюдаемое-значение)) | да |
| `FAULT` | определённая языком остановка программы: `ARITHMETIC_OVERFLOW`, `DIVISION_BY_ZERO`, `DUPLICATE_KEY`, `TEST_ASSERTION` | `code`, `site` (файл и диапазон узла; nid в наблюдение не входит — r30, BIR-03), `data` | да; транзакция откатывается |
| `SEMANTIC_STOP` | остановка по правилу машины: `BUDGET_EXCEEDED`, `CANCELLED` | `code` | только префикс |
| `IMPLEMENTATION_STOP` | реализация не смогла дать обещанную семантику: `NOT_IMPLEMENTED`, `RESOURCE_LIMIT`, `STACK_LIMIT`, `MACHINE_INVARIANT`, `INTERNAL_ERROR` | `code` | неизвестно; результатом программы не считается |

Различение FAULT и Result (D72): `a + b` при переполнении — FAULT, `std.i64.add(a, b)` — `RETURNED` с `Err(Overflow)`.

Уровни соответствия (D76):
- L1 (только эталон) дополнительно сравнивает `steps` и `trace_l1`.
- В реализации-компиляторе исчерпание топлива — защитный `IMPLEMENTATION_STOP` `RESOURCE_LIMIT`, а не `SEMANTIC_STOP`.

**OUT-08. Проверка до запуска** (`bag parse`, `bag check`, фазы `parse` и `check` корпуса):
- `ACCEPTED` — программа прошла фазу;
- `PRELAUNCH` с `diagnostics` — не прошла.

## 2. Исход внешней операции

**OUT-02.** EffectOutcome — ответ зарегистрированного адаптера хоста (SEM-0.1 §3):

| Исход | Значение |
| --- | --- |
| `SUCCEEDED` | операция выполнена, есть результат |
| `REJECTED` | операция не выполнена по определённому контрактом адаптера правилу, новых изменений нет |
| `INDETERMINATE` | подтверждённого исхода нет; хранится `operation_key`; повтор с этим ключом — только сверка, не новая отправка |

Прежние словари сводятся к этому:

| Прежний словарь | Где | Соответствие |
| --- | --- | --- |
| NOT_STARTED / MAY_HAVE_RUN / CONFIRMED_APPLIED / CONFIRMED_NOT_APPLIED | R16 | ещё не отправлено (нет исхода) / INDETERMINATE / SUCCEEDED / REJECTED |
| NotDispatched / MayHaveRun / Known | R23 | (нет исхода) / INDETERMINATE / SUCCEEDED или REJECTED |
| Applied / Pending / Unknown / ClosedWithoutPayload / KnownNotAdmitted | R24 | SUCCEEDED / INDETERMINATE / INDETERMINATE / SUCCEEDED без результата / REJECTED |
| 17 статусов выпуска | R20 | заморожено (D88); при возобновлении фаза выпуска хранится отдельно, исход внешней публикации — OUT-02 |

## 3. Исход точки входа

**OUT-03.** CommandOutcome — исход `command` и `handler` (D81):

| Исход | Значение | Что сохранено |
| --- | --- | --- |
| `COMMITTED` | `Ok` или успешный handler | данные, outbox, inbox, receipt — атомарно |
| `ABORTED` | `Err(e)` или FAULT | ничего, кроме receipt отказа (для повтора с тем же ключом) |
| `UNKNOWN` | ответ потерян: клиент не знает, была ли фиксация | ничего нового; узнаётся по KeyRef через `status` |

`ABORTED` с `Err(e)` — обычный исход приложения: e вернётся при повторе с тем же ключом. FAULT при повторе исполняется заново: детерминированная программа снова даст тот же FAULT.

**r31.** Квитанцию отказа получает только `Err(e)`. FAULT и остановки откатывают транзакцию целиком, и квитанции у них нет; в ответе хоста это `ABORTED` с `final: false` ([HOST-1](../runtime/host.md) HST-06). `UNKNOWN` — состояние клиента. Хост его не выдаёт; чтение квитанции даёт `RESULT` или `ABSENT_AT_READ` (HST-07).

## 4. Статусы анализа и знаний

**OUT-04.** Результат проверки утверждения (claim, evidence):

| Статус | Значение |
| --- | --- |
| `PASS` | утверждение подтверждено в объявленной области |
| `FAIL` | опровергнуто |
| `UNKNOWN` | основания недостаточно; это не PASS |

Применимость свидетельства к предмету — отдельное измерение: `applicable` / `stale` / `out_of_scope` ([01-program-model.md](../architecture/01-program-model.md)).

**OUT-05.** Статус элемента в анализе влияния ([links/03](../links/03-impact-and-context.md)):

| Статус | Значение |
| --- | --- |
| `in_scope` | затронут, нужно обработать |
| `excluded_with_basis` | исключён по сертификату (D83), сертификат хранит свои предпосылки |
| `unknown` | влияние не установлено (TOP) |
| `frontier` | анализ не дошёл (бюджет) |

Отношение к обязательству дополнительно описывается состоянием `open` / `supported` / `contradicted` / `excluded_with_basis` ([04-agent-tooling.md](../architecture/04-agent-tooling.md)). Для удалённых связей прежние метки `REMOVAL_OPEN` и `UNCHANGED_UNASSESSED` выражаются через `open` и `unknown`.

**r33.** Отчёт влияния LINKS-1 ([LNK-08-14…17](../links/08-bagaev-extraction.md#5-влияние)) имеет статус `COMPLETE` или `INCOMPLETE` и готовность `BLOCKED`, `ELIGIBLE_IF_ALL_OBLIGATIONS_PASS` или `NO_OPEN_OBLIGATIONS`. Обязательства в нём — `open`, `unknown` или `excluded_with_basis`; `supported` и `contradicted` даёт приёмка со свидетельствами (Ф6).

**OUT-06.** Покрытие ContextPack (D28): `expanded` / `boundary` / `pending` / `blocked`.

## 5. Статусы проверок инструментов

**OUT-07.** `tools/check.py`, `conformance/run.py`, `bag test`:

| Статус | Значение | Влияет на код возврата |
| --- | --- | --- |
| PASS | исполнено, совпало | нет |
| FAIL | исполнено, не совпало | да |
| ERROR | не удалось исполнить: ошибка инструмента, тайм-аут, нечитаемый вывод | да |
| SKIP | **не исполнено** (NOT_RUN) с причиной; пустой набор 0/0 — тоже SKIP | нет |
| KNOWN | разобранное расхождение со ссылкой на ERRATA | нет |
| INFO | сведения, не результат проверки | нет |

То же в [baseline.md §4](../baseline.md).
