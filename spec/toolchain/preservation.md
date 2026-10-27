# PRESERVE-0.1 · сохранение наблюдаемого исполнения

**R22 · WORKING_DESIGN.** Проект всего T13-C03 для выбранного V1: область преобразований, граница доверия, конкретные правила, композиция и маршрут проверки. Нормативная приёмка не выполнена. Полная грамматика, общий evaluator всех форм, ABI и production checker остаются точными входными зависимостями соответствующих задач.

Этот контракт продолжает [R21 pipeline](pipeline.md), [SEM](../language/semantic-core.md), [CORE](../runtime/core-machine.md), [DATA-WORK](../runtime/data-work.md). Старые R03/R04 сохраняют свою ограниченную observation domain. Они не доказывают новые свойства задним числом.

## 1. Предмет и результат

Оптимизатор получает полностью проверенное typed/effect IR точного SourceBundle, MeaningLock, DependencyLock и SemanticEnvironment. До оптимизации должны быть проверены все ветви и тела, включая неисполняемые. Оптимизатор не исправляет исходную программу, не меняет accepted head и не запускает host code.

Результат — CandidateProgram и PreservationCertificate, либо диагностированный отказ. Кандидат допускается к emit только после независимой от предложенных аннотаций проверки. Успешный форматный validator проверяет форму записей; он не заменяет этот семантический checker.

Точка включения — новый контракт P5-OPT-0.1: сначала проверенное reference lowering, затем сохранение его поведения оптимизированным lowered IR. SourceSubject сохраняет authored snapshot; origin_ir — этот exact reference lowered seed; input_ir — текущий вход преобразования; candidate_ir — его выход. На первой попытке input_ir=origin_ir. Эти четыре понятия не объединяются в одно поле source. Точный мост к P5/P6/P7, новым target forms и картам всех code-bearing outputs описан в [pipeline-bridge.md](pipeline-bridge.md).

Режимы:

| Режим | Поведение |
| --- | --- |
| REFERENCE | Точное эталонное преобразование R21; все обязательные контракты всё равно проверяются |
| SAFE_OPT | Проверенные локальные преобразования; неприменимое правило оставляет прежний фрагмент |
| REQUIRE_OPT | Как SAFE_OPT, но отсутствие хотя бы одного действительного преобразования даёт NO_APPLICABLE_RULE |

Invalid supplied certificate возвращает INVALID_CERTIFICATE; автоматическая замена отказа успешным исходным артефактом запрещена. Caller может создать отдельную явно записанную попытку REFERENCE. UNKNOWN/UNSUPPORTED/предел проверки не означают equivalence.

## 2. Наблюдение

Для source P, inputs I, начальных логических лимитов B и зарегистрированной стратегии окружения E определим историю H(P,I,B,E). Она состоит из состояния до первого шага, каждого опубликованного логического перехода и терминального состояния.

Обязательная проекция:

    O(M) = (
      source_subject, semantic_profile_and_environment,
      logical_position, reference_control_location,
      visible_typed_values, continuation_and_capture_relation,
      semantic_state, budgets, cancellation_record,
      ordered_effect_prefix, settlement_knowledge_at_boundary,
      termination, diagnostic_origin
    )

Source subject — точные исходные bytes/IR и semantic bindings. Target artifact и compiler implementation имеют собственные identity в receipt, но не должны быть ошибочно сравнены как одинаковые source bytes. Общая source identity обеих сторон проверяется через сертификат; target identity сохраняется отдельно.

Значения сравниваются по exact type/value contract: номинальные IDs сохраняются; String не нормализуется; Bool не становится Int64; Result.Err — значение. Closure сравнивается не по host address, а по точному code correspondence, lexical captures и type specialization. Capability/HostHandle сравниваются только по разрешённому непрозрачному отношению их lifecycle contract, без сериализации или создания новых полномочий. Если такого отношения нет, соответствующий target не допускается.

Условия совпадения наблюдений не разрешают удалять ошибку, dispatch, квитанцию или charge. В V1 нет общего разрешения превращать определённую ошибку в произвольное поведение по аналогии с undefined behavior другого языка.

## 3. Сильное отношение исполнения

Production claim EXACT_BOUNDARIES требует при одинаковых P/I/B/E:

1. Совпадения O до первого семантического перехода.
2. Для каждого опубликованного source перехода — ровно одного соответствующего target logical event с тем же source RuleId, NodeId, dynamic occurrence, cursor и списаниями.
3. Совпадения O после этого перехода, включая остановленный prefix.
4. Одновременной терминальности и одинаковой категории/value/code/origin.
5. Отсутствия дополнительных наблюдаемых переходов target.

Допускаются физические microsteps без публикации. Каждый такой участок конечен по опубликованной мере и не производит host effect, логическую запись, consumption of input, изменение capability или authoritative state. Бесконечное target stuttering запрещено.

