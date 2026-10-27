# DATA-IR-0.1 — формы данных и соединение с CORE

**R07 · WORKING_DESIGN, integration NOT_RUN.** Документ задаёт общий проект расширения IR. [CORE R06](typed-core.md) остаётся замороженным ограниченным профилем; [DATA R07](../../models/r07-core/experiments/data-core/API.md) исполняет jobs над готовыми operands. Совместное исполнение всех форм одним source frontend/runtime пока не проверено. Наличие правил ниже не означает полной registry V1: Host, ресурсы, полный source pipeline и часть stdlib ещё открыты.

## 1. Общие поля и type references

Каждая expression form имеет уникальный `NodeId` и известный monotype после проверки. Дополнительные source spans связываются с CST revision; они не являются идентичностью узла. Все nominal references и primitive revisions разрешены относительно одного ProgramSnapshot. Type metas, unresolved aliases и implicit default types в accepted IR отсутствуют.

Schema registry — часть snapshot. TypeRef содержит nominal entity/revision и полностью определённые ordered type arguments; structural types имеют закрытые конструкторы. Переменные, функции и continuations сохраняют ранее определённые lexical правила CORE/TYPES. Fn values разрешены как несохраняемые payload там, где это допускает тип; DATA harness не исполняет такие значения.

## 2. Registry форм

| Форма / существенные поля | Тип | Порядок исполнения | Возможный отказ |
| --- | --- | --- | --- |
| ScalarConst(type,value) | точный primitive type | одно чтение validated constant; source literal decode до launch | prelaunch invalid scalar/Int64/Bytes |
| Record(type, ordered field initializers) | nominal Record<T…> | initializer order исходника; затем сборка declaration layout | prelaunch missing/unknown/duplicate field, wrong type |
| Field(receiver,field_id) | substituted field type | receiver; затем projection | prelaunch unknown field/type |
| Variant(type,tag,payload) | exact instantiated closed sum | payload; затем wrapper | prelaunch unknown tag/wrong payload |
| Match(scrutinee,arms) | общий branch result | scrutinee; одна выбранная branch | prelaunch exact coverage/type diagnostics |
| Sequence(element_type,items) | Seq<T> | все items слева направо | prelaunch type; runtime resource bound |
| MapBuild(key_type,value_type,entries) | Result<Map<K,V>,DataError> | все key/value operands слева направо; затем DATA MapBuild job | prelaunch Key/type; ordinary duplicate Err |
| DataPrim(revision,op,type_args,args) | exact registered signature | callee metadata не исполняется; все args слева направо; затем work cursor | prelaunch signature/predicate; ordinary Result или runtime stop |
| Let / If / Lambda / Call / RecursiveGroup | по TYPES/CORE | сохраняют ранее заданные lexical/strict правила | по общей классификации |

ScalarConst для composite value может появляться после lowering только с проверенным exact typed value и правилами его materialization. Нельзя спрятать произвольную работу decoder/normalizer в zero-cost literal loading. Разделить compile-time artifact loading и runtime construction по versioned resource contract; большой embedded literal подчиняется prelaunch size/work guards.

## 3. Проверка constructor с ожидаемым типом

```text
check_constructor(C, expected, Gamma, Delta, Registry):
    resolve exact constructor ref and explicit type arguments if provided
    if explicit arguments missing:
        create fresh metas only for this use, with allowed rigid scope
    if expected exists:
        unify result_type(C) with expected BEFORE children
        # MapBuild result is Result<Map<K,V>,DataError>, not bare Map<K,V>
    validate field/tag set or container arity without executing children
    for child in source evaluation order:
        child_expected := apply current substitution to declared child type
        check(child, child_expected); accumulate substitution, effects, pending bounds
    return constructed type and pending constraints
    # finalization belongs to initializer/function body/entry, not each child
```

Для MapBuild `DuplicateKey` — значение error code внутри fixed DataError, а не отдельный тип результата bridge. Expected type унифицируется с полным Result<Map<K,V>,DataError>, после чего ограничения K/V передаются children.

