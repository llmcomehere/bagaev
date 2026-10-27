# Conformance-корпус bagaev

Языконезависимые случаи соответствия. По ним проверяется любая реализация: эталон на Python (`ref/`), затем компилятор на Rust (`compiler/`). Метрика — [EXEC-1](../registry/EXEC_METHOD.md).

## Раскладка

```text
conformance/
  schema/case.schema.json      форма case.json (JSON Schema 2020-12)
  cases/<область>/<имя>/       один случай: case.json и файлы программы (*.bag)
  bridges/                     прогон замороженных моделей models/ как второй реализации (с Ф3)
  gen/                         генератор программ для дифференциальных тестов (с Ф9)
  run.py                       раннер
```

## Случай

```json
{ "id": "eval/let-shadow-01",
  "spec": ["spec/language/surface.md#let"],
  "origin": "independent",
  "levels": ["L2"],
  "files": ["main.bag"],
  "run": { "entry": "main.run", "args": [], "fuel": 10000 },
  "expect": { "phase": "run", "outcome": "RETURNED",
              "value": { "type": "Int64", "value": 7 }, "effects": [] } }
```

- `id` = `<область>/<имя>` и совпадает с путём каталога.
- `spec` — ссылки `путь#якорь` на нормативные документы; путь обязан существовать.
- `origin` — `independent`, `model:<путь>#<id>` либо `derived`. Значения описаны в [EXEC_METHOD.md §2](../registry/EXEC_METHOD.md).
- `levels` — уровни соответствия (решение D76):
  - `L1` — точная трасса и топливо, только эталон;
  - `L2` — значение, отказ, диагностика, трасса эффектов, состояние; для всех реализаций.
- `expect.phase` — `parse`, `check`, `run`, `graph`, `impact`, `context`, `edit`, `accept`, `store`, `events`.
- `expect.outcome` — исход по [outcomes.md](../spec/kernel/outcomes.md): `ACCEPTED` и `PRELAUNCH` для фаз `parse`/`check` (OUT-08); `RETURNED`, `FAULT`, `SEMANTIC_STOP` и др. для `run` (OUT-01).
- Реализация, которая ещё не поддерживает фазу, отвечает `IMPLEMENTATION_STOP` с `code: NOT_IMPLEMENTED`. Раннер засчитывает такой случай как SKIP (NOT_RUN), а не как PASS или FAIL.
- Отрицательный случай задаёт `diagnostics`: список `{code, file, span: [начало, конец), data?}`. Коды берутся из реестра DIAG-1.

## Контракт исполнителя

Реализация предоставляет команду:

```bash
<реализация> conformance-exec --case <каталог> --json
```

Она печатает одно **наблюдение** — обычный JSON-объект; канонический BAG-CJSON-1 не требуется. Поля:

| Поле | Содержание |
| --- | --- |
| `phase` | фаза, до которой дошла реализация (`parse`, `check`, `run`, …) |
| `outcome` | исход: OUT-08 для `parse`/`check`, OUT-01 для `run` |
| `value` | значение по CANON-11 (Int64 — строкой) |
| `diagnostics` | **все** диагностики в каноническом порядке SURF-58. Каждая — `{code, file, span: [начало, конец), data}`, span — целые числа; прочие поля (`phase`, `message`) допустимы |
| `effects`, `state` | трасса эффектов и состояние (Ф3–Ф4) |
| `trace_l1`, `steps` | только для уровня L1 |
| `code` | код остановки при `IMPLEMENTATION_STOP` |

Правила сравнения с `expect` по объявленным уровням:
- Сравниваются только поля, заданные в `expect`. Отсутствие поля в наблюдении не равно `null`.
- `diagnostics` — **префикс**: k-я ожидаемая диагностика сравнивается с k-й наблюдаемой. Код — точно. `span` и `file` — точно, если заданы в ожидании. `data` ожидания должна быть подмножеством `data` наблюдения. Лишние наблюдаемые диагностики после префикса допустимы.
- В L2 трасса и топливо не сравниваются.
- **NOT_RUN.** Ответ `{"outcome":"IMPLEMENTATION_STOP","code":"NOT_IMPLEMENTED","phase":P}` засчитывается как NOT_RUN, только если P совпадает с `expect.phase`. Иначе это FAIL: реализация не может «не уметь» другую фазу, чем требует случай.

```bash
python3 conformance/run.py --impl ref               # эталон
python3 conformance/run.py --impl ref --area eval   # одна область
python3 conformance/run.py --lint                   # только проверка формы случаев
```

Ожидание пишется до запуска реализации. Снятое с реализации помечается `derived`.

## Сценарий хоста (фазы `store`, `events`, `migrate`)