Это параметрическое обязательство для всех входов выбранного полного профиля, допустимых окружений и бюджетов, а не утверждение, установленное finite report. Конкретные локальные правила ниже сводят проверку замены к закрытому structural replay и зарегистрированным переходам. General equivalence произвольных программ не решается.

Если профиль имеет только конечные budgets, можно доказывать соответствие каждого конечного prefix индукцией по числу опубликованных переходов. Для бесконечного разрешённого запуска необходима отдельная productivity/fairness часть: конечность каждого target участка и отсутствие новой внутренней дивергенции. Наличие bounded test не устанавливает её.

## 4. Время и окружение

Cancel schedule здесь задаётся видимостью события на точной логической границе, а не миллисекундами. E — функция разрешённой истории запросов и логического положения, возвращающая очередное событие/ответ/отсутствие ответа. Она может зависеть от предыдущих наблюдений; одного одинакового списка ответов недостаточно, если порядок запросов изменился.

Для replay закрепляются одинаковый журнал, observation contract и policy выдачи событий. Пустая запись не разрешает обратиться к реальному host. Для live execution statement условен относительно одинаковых наблюдаемых входов: физически ускоренная программа может встретить внешнее событие в другое wall-clock время. R22 не обещает одинаковый живой сетевой мир или одинаковую latency.

Current authority проверяется при каждом реальном dispatch. Ни сертификат, ни старый receipt, ни вычисленный заранее аргумент не заменяют текущую capability. Отзыв может быть входным событием E; при одинаковой логической истории обе стороны доходят до одинаковой проверки.

## 5. Канонический порядок границы

    advance(target):
      if terminal or projected reference state is terminal:
        return existing terminal result
      materialize/validate current logical checkpoint
      if registered cancellation is visible now:
        fix Cancelled; keep effect and settlement prefix
      if next required semantic budget cannot cover transition:
        fix BudgetExceeded with same origin and prefix
      validate current authority if this is dispatch
      check applicable implementation guard before publication
      execute or select the checked replacement for exactly one rule
      atomically publish successor + exact logical event + counters

Terminal test не требует исполнения следующего source rule. Нельзя вызвать generator следующего chunk «для проверки, закончился ли он», если тот выполняет работу до budget/cancel.

Полный precedence нескольких semantic resource classes определяется exact ResourcePolicy. R22 сохраняет его; собственный порядок по имени класса запрещён. Доступные CORE/DATA различают terminal → cancel → step budget. Их общая композиция не получает reset при входе в data job или функцию.

Внешнее действие имеет свои intent/dispatch/reply/settlement границы. Нельзя объединять их в один удобный checkpoint. Поздний settlement может дополнять историю знания, но зафиксированный termination не переписывается. Cancelled не означает rollback уже отправленного действия.

## 6. Логическое состояние при физической оптимизации

Target имеет (physical_state, LogicalCursor, ReconstructionMap). Последние два объекта определяют, какое source состояние соответствует текущей опубликованной границе.

ReconstructionMap — замкнутый типизированный DAG:

| Узел | Разрешённый смысл |
| --- | --- |
| KEPT_SLOT | Прочитать уже существующий immutable typed slot с exact lifetime |
| PINNED_SCALAR | Взять проверенный scalar/Result из immutable literal pool |
| RECORD_VIEW | Собрать view из уже доступных children по exact nominal declaration |
| FRAME_VIEW | Восстановить control/caller/type environment из существующих значений и source frame recipe |

Запрещены host calls, новые вычисления source expressions, чтение mutable accepted head, скрытые capabilities, выполнение пропущенного dispatch. Для функций/recursion slots используется зарегистрированная opaque slot correspondence с общим run lifetime, без сериализации.

Каждый узел DAG типизируется; все ссылки существуют; graph acyclic; bounds проверяются до использования. Materialization повторяема, не списывает semantic work и не создаёт effect. Её physical work имеет собственный implementation limit. Отказ реконструкции — ImplementationStop, не Cancelled и не successful equality.

Baseline implementation сохраняет все исходные slots/frames и использует identity reconstruction; оптимизации этой редакции меняют вычисление scalar result/ветви, не удаляют live bindings. Это конкретный реализуемый вариант. Lazy frame compression и уничтожение slots не разрешаются этим профилем.

## 7. Предвычисление и публикация

Предвычисленный результат хранится privately. Он становится текущим source value только на прежнем source переходе. Для closed expression можно сохранить последовательность source checkpoint recipes и заменить физическое вычисление готовыми значениями; каждый переход всё равно проходит advance.

Например, CORE i64.add(2,3) выполняет PRIM_ENTER, CONST, PRIM_NEXT, CONST, PRIM_APPLY. Optimization может не складывать числа во время runtime, но все пять логических событий и их промежуточные состояния сохраняются. На PRIM_APPLY появляется Ok(5), а не bare Int64.

При overflow предвычисляется Err(Overflow). Он появляется на прежнем PRIM_APPLY и продолжает вычисление как обычное значение. Если программа затем явно обрабатывает Err, её Match и последующие strict operands остаются. Compile-time discovery не превращает определённый runtime outcome в prelaunch error.

