# OPT-RULES-0.1 · конкретный каталог преобразований

Статус: проект R22. Общая область и отношение — [PRESERVE](preservation.md). Каталог определяет конечную, реально реализуемую политику оптимизатора полного V1: обходит все известные формы, выполняет только перечисленные замены и сохраняет остальные формы по exact reference contract. Он не разрешает произвольную «семантически похожую» правку.

## 1. Общие предпосылки

Программа полностью resolved/type/effect checked до первого правила. IR, primitive, ResourcePolicy, observation, lowering и target revisions закреплены. Входной registry содержит полный список обязательных forms и children/scopes. Unknown child order, scope, charge или result encoding блокирует соответствующий переход, а не заполняется эвристикой.

Actual V1 operands сохраняют source order. Все strict initializers/arguments исполняются прежнее число раз. Canonical storage order не является evaluation order. Ни одна оптимизация не меняет nominal identities, ResourceRef, OperationKey, current authority, Result propagation или semantic costs.

RuleId/version относятся к точному matcher, replacement constructor и checker. Candidate не может поставлять произвольный executable checker. Пользовательский plugin только предлагает данные, которые проверяются известным ядром.

## 2. R22-CLOSED-SCALAR-REPLAY

### 2.1. Область

Closed finite subtree из CONST, VAR, LET, IF, PRIM, RESULT, MATCH_RESULT. Все free value/type variables должны отсутствовать; primitive registry и scalar/Result types точны. Разрешены Bool, Int64, Unit, ArithmeticError и Result<Int64,ArithmeticError>; вложенные/nominal types требуют собственной записи rule revision.

Разрешённая первоначальная primitive table повторяет семантику CORE: i64.eq, i64.lt, i64.add, i64.sub, i64.div, i64.rem. Это allowlist exact contracts, не поиск по одинаковой строке имени. Add/sub дают Ok либо Err Overflow; div при нуле даёт DivisionByZero, MIN/-1 даёт Overflow; rem при нуле DivisionByZero, MIN rem -1 даёт Ok(0), иначе остаток относительно quotient к нулю.

Нет call/lambda/letrec/host/handle/durable/data-job. Значит evaluator не вызывает пользовательские функции или внешние adapters. All-branch typecheck выполнен заранее, хотя runtime выберет одну ветвь.

### 2.2. Построение

1. Выделить точное subtree и проверить замкнутость, типы, allowlist.
2. Создать локальный reference cursor с символическими BASE_ENV, BASE_K и DYNAMIC_OCCURRENCE_PREFIX. Они обозначают неизменные контекстные параметры точки входа.
3. Выполнить зарегистрированные source transitions для этого замкнутого выражения в bounded compile evaluator. Не применять runtime cancellation; вычисление строит потенциальную локальную историю, которую runtime будет открывать по шагу.
4. Для каждого перехода записать source rule/node, локальную control/frame/env delta, exact cost vector, resulting typed scalar/Result slots и location рецепта ошибки. Source terminal данного subtree означает ready value к BASE_K, а не обязательно конец всей программы.
5. Проверить, что после конечного числа переходов получено ready value, не превышены лимиты, все значения имеют объявленные types.
6. Построить REPLAY_REGION с таблицей immutable values/checkpoints и точной original region ref.

Precompute не считает Result.Err terminal. Он обрабатывает последующий Match/Let ровно по source semantics. Если достигнут локальный предел этого region, правило неприменимо с причиной LOCAL_RULE_LIMIT; исходный фрагмент сохраняется, потраченная работа остаётся в общих counters. Исчерпание общего compile/check budget останавливает всю попытку с CHECK_LIMIT. Ограничение инструмента не превращается в compile-time diagnostic о некорректной пользовательской программе.

### 2.3. Проверка

Checker не принимает supplied trace как основание. Он заново определяет тот же разрешённый subtree из current checked source, запускает свою зарегистрированную локальную evaluation procedure и сравнивает весь replacement: values, states, frames, terminal continuation, event origins и costs. Проверка только final value или списка RuleId недостаточна.

