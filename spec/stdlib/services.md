# STD-SERVICE-1 — хранилище и события в программе (D81)

**r31 · WORKING_DESIGN.** Документ заменяет STD-SERVICE-0.1 (R24; прежний текст — тег `r24`). Хранилище и события в V1 — это не библиотечные сервисы с capability-значениями, а эффекты точек входа: атомы `reads`/`writes`/`emits` в рядах ([effects.md §4](../language/effects.md)), операции `std.store`, форма `emit` и объявление `handler`. Транзакцию открывает и фиксирует хост ([HOST-1](../runtime/host.md)); программа её не видит и ею не управляет.

## 1. Что доступно программе

| Средство | Сигнатура | Атом | Где исполняется |
| --- | --- | --- | --- |
| `store.get` | `<K: Key, V>(Table<K, V>, K) -> Option<V>` | `reads t` | Perform (HST-08) |
| `store.contains` | `<K: Key, V>(Table<K, V>, K) -> Bool` | `reads t` | Perform |
| `store.all` | `<K: Key, V>(Table<K, V>) -> Map<K, V>` | `reads t` | Perform |
| `store.put` | `<K: Key, V>(Table<K, V>, K, V) -> ()` | `writes t` | Perform |
| `store.remove` | `<K: Key, V>(Table<K, V>, K) -> ()` | `writes t` | Perform |
| `store.replace_all` | `<K: Key, V>(Table<K, V>, Map<K, V>) -> ()` | `writes t` | Perform |
| `emit E { … }` | форма языка | `emits E` | Perform: событие в outbox после фиксации |
| `handler h(ev: E)` | объявление | `consumes E` неявно | хост доставляет события E (HST-11) |

- Таблица — объявление `table` внутри `store`; её значение `Table<K, V>` нельзя сохранить, передать в данные или создать в программе: это имя ресурса, а не capability.
- Чтение видит записи своей транзакции. `store.all` возвращает снимок таблицы как `Map` в порядке Key.
- Функции `std.store` вызываются из `fn`, если ряд точки входа покрывает их атомы (EFF-08). Вне транзакции такой вызов отклоняется до запуска: `HOST_EFFECT_OUTSIDE_TRANSACTION`.

## 2. Транзакции

**SVC-01.** `command` — одна транзакция с ключом идемпотентности (KeyRef, CANON-10). Порядок проверок и исходы — HST-05 и HST-06:
- `Ok` фиксирует записи, события и квитанцию;
- `Err` — окончательный ответ с квитанцией без изменений данных;
- FAULT и остановки ничего не фиксируют.

**SVC-02.** `handler` — одна транзакция на пару (обработчик, событие). Запись inbox — квитанция обработки; повтор доставки не исполняет обработчик заново (HST-11).

**SVC-03.** `query` — чтение согласованного снимка без квитанции (HST-10).

**SVC-04.** `migration` — чистое преобразование одной строки. Хост применяет его ко всей таблице при остановленных писателях (HST-14, HST-15).

**SVC-05.** Внешних эффектов внутри транзакции нет: сеть, файлы и процессы программе V1 недоступны (D87). Outbox фиксирует только намерения. Доставка за пределы хоста — отдельный адаптер вне V1.

## 3. Соответствие прежнему API R24

| R24 (STD-SERVICE-0.1) | V1 (STD-SERVICE-1) |
| --- | --- |
| STD-052 `std.store.snapshot(ReadCap)` | `store.get` / `store.all` в транзакции точки входа; снимок согласован HST-01 |
| STD-053 `std.store.commit(WriteCap, ActiveRef, KeyRef, S, events)` | тело `command`; KeyRef передаёт вызывающий хосту, а не программа; guard StateVersion — у запроса (HST-05) |
| STD-054 `std.store.status` | `bag status` хоста (HST-07) |
| `CommitKnowledge`: Applied / Pending / Unknown / ClosedWithoutPayload / KnownNotAdmitted | квитанция: `RESULT` / `ABSENT_AT_READ`; `UNKNOWN` — состояние клиента (OUT-03, HST-07). Ключи не истекают, поэтому вариантов закрытого адреса нет |
| STD-055 `std.events.read(EventReadCap, cursor, limit)` | параметр `handler`; курсоры и страницы — дело хоста (outbox, `seq`) |
| STD-056 `std.events.apply(ConsumerCap, …)` | тело `handler`; дедупликация по (обработчик, seq) |
| STD-057 `std.events.status` | чтение inbox хостом (HST-07) |
| `ReadCap` / `WriteCap` / `EventReadCap` / `ConsumerCap` | атомы ряда и политика хоста (EFF-11, HST-09) |
| `ActiveRef` (store, authority epoch, generation, state version, schema) | активная привязка хоста: схема, `epoch`, StateVersion (HST-04) |
| REGISTERED-SERVICE-V1, STORE-V1, EVENTS-V1, APP-IDEMPOTENCY-V1, JOURNAL-V1 | HOST-1 целиком. Отдельные контракты не нужны, `INPUT_NOT_READY` для этих функций снят |

## 4. Проверка

- Сценарии корпуса `conformance/cases/{store,events,migrate}`: квитанция, повтор, конфликт ключа, отказ guard'а, Err и FAULT, полномочия, порядок доставки, replay, миграция, точки сбоя.
- Тесты эталона `ref/tests/test_host.py` — настоящий kill -9 в каждой точке HST-16.
- Мост `conformance/bridges/authtx.py` к модели AUTH-TX-0.1 (A01–A12) — с перечнем отклонений HOST-1.
