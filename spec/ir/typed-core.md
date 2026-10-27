# IR-CORE-0.1 — закрытое ядро и граница полного IR

**R06 · WORKING_DESIGN.** Закрытый сериализуемый research IR в этой итерации — CORE-0.1. Его авторитетная схема, допустимые поля, types и diagnostics находятся в [API](../../models/r07-core/experiments/core-machine/API.md), а правила машины — в [core-machine.md](../runtime/core-machine.md). Этот документ задаёт место ядра в будущей полной цепочке source → CST → typed IR → execution. Полный wire format V1, source grammar и CST roundtrip ещё не закрыты.

Нельзя применять ограничение CORE как запрет функции V1. В частности, String, Bytes, nominal records/sums, пользовательские параметрические типы, коллекции, эффекты, capabilities и durable operations остаются обязательными согласно [профилю V1](../profiles/v1.md). Формы за пределами CORE получают отказ именно этого исследовательского профиля.

## 1. Три границы представления

| Представление | Назначение | Состояние R06 |
| --- | --- | --- |
| Lossless CST + source map | Человеческий текст, комментарии, точная правка и восстановление после синтаксической ошибки | Проект T03; CORE не содержит parser/formatter |
| Typed CORE artifact | Разрешённые локальные ссылки, явные type_args и сигнатуры, точный code body | Закрытая исследовательская схема, исполнимая проверка и finite oracle |
| Полный Typed V1 artifact | Все обязательные типы/формы, эффекты, imports, source mappings и канонический codec | Общий реестр форм ниже; часть схем и transitions ещё draft/open |

Успех `prepare` CORE свидетельствует о корректности входа в его области. Он не свидетельствует о parse/lower исходника, сохранении комментариев, корректном переносе EntityId или совместимости с уже существующим bagaev.

## 2. Идентичности и ссылки

- **EntityId** относится к существенной сущности проекта; rename и новая revision не меняют её идентичность.
- **BinderId** различает lexical bindings в одном typed artifact. Два source-имени `x` при shadowing получают разные BinderId. Он не является предметным PersonId/ArticleId или глобальной EntityId.
- **NodeId** адресует конкретный узел конкретного artifact. Перенос узла между ревизиями требует отдельного mapping; равенство текста не делает mapping автоматическим.
- **TypeParamId** различает rigid параметры типов. Подстановка идёт по ID, а не по написанию A/T.
- **CodeRef** в общей модели связывает immutable program content, entity/body revision и node/member. Ссылка на текущий accepted head не является CodeRef исполнения.

В CORE source_id/revision — объявленные labels входа, не криптографическое доказательство ProgramSnapshot. Поэтому execution binding включает content digest реально подготовленного input. Хеш подтверждает привязку к байтам/каноническому объекту профиля, но не авторство, authority или соответствие исходнику. Runtime-allocated closure/group slots локальны конкретному запуску и не становятся долговечными IDs.

## 3. Проверка входа до исполнения

Проверяющая граница включает следующие обязанности; они могут выполняться одним детерминированным обходом, не требуют отдельных глобальных проходов и должны оставлять известным место отказа:

```text
decode input under exact profile/version
check complete shape, known fields and literal representation
check uniqueness and lexical reachability of nodes/binders/type parameters
check type well-formedness and all branches/member bodies
check exact top-level result type and closed entry scope
freeze a private prepared representation and pin its content digest
launch one runtime instance with validated semantic limits and cancel schedule
```

CORE выполняет проверки формы, scope и типов по мере обхода, а не сначала проверяет всю shape каждого узла программы. Конкретные codes принадлежат API, порядок первой ошибки задаётся reference checker этого исследовательского профиля. Он может обнаружить ошибку типа раннего выражения до malformed формы в более поздней ветви. Полный независимо описанный diagnostic recovery protocol V1 остаётся задачей T03. Внешний JSON decoder обязан либо сохранять точные Int64 целые, либо отвергнуть значение, которое host уже округлил. Bool не принимается как Int64. Неизвестные tags/поля не игнорируются; пропущенные обязательные поля не достраиваются эвристикой. Некорректный Unicode и duplicate JSON member keys относятся к decoder boundary, которая не подменяется API уже разобранного host-объекта.

CORE эксперимент принимает структурированный host-object/его fixture encoding. Это не реализованный универсальный сеть/диск codec V1; наличие `json.dumps` не доказывает канонический формат всего языка. Prepared representation не должна зависеть от последующего изменения словаря caller. Повтор `run` создаёт независимое runtime состояние; при одинаковом artifact и schedule логические исходы совпадают в области модели.

## 4. Закрытые формы CORE

В API ровно десять expression families. Внутри `letrec` member definitions и параметры — вспомогательные records, не дополнительные исполняемые opcodes.