В production trust base входит soundness этого evaluator относительно bound FormContracts. Две одинаковые реализации producer/checker не образуют независимое доказательство. Именно поэтому отдельно нужны независимый runtime oracle и локальные preservation lemmas.

### 2.4. Runtime

При входе создаётся local cursor index0 и фиксируются BASE_ENV/BASE_K/occurrence текущего вызова. На каждом advance:

    observe terminal/cancel/budget at the current source boundary
    instantiate next checked local checkpoint using retained context
    publish exactly one source transition and its successor

Нельзя публиковать final value перед последним local transition; нельзя объявлять program terminal, когда готов только subtree. После конца local schedule вернуть ready value в прежний continuation, без дополнительного RETURN charge. При повторном вызове функции создаётся новое dynamic occurrence; сохранённые recipes не переиспользуют старую runtime identity.

Сокращается физическое вычисление арифметики и выбор локальных ветвей. Логические события остаются. Размер tables и стоимость их чтения могут перекрыть экономию; speed не заявлен.

## 3. R22-LEXICAL-SCALAR

### 3.1. Область и факт

Только resolved Var точного BinderId с monomorphic scalar/Result type из предыдущего allowlist. Binding вводится strict Let initializer, для которого checker установил closed scalar value по R22-CLOSED-SCALAR-REPLAY или прямому exact literal.

Fact имеет (artifact, declaring Let NodeId, BinderId, monotype, initializer_ref, computed_value, lexical_scope_path). Не является фактом совпадение имени, значение одного прежнего запуска, аргумент функции или runtime input.

### 3.2. Алгоритм lexical facts

Обходить typed tree по FormContract.child_order с явным stack scope. В initializer Let новый BinderId ещё не виден. После сохранённого выполнения initializer расширить факты только для body. При выходе из body вернуть прежнюю таблицу. Для lambda/recursive body начать новый уровень: параметры и captures считаются UNKNOWN; заново выводятся только локальные closed Let facts. Подстановка в closure capture по этому правилу не выполняется.

Для If/Match body факты наследуются по своей lexical scope, без слияния разных binders в один. CFG variants обязаны применять declared dominance+all-predecessor agreement; базовый tree checker этого профиля не выводит такие facts из произвольного CFG.

### 3.3. Замена и обязательство

Физическое чтение Var может стать загрузкой закреплённого значения; logical VAR сохраняет тот же BinderId/NodeId и стоимость. Let initializer/LET_BIND остаются. Source env slot сохраняется и реконструируется, поэтому debugger/остановленный prefix не теряют binding.

Checker находит объявляющий Let в текущем IR, подтверждает scope и exact initializer derivation, сам вычисляет разрешённое значение. Любое изменение defining value, type, capture/scope или artifact инвалидирует fact. Служебная таблица supplied known_values не является доверенной.

## 4. R22-KNOWN-ARM

Применяется к IF с exact Bool condition либо MATCH_RESULT с известным Result tag/payload, полученным из literal или действительного lexical fact. Full original condition/scrutinee evaluation сохраняется; её strict effects и logical transitions не удаляются. Если знание требует speculative effect/input read, правило неприменимо.

Замена сохраняет entry и selection rule (IF_ENTER/IF_THEN/IF_ELSE либо MATCH_ENTER/MATCH_OK/MATCH_ERR) с точными origins, frames и costs. Меняется физический выбор continuation: он заранее указывает на проверенную выбранную ветвь. Payload binder Match получает тот же typed payload.

Неисполняемая ветвь уже статически проверена и остаётся доступной как exact source/type/origin metadata. Удаление её source diagnostics или изменение authored source не входит в правило. Можно не включать физический код этой ветви в specialized internal representation только если нет иных входящих code references, target checker подтверждает closure, а source provenance сохраняет её существование.

Для повторного исполнения с новым input нельзя использовать предположение об условии из прошлого запуска. Value fact обязан быть статическим относительно immutable program, а не observed input sample.

## 5. KEEP-REFERENCE и общий проход