Типы children проверяются даже для невыполняемых ветвей. Если первый аргумент generic constructor — Lambda без annotation, поздний соседний аргумент сам по себе не даёт двунаправленному checker права переиграть уже отвергнутую Lambda: доступный expected Fn должен существовать в точке её проверки. Поздние уравнения могут уточнять уже созданные metas, но не заменяют отсутствующий алгоритм. Возможность более сильного inference потребует отдельной версии.

### Минимальные ожидаемые derivations

| Исходная ситуация | Ожидаемое решение |
| --- | --- |
| `let xs: Seq<Int64> = []` | expected element type Int64, accepted |
| `let xs = []` без annotation/context | AmbiguousTypeArgument |
| Пустой MapBuild с expected `Result<Map<PersonId,Int64>,DataError>` | K=PersonId, V=Int64; проверить Key(PersonId), затем accepted |
| `let x: Option<Int64> = None` | expected sum supplies absent payload type |
| `let x = None` без иного контекста | AmbiguousTypeArgument |
| `Box<A>{ value = 7 }` с omitted A | constraints determine Int64; finalize once initializer complete |
| `Phantom<A>{}` без expected/explicit A | AmbiguousTypeArgument, несмотря на пустую раскладку |
| Record field с PersonId, передан ArticleId той же физической формы | TypeMismatch |
| `Seq<Fn>` пустой, затем `encode` | тип Seq допустим; encode требует Persistable и отвергается |
| `Map<Bytes,Int64>` со String key | TypeMismatch; no implicit UTF8 encode |
| Expected `Fn([Int64],Int64)` у field constructor, Lambda parameter не аннотирован | проверка использует known expected parameter type |

Это вручную определённые derivations проекта source checker. Если отдельный executable checker их не выполнял, статус остаётся NOT_RUN; проверки ground DATA types не переименовываются в source inference coverage.

## 4. Frame протокол интеграции

General machine добавляет следующие классы continuations; точный wire opcode registry общего V1 ещё требуется интеграционной редакции.

- `CollectRecord`: remaining source initializers, declaration destination slots, frozen lexical environment, caller continuation.
- `CollectSequence`: next element expression, collected immutable values.
- `CollectMapOperands`: pair index, key/value phase, completed operands; duplicate checking ещё не начиналось.
- `WrapVariant`: exact sum instance и tag.
- `ChooseMatch`: checked tag→branch table и payload binding.
- `ResumeData`: exact operation/profile, validated typed operands, DATA cursor и destination continuation.

Каждый переход сохраняет invariant: slots содержат values своих monotypes; completed operands не переоцениваются; capture environment относится к snapshot; дальнейшие выражения доступны только через явно сохранённый frame. Вход в DATA не ищет primitive по новому accepted head.

При `DataPrim` общий evaluator сначала получает все operands. Затем отдельно оплачивает entry/control rule и переносит управление DATA cursor. DATA_DONE возвращает обычное typed value в continuation; `Err` не автоматически покидает caller. Budget/cancel проверяются на каждой общей границе, включая внутренние DATA work rules. Переходы entry/return должны иметь назначенные distinct rule IDs и charges в интеграционной версии; R07 не придумывает их задним числом к CORE traces.

Данные одного job не получают отдельный бесконечный вложенный budget. При интеграции счётчик общих semantic transitions един, либо явно специфицированы несколько независимых resource counters. Reset бюджета при входе в primitive запрещён. Самостоятельный harness имеет один budget на job; это не проверка общего nested counter.

## 5. Приоритет ошибок и observable order

Prelaunch: malformed IR → resolve/type/predicate diagnostics по опубликованному порядку frontend; никакие effects ещё не начинаются. Точный порядок нескольких одновременных frontend ошибок не выводится из порядка runtime.

Runtime: строгое вычисление source operands до DATA-проверки дубликатов/codec. Если ранний operand вернул обычный Err как значение, следующий operand всё равно вычисляется, если явный Match не меняет control flow. Если operand остановлен по budget/cancel, DATA job не запускается. После успешного сбора operand values job применяет свою terminal→cancel→budget→work boundary.

Невзятая branch Match/If не исполняется, хотя type checker её проверил. Duplicate Map и malformed wire/UTF8 returns — программные values с отдельными error types. Нарушение internal typed invariant — ImplementationStop; оно не маскируется обычным Result.