Случай хоста — последовательность шагов `run.steps` над одним новым хранилищем ([HOST-1](../spec/runtime/host.md)).

- Шаг — `{op, …}`: `seed`, `command`, `query`, `status`, `deliver`, `replay`, `migrate` (`action: plan | apply | abort`). Поля шага — аргументы одноимённой операции хоста (HST-17).
- `program: "v2"` — шаг исполняется программой из подкаталога `v2/` случая. Корневая программа — файлы вне таких подкаталогов. Так в одном случае живут версии до и после миграции.
- `crash_at: <точка>` — сбой в точке HST-16. Реализация моделирует его так, чтобы незафиксированное пропало, как при kill -9; наблюдение шага — `{"outcome": "CRASHED", "at": …}`.
- `lock` — шаг стенда, а не операция хоста: ставит чужой `writer_lock`, чтобы проверить остановку писателей.
- Наблюдение: `outcome: COMPLETED`, `value` — список наблюдений шагов по формам HST-17, `state` — состояние после последнего шага (программы `run.state_program`, по умолчанию — программы последнего шага).
- В сравнение не входят поля-дайджесты (`plan_id`, `from_schema`, `to_schema`, `lock`) и пояснения `detail`. Пустой объект `data` после их удаления опускается.

Ожидания сценариев выведены из правил HST вручную, генератор — [gen/make_host_cases.py](gen/make_host_cases.py). Мутационная проверка [bridges/host_mutants.py](bridges/host_mutants.py) подтверждает, что порча каждого проверяемого правила ловится хотя бы одним сценарием.

## Связи (фазы `graph`, `impact`, `context`)

Случай связей задаёт операцию `run.links` ([LINKS-1](../spec/links/08-bagaev-extraction.md)):
- `op` — `graph`, `relations`, `impact`, `why`, `context`;
- кандидат — программа из подкаталога `candidate`, перепроверка основания — из подкаталога `recheck`;
- `budget` — бюджет анализа, `unavailable` — недоступные сущности, `with_tests` — тесты кандидата как свидетельства D83(a), `watch` — сущности, чей статус включается в наблюдение, `context_budget` и `cursor` — для ContextPack.

Наблюдение — проекция ответа по **полным именам** сущностей, без дайджестов. Граф проецируется на узлы `[имя, вид]`, рёбра `[вид, источник, цель]` (без `defines`, если не задано `include_defines`), статусы покрытия и пробелы. Генератор — [gen/make_links_cases.py](gen/make_links_cases.py): ожидания выведены из правил LNK-08 вручную; сценарии C05, C08, C10, C11, C12 фикстуры authorship переведены на сущности примера с записанным соответствием узлов. Мутационная проверка — [bridges/links_mutants.py](bridges/links_mutants.py), сверка инкрементального извлечения — [tools/incremental_vs_full.py](tools/incremental_vs_full.py).

## Изменение и протокол (фазы `edit`, `accept`, `protocol`)

Случай задаёт `run.change` ([CHANGE-1](../spec/protocol/agent-protocol.md)): `principal`, необязательную `policy` и `steps`. Шаг `request` — запрос протокола без поля `protocol`; шаг может указать свой `principal`.
- Проект — копия файлов случая; перед шагами выполняется `bag project init`.
- В запросах подставляются:
  - `$change`, `$change2`, … — работы по порядку `change_begin`;
  - `$sha:<путь>` — sha256 файла текущего кандидата работы запроса;
  - `$head` — текущий head.
- Шаг `{"op": "head_files", "changes": {...}}` — правка head вне работы (чужая приёмка с записью приёмки, инвариант CHG-16); шаг `{"op": "policy", "policy": {...}}` — смена `.bagaev/policy.json` посреди работы.
- Наблюдение: `value` — проекции ответов по операциям (`conformance.project` эталона), `state.head_revision`. Дайджесты заменены на `<digest>`, ID работ — на `<change>`, ID, назначенные `assign_ids` (в ответах `apply` и `rebase`), — на `<assigned>`. Пояснения `detail`, поля `expected`, `actual`, `head`, `principal`, `diagnostics` в данных отказа не сравниваются. Проекция `accept` — каждое обязательство вне `excluded_with_basis` с основанием, заменённые условия и тесты, пробелы покрытия.

Генератор — [gen/make_change_cases.py](gen/make_change_cases.py): ожидания выведены из правил CHG вручную. Сценарии фикстуры authorship: C04 и C06 переведены на пример `examples/authorship`, C07 — на программу-приветствие. Случаи ревью m6 закрепляют найденные ложные приёмки (registry/reviews/m6.md). Мутационная проверка — [bridges/change_mutants.py](bridges/change_mutants.py).