Physical precompute не пересекает host/capability/durable boundaries. Динамическое вычисление будущего source suffix перед cancel/budget этой редакцией не допускается. Closed constants вычисляются во время компиляции под отдельным compile budget; это не выполнение программы с текущими правами.

## 8. Область всех V1 форм

Политика охватывает все обязательные семейства, а не только конечный опыт:

| Семейство | Политика R22 |
| --- | --- |
| Scalars, local bindings, conditions | Closed scalar/Result replay, lexical scalar reuse и known-arm specialization по каталогу |
| Calls, closures, generics, recursive groups | Сохранять callee/strict args/capture/type env и reference frame boundaries; оптимизировать допустимые локальные children |
| Records, sums, Option/Result, Match | Сохранять source initializer order и nominal identity; локальные правила только при полном exact form contract |
| Sequences/maps/String/Bytes and data jobs | Сохранять reference work cursor, comparison/codec costs и shared budget; динамическое batching не допущено |
| Host, handles, capabilities | Неподвижные границы; exact adapter, текущие authority checks и сохранение lifecycle |
| Durable state/events/recovery | Exact operation keys, request identity, dispatch/settlement и external protocol; без слияния или повторного исполнения |
| Imports/linking/target boundaries | Exact R21 closure/ABI/target; источник смысла и target checker не выбираются по одной подписи |

Для любого узнаваемого opcode решение определяется data/form-coverage.json и полным FormContract. DEFAULT_KEEP допустим лишь при exact исходном IR и известном reference execution/lowering; он не реализует неизвестную форму. Missing mandatory form/evaluator/charge/ABI contract → INPUT_NOT_READY. Unknown opcode/profile → UNSUPPORTED. Эти отказы являются открытой зависимостью реализации, не исключением возможности из языка.

Наличие reference fallback не закрывает T13-C03 само по себе. Здесь дополнительно определены действительные локальные оптимизации, проверка их замены, состояние на всех границах и композиция с оставшимися формами.

## 9. Физические ресурсы и полезность

Semantic steps не равны CPU instructions. Сохранение logical checkpoints может оставить почти ту же стоимость управления, даже если arithmetic work уменьшилось. Ускорение требует benchmark с учётом checker, compile-time evaluation, памяти checkpoint recipes и runtime reconstruction.

ImplementationStop не является семантическим успехом и не используется как способ объявить любые две программы эквивалентными. Production claim содержит TargetCapacityContract: границы размера кода/slots/stack/trace и область входов, на которой target обязан реализовать semantic execution. Ухудшение этой области — изменение target claim, а не тихая оптимизация. Вне неё возвращается отдельная диагностика без equivalence result.

Floating point, arbitrary host UB, JIT speculation, profile-guided input narrowing, TCO/inlining, effect reordering, removal of logical work, live patching и dynamic data batching требуют новых явно проверяемых правил. Они не включены в исходный каталог оптимизаций.

## 10. Композиция, деоптимизация и остановка

Для checked A→B и B→C сравнить C1.candidate_ir=C2.input_ir, одинаковые SourceSubject и origin_ir, observation/resource/environment policy. C2 не называет B новым authored source. Скомпозировать node/occurrence/slot maps; проверить полноту и отсутствие изменения origin. Каждое отношение сохраняет одну и ту же logical schedule, поэтому границы соединяются по одной и той же позиции. Результат не обобщает входные области; берётся их проверяемое пересечение.

Deoptimization допустима только на опубликованной границе с готовым ReconstructionMap. Создаётся source state той же позиции, с прежними budgets, journal offset, operation keys, capture group slots, cancellation knowledge и termination. Никакой повторной инициализации runtime instance и добавления бюджета. Уже dispatched effect не исполняется снова.

В initial implementation deopt означает переключение с scalar replacement на reference continuation при identity reconstruction. Dynamic guard assumptions и transfer между процессами отсутствуют. При невалидной реконструкции выполнение останавливается как ImplementationStop; fallback путём повторного запуска программы запрещён.

## 11. Обязательства корректности

Для каждого admitted rule должны быть обоснованы: совпадение initial state, exact step relation, typed reconstruction, equality каждого event/cost, terminal reflection, bounded physical progress и отсутствие новых effects. Для замены внутри контекста дополнительно нужны strict child order, lexical hygiene, сохранение untouched subgraphs и frames.

Основание production admission — версия rule semantics и checker с отдельно проверенным soundness obligation. Проверка конкретного certificate подтверждает соблюдение этого правила на этих bytes, но не доказывает корректность реализации checker. Независимый finite oracle и semantic mutations ищут ошибки; доказательство всех случаев остаётся отдельным результатом.

Подробные алгоритмы: [optimization-rules.md](optimization-rules.md), [preservation-checking.md](preservation-checking.md). Реальная приёмка и implementation order: [preservation-route.md](preservation-route.md). Все production cases этой итерации имеют NOT_RUN.
