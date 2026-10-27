# DATA-WORK-0.1 — возобновляемые операции над данными

**R07 · WORKING_DESIGN.** Общий runtime contract для [DATA jobs](../../models/r07-core/experiments/data-core/API.md); exact rules, counters, limits и transport в API. Исторический CORE не переопределяется. R07 исполняет отдельный typed job над ready values, а не source program с вложенными primitives.

## 1. Почему primitive должен иметь внутреннее состояние

Размер имени операции не ограничивает её работу. `equal`, map construction и encode/decode могут обходить данные произвольного допустимого размера. Если весь обход скрыт в одном charged step, semantic budget почти ничего о нём не сообщает и cancellation нельзя проверить между элементами.

Выбранное решение — операция возвращает управление машине после ограниченной единицы логической работы. `WorkCursor` хранит operation/profile binding, explicit control stack, позиции child/byte, private accumulators и ожидаемый тип результата. В нём нет неразрешённого имени, mutable source object или ссылки на будущую registry revision.

Это logical work accounting. Оно не измеряет CPU instructions, wall time, host allocator, GC, cache misses или фактические bytes памяти. В частности, Python list allocation/append или построение диагностического объекта могут иметь другую физическую стоимость. Resource/latency гарантия production backend потребует отдельного implementation contract. Число logical work steps не выдаётся за benchmark.

## 2. Public boundary

```text
prepare(job):
    bound and validate raw request/schema/type/value structure
    freeze exact ready operands
    bind content, registry, type and profile revisions
    return Prepared or PrelaunchDiagnostic

start(Prepared, budget, cancellation_schedule):
    validate provenance again at public trust boundary
    create private cursor; no eager comparison/encoding result

advance(machine):
    if terminal state already reached: expose that result
    if cancellation visible at current completed-step boundary: stop Cancelled
    if remaining == 0: stop BudgetExceeded
    check relevant physical guard before publishing next transition
    execute one registered work rule
    append exact trace record; decrement budget; increment completed steps
    expose resulting state without evaluating next semantic rule speculatively
```

Terminal-before-cancel-before-budget совпадает с выбранной общей границей R06, но operation entry/finish costs и trace contents задаёт собственная revision DATA. Terminal value не получает скрытого дополнительного RETURN charge. Запуск с budget0 не выполняет семантическую часть операции. Нельзя выполнить следующий generator chunk лишь для того, чтобы выяснить, есть ли ещё шаг: это может обойти budget/cancel.

Внешний caller может не вызывать advance некоторое время; это пауза процесса в пределах существующего состояния. Cancelled/BudgetExceeded — завершённые исходы этого запуска, а не разрешение незаметно добавить budget и продолжить. Durable resume, serialization cursor и transfer между workers здесь не заявлены.

## 3. Наблюдаемая запись

Observation включает точный profile/content binding, terminal category/code, typed returned value или отсутствие результата, completed steps, remaining budget, cancellation identity и ordered trace. Trace связывает каждый work rule с operation и data path/item/byte cursor по exact API.

Скрытые mutable buffers не являются returned values. При decode error, limit или cancellation нет partially decoded authoritative result; при encode stop нет успешно опубликованного prefix Bytes. Trace может сохранять историю выполненной работы, но не объявляет частичный payload валидным значением.

При physical guard отказе не публикуется transition, который guard запретил. До него сохраняется полный successful prefix. Такой исход проверяется отдельно от математического unlimited-resource oracle. Ошибка реализации не приравнивается пользовательскому malformed input.

## 4. Декомпозиция операций

### Structural compare / Eq

Explicit stack содержит paired nodes, instantiated type и current path. Посещение composite node открывает соответствующий ordered traversal; дети поступают по одному. Для String/Bytes сравниваются отдельные scalars/octets; для record — declaration fields; для суммы сначала ordinal, затем выбранный payload; для Seq — общий prefix и длина. При первом различии traversal завершается. Map допускает Eq при Eq(V), даже когда V не Key; comparator Map как key не разрешён.