KEEP-REFERENCE не считается оптимизацией. Он сохраняет форму, order, scope, type/effect semantics и исходные registered transitions. Его target encoding проверяется R21 translation/loading contract.

    optimize(checked_IR, policy):
      verify complete known FormRegistry and all bound dependencies
      current = exact original
      traverse original semantic children bottom-up in stable source order
      at each source region:
        attempt CLOSED_SCALAR_REPLAY, then LEXICAL_SCALAR, then KNOWN_ARM
        if result is VERIFIED_REPLACEMENT:
          append exact rule step and replace this region
        if result is NOT_APPLICABLE or LOCAL_RULE_LIMIT:
          keep the current reference representation and record reason
        if result is INPUT_NOT_READY or UNSUPPORTED_REQUIRED_CONTRACT:
          terminate the whole attempt with the corresponding diagnostic
        if result is CHECK_LIMIT or TOOL_LIMIT or CANCELLED:
          terminate the whole attempt; retain counters and frontier
        if generated candidate violates an invariant:
          terminate INTERNAL_ERROR; do not silently KEEP
        if externally supplied certificate is invalid:
          terminate INVALID_CERTIFICATE; do not silently KEEP
      check chain and final candidate independently
      return candidate and certificate; report actual rule applications

Candidate internal nodes REPLAY_REGION/SCALAR_SLOT/KNOWN_ARM являются частью отдельного target form registry. Они сохраняют original semantic region. Второй проход не трактует их как обычные source const/if и не списывает costs повторно. Каждый rewrite step адресует текущий artifact; копия source origin не считается текущим адресом.

LOCAL_RULE_LIMIT — только опубликованный предел одного предпринятого local rewrite, например 4 096 checkpoints. Он не обнуляет потраченную работу общей попытки. Исчерпание shared compile/check budget всегда CHECK_LIMIT; нельзя продолжать под видом неприменимого правила, выдать частичную проверку за полную или сбросить счётчик при KEEP.

Базовый driver обходит каждый исходный region один раз; внутренние generated nodes не запускают новый поиск оптимизаций. За одну позицию применяется максимум одно правило этой revision. Parent CLOSED_REPLAY строится из exact original semantic subtree и включает уже checked children путём flattening source schedule, а не склеиванием их повторных costs. Checker сравнивает flattened schedule с исходной local reference evaluation.

Ненасыщенный результат допустим. Нельзя заявлять оптимальность, единственную нормальную форму или максимальную скорость. Детерминированный порядок нужен для воспроизводимости, не для доказательства минимальности.

## 6. Общие ограничения

Эта revision не выполняет reassociation/commutation, elimination strict initializer, CSE внешнего чтения, speculative host effect, loop unrolling, TCO, inlining, semantic cost reduction, dynamic DATA batching или пользовательские rewrite plugins. Для них нужны новые rules с полным observation relation, state reconstruction и независимой приёмкой.

Даже algebraically valid x+0 не позволяет пропустить вычисление x или Result wrapping; initial catalogue не содержит такого blanket law. У checked arithmetic разные grouping могут менять Overflow/Err и дальнейший Match.

## 7. Конечность и limits

Точные значения задаёт pinned LimitsContract; baseline R22 defaults:

| Ресурс checker/producer | Default |
| --- | ---:|
| Каждый serialized input/output metadata payload | 16 MiB |
| Source/candidate IR nodes | 100 000 |
| Explicit traversal stack depth | 4 096 |
| Supplied rewrite steps | 4 096 |
| Local replay transitions на region | 4 096 |
| Совокупные reconstructed checkpoints | 262 144 |
| Local scalar pool entries | 65 536 |
| Reconstruction DAG nodes | 262 144 |
| Compile/check logical work units | 16 777 216 |

Все counters exact unsigned integers; bool/float/negative отвергаются. Add/multiply размеров проверяются до overflow/выделения. У каждой traversal/evaluation/checkpoint/comparison action есть счётчик compiler work; runtime budget не расходуется при компиляции. Physical memory/time guard может остановить checker отдельно с TOOL_LIMIT без успешного certificate.

На конечном input driver завершает bounded traversal. Closed local evaluator не имеет call/recursion и ограничен checkpoint budget. Повторяющийся source path, лишний rule, cycle reconstruction или превышение счётчика даёт явный отказ. Эти defaults не изменяют семантическую допустимость V1 программы; они задают область данной реализации инструмента.