| Форма | Существенное правило | Статическая граница |
| --- | --- | --- |
| const | Перевод literal в value одним переходом | Bool/Int64/Unit/ArithmeticError и exact value constraints |
| var | Чтение resolved binding; специализация схемы не исполняет body | Binder виден; arity type_args; rigid/monomorphic recursion |
| let | Strict initializer один раз, затем body | Аннотированный monotype; binder не виден в initializer |
| if | Сначала condition, затем только выбранная ветвь | Bool condition, совпадающие типы обеих проверенных ветвей |
| lambda | Создать immutable lexical closure | Полная сигнатура, свободные bindings доступны |
| call | Callee, args слева направо, вход в body после args | Fn, точная арность и типы |
| letrec | Создать группу функций и lexical references, затем body | Shared type params, explicit signatures, без recursive values |
| prim | Вычислить args и применить exact primitive rule | Известное имя/арность/типы шести операций |
| result | Вычислить payload и завернуть в Ok/Err | Полный Result<T,ArithmeticError>; Err не terminal |
| match_result | Scrutinee один раз, payload только в выбранной ветви | Обязательные Ok/Err arms одинакового типа |

Ни одна неизвестная форма не снижается в host call. CORE не импортирует OBS `emit/read`, CALL static definitions или AUTH transitions автоматически: у них другая API и observation domain.

## 5. Полный V1: что покрыто и что остаётся

| Семантическая семья V1 | Исследовательское покрытие R06 | Дополнительное обязательство до freeze |
| --- | --- | --- |
| Scalar values | Bool/Int64/Unit; ArithmeticError как фиксированный builtin | String/Bytes codecs и операции; общая primitive table |
| Локальные bindings/условия | const/var/let/if | Полная source grammar и source → resolved ID mapping |
| Sequence / short-circuit | Общий lowering в nested Let/If описан | Нормативные source forms, source maps и cost attribution |
| Функции / closures | Аннотированные lambda/call и escaping closures | Полная module/export linkage, captures с capabilities |
| Generics | Shared forall на function group, явные instantiations | Source inference, generic type declarations/codecs, bound checking полного V1 |
| Рекурсия | Self/mutual recursion до budget/cancel | Все resource classes, backend/TCO simulation |
| Tagged sums / matching | Только Result<T,ArithmeticError> | Общие nominal sum table/Variant/MatchTag и source patterns |
| Records / field | Общий type/evaluation contract | Exact fields/source order/codec/diagnostic wire schemas |
| Sequences / maps | Общий строгий порядок и Key table | Constructor/results, canonical ordering, duplicate handling, full transitions |
| Host/effects/capabilities | В pure CORE запрещены | ABI, authority/revocation, dispatch/reply/settlement, replay |
| Durable state/events | Отдельный AUTH-TX-0.1 опыт | Выполнение операций через язык, реальные codecs/storage/migration/activation |
| Resource observations | Semantic step budget и deterministic cancel boundary | Value size, call depth, output limits, handles и physical implementation guarantees |

Здесь «запрещены» означает отказ CORE profile, не удаление из V1. [TYPES-0.1](../language/types.md) предлагает общий типовой алгоритм и таблицу predicates. Эти главы не дают статуса PASS всей колонке V1.

## 6. Как расширять IR без скрытой смены семантики

Для новой формы обязательна запись:

```text
FormContract = {
  profile_revision, tag, fields, recursive_children_in_source_order,
  binder_scopes, type_rule, effect_rule, value_domain,
  transitions, continuation_frames, logical_charges,
  malformed_input_diagnostics, runtime_invariant_faults,
  primitive_or_adapter_versions, observation_domain,
  dependency_extraction_rule, independent_cases
}
```

Это перечень необходимых полей контракта, не готовая JSON schema V1. Отсутствие любого наблюдаемого правила оставляет форму draft. Extension не допускает fallback с неизвестным opcode; профиль и decoder version меняются явно. Старые execution/evidence records продолжают ссылаться на свой profile revision.

У расширения бывает три разных вида влияния: добавление только metadata; добавление наблюдаемой формы; изменение semantics/cost существующей формы. Во втором и третьем случаях требуется пересмотр coverage и применимости оснований. Нельзя сохранить старое имя профиля и незаметно поменять число переходов.

## 7. Lowering и source order

Typed IR хранит order выражений независимо от канонического порядка хранения полей. Для Record/Map сначала оцениваются source-order initializers; сортировать их до исполнения нельзя. Кодирование ключей JSON и сортировка nominal declarations не должны переставлять вычисления.

Любой source sugar получает отдельную запись: входная форма, lowered graph, generated BinderId/NodeId, source-map mapping, ошибки и наблюдаемая стоимость. Например, `a and b` может lowering в If(a,b,false) при определённом Bool type, но строгий `and(a,b)` вызывает b всегда. Для Result propagation требуется Match с явной ветвью возврата и контролем окружающего Result-типа; Err сам по себе не является командой unwind.

R06 не заявляет готовый source lowering и не меняет старые R03 law traces. Для дальнейшего compiler contract каждый lowering должен иметь либо reference lowering как часть semantics, либо проверяемое соответствие уже выбранной машине. Два произвольных дерева с одинаковым неограниченным результатом не объявляются автоматически эквивалентными по ресурсам.

## 8. Приёмка этого слоя

Проверка CORE: shape/typing negative cases; lexical capture после выхода из области; self/mutual recursion; generic specializations; checked arithmetic; строгие аргументы; неизвестные формы; mutation исходного input после prepare; budget/cancel при одинаковой границе; независимые ожидаемые traces.

Приёмка полного T03 дополнительно требует grammar/CST, bytes-preserving edits, roundtrip, stable EntityId operations, canonical codec и соответствие исходному репозиторию. Эти обязательства остаются открытыми. R06 не переименовывает ограниченный kernel в готовый язык.