Predicate eligibility проверяется до traversal по всему типу, включая отсутствующие варианты и пустые контейнеры. Короткое runtime сравнение actual values не заменяет этот допуск. Full type validation относится к bounded prepare, а не к автоматически повторяемому hidden runtime traversal.

### MapBuild

Ready operand staging следует входному порядку. Вставки выполняются детерминированно; каждый поиск позиции использует тот же structural Key comparator и сохраняет его continuation. Принята insertion-based reference strategy малого DATA-профиля; она не претендует на оптимальную asymptotic complexity.

При совпадении ключа результат содержит first/repeated source positions. Иначе ключ/value включаются в ordered result. Canonical map output одинаков для перестановок уникальных operands, однако trace и work count могут различаться. Сравнение raw serialized key bytes вместо Key comparator — дефект.

Physical movement/copying внутреннего host list не тождественно semantic visit. В exact профиле все контейнеры ограничены, а pattern work rules явно перечислены. Production persistent tree/flat-map backend должен сохранять выбранные наблюдения либо иметь отдельный допустимый refinement contract, а не просто объявлять более быстрый алгоритм эквивалентным по конечному значению.

### UTF-8 и codec

UTF8 transcode читает/пишет bounded octet work и хранит lead/continuation state. Error offset считается в bytes входа. Encode String выполняет charged scalar length prepass. Codec использует typed node stack, bounded header/length reads и private output slots; map decode дополнительно проверяет strict ascending Key order.

### Простые selectors/length/constructors

Field, sequence access и length используют validated metadata/typed children по своему API. В exact DATA length выполняет LENGTH_ITEM для каждого scalar/octet/item/entry, даже если host metadata уже хранит длину: эти charges и cancellation boundaries обязательны. Использовать metadata без сохранения логических steps можно только в новой revision или после отдельного разрешённого refinement; R07 такого shortcut не делает. Record/sequence construction учитывает перенос готовых children по правилам профиля; source initializer execution остаётся вне DATA.

## 5. Четыре разных предела

| Предел | Что ограничивает | Исход |
| --- | --- | --- |
| Prelaunch structural limits | raw request, schema/type/value depth, node count, allowed IDs/arity | явная prelaunch diagnostic/implementation limit |
| Semantic work budget | число зарегистрированных runtime rules | BudgetExceeded |
| Runtime physical guard | размер stack/private buffer/output/container | ImplementationStop |
| External production timeout/memory quota | wall time/process/platform allocation | ещё требует host/runtime contract; не моделируется как semantic result |

Budget не заменяет value limits: небольшой wire может объявить огромный container length. Value limits не заменяют budget: много сравнений коротких ключей может быть дорого. `cancel_at=k` обозначает границу после k completed rules, не wall-clock timestamp. Никакой связи с миллисекундами опыт не устанавливает.

## 6. Кеши и будущая оптимизация

Type predicates/codec layout могут кешироваться по exact registry+type+profile. Caller не подаёт произвольный bool «проверено» как доказательство. Изменение schema, primitive/work revision или input binding инвалидирует соответствующий witness.

Для оптимизации pure operations можно исследовать batching физических действий при сохранении logical work observation. До разрешения такого batching нужно определить, какие cancellation boundaries и trace events он воспроизводит, и доказать refinement. Положительное сравнение finite values не даёт этого свойства. R07 не реализует batch certificate и не заявляет ускорение.

## 7. Граница с общей машиной

[DATA-IR](../ir/data-forms.md) описывает вход после вычисления всех source operands и возврат ordinary value в общий continuation. До единого evaluator остаются exact bridge rule IDs/charges, общий budget без reset, source diagnostic/lowering, nested closure/data tests и независимый сквозной oracle. Отдельные CORE и DATA experiments дают конкретные reusable contracts, но не готовую композиционную теорему.