Случай для будущей обязательной интеграционной проверки:

```text
MapBuild([(same_key, first_value),
          (same_key, second_value),
          (other_key, divergent_or_effectful_expression)])
```

Здесь нельзя вернуть DuplicateKey до вычисления третьей пары. R07 map_build использует ready operands, поэтому такой trace в его report отсутствует. Это явно сохранённое требование до объявления общего V1 evaluator готовым.

## 6. Компиляция и identity

Lowering сохраняет source evaluation order в ordered initializer list. Declaration order используется только для готового layout. Для record/hash-consing backend может переиспользовать immutable nodes, но pointer equality не подменяет Eq при отсутствии доказанного same-instance shortcut. Such shortcut не должен менять выбранный cost/trace contract.

Ground type/codec witnesses можно кешировать по exact registry binding + type + profile. Witness не даёт capability и не переживает произвольную schema revision. Trusted prepared object не принимает caller-supplied cached predicates без проверки происхождения: public API заново связывает input bytes с exact content digest.

В будущий graph provider идут прямые facts: nominal identity use, field projection, tag coverage, structural predicate use, codec layout use, comparator revision и work-profile revision. Reverse index выводится из них. Identity-use нельзя убрать лишь потому, что функция не читает изменённое поле: изменение nominal revision уже изменило её типовую предпосылку. Для value-only state change сохраняется отдельный более точный field-use анализ.

## 7. Условия завершения интеграции

До claim общего pure V1 evaluator нужны: единый closed IR registry; source→IR expected-type derivations; exact переходы bridge и одна модель budget/cancel; cross-language values/codecs; непрерывные traces с closures/generics/data; constructor-order cases с поздним error/divergence; общий oracle и критерии refinement для backend. По отдельным успешным CORE и DATA отчётам эти свойства не следуют автоматически.

### 7.1. Явное согласование двух исследовательских представлений

R08 не может просто объединить JSON формы старых исполнителей. Перед переносом нужен новый versioned internal type/value registry и документированный embedding каждого прежнего профиля:

| Граница | Обязательный проект отображения | Проверяемое условие |
| --- | --- | --- |
| CORE `Result(ok=T)` | В новом internal registry это `Result<T,ArithmeticError>`; DATA `Result(ok=T,err=E)` сохраняет E | ArithmeticError и DataError различны; старый shorthand не получает новый смысл задним числом |
| Scalar/nominal/composite values | Одна typed immutable Value модель с exact snapshot type refs | Прежние Bool/Int64/Unit сохраняют значения; новые nominal IDs не стираются в host dict/string |
| Closure внутри Seq/Record/sum | Closure сохраняет code revision, lexical capture и specialization как internal value | Передача через контейнер и последующий Call воспроизводят lexical поведение; JSON descriptor не заменяет capture |
| Public DATA operand | Только явный перенос допустимого ground data через `value_json` и повторную проверку | Внутренний Fn/authority value не отправляется в JSON API, где его представления нет |
| Eq/Key/Persistable | Проверка общего instantiated type до запуска операции, с теми же whole-type правилами | Пустой функциональный контейнер не получает predicate по своему фактическому пустому payload |
| Match | Полное покрытие exact tags и typed payload bindings в новой registry | Ветви arithmetic/data errors не смешиваются; исполняется только выбранная branch |

Internal constructor/selector для функциональных payload не обязан вызывать публичный DATA job: этот API сознательно не умеет передавать функции. Интеграционная машина должна либо реализовать такую внутреннюю операцию на общей Value модели, либо явно оставить форму непокрытой. Не допускается стирать capture, заменять функцию code descriptor или выдавать отдельный job report за проверку этого пути.

Для reuse старых опытов сначала задать translation старого typed program/job в новый registry, затем сравнивать выбранную observation projection. Новые entry/return charges означают, что полный integrated trace не обязан побайтно совпадать со старым standalone trace. Нужны явное соответствие внутренних DATA work units, новые bridge units и независимое вычисление общей стоимости. Такое сопоставление является будущим contract/refinement gate, не уже полученным R07 результатом.
