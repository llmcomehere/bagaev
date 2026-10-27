# TYPES-0.1 — проверка типов и локальный вывод

**R06 · WORKING_DESIGN.** Документ задаёт проект алгоритма для V1 и точную границу реализованного исследовательского подъязыка. [CORE-0.1](../../models/r07-core/experiments/core-machine/API.md) проверяет уже аннотированный IR: Bool, Int64, Unit, ArithmeticError, Result с фиксированным error type, функции, общие параметры рекурсивной группы. Source inference, пользовательские nominal types, контейнеры и эффекты описаны здесь, но не объявляются исполненными опытом R06. Type-safety доказательство T04 остаётся открытым.

**r26.** Документ дополнен решениями D69 (рекурсивные типы), D70 (эффект-переменные), D74 (явные сигнатуры верхнего уровня) и D79 (порядок тегов, MapBuild). Исходный синтаксис — [surface.md](surface.md), эффекты — [effects.md](effects.md), коды — [DIAG-1](../diagnostics/registry.json). Прежние имена диагностик этого документа (InfiniteType, SkolemEscape и др.) — псевдонимы кодов DIAG-1.

Связанные контракты: [SEM-0.1](semantic-core.md), [IR](../ir/typed-core.md), [ошибки](errors.md), [машина](../runtime/core-machine.md). Обязательные функции V1 из [реестра](../profiles/v1.md) не исключаются ограничениями CORE.

## 1. Конечный выбор возможностей

1. Типы первого ранга: `forall` допустим только на уровне схемы именованного binding, не внутри параметра, поля, элемента контейнера или результата функции. При передаче generic-функции как значения её схема сначала специализируется до monotype.
2. Все функции и точки входа верхнего уровня имеют явные сигнатуры, включая ряд эффектов (D74). В локальной Lambda типы параметров задаются явно либо поступают из известного ожидаемого Fn. Результат локальной функции допускает синтез из тела. Неоднозначность не разрешается defaulting.
3. Обычный Let связывает monotype. Неявного HM let-generalization нет. Для локальной generic-функции требуется явное объявление с параметрами типов и Lambda/FunctionDef в RHS. Это проверяемое правило generalization, а не обещание произвольного inference.
4. Higher-rank, impredicative instantiation, higher-kinded параметры и неявные coercions отвергаются до запуска. Полиморфная рекурсия функций верхнего уровня допустима: их схемы явные, выводить её не нужно (D74). Отказ не исключает обычные параметрические функции, пользовательские параметрические и рекурсивные типы (D69), рекурсию и замыкания.
5. Все функции модуля образуют одну рекурсивную группу (BIR `LetRec`). Каждая проверяется против своей явной схемы. Ссылка на функцию группы, в том числе рекурсивная, специализирует её схему так же, как внешняя (D74). Локальные лямбды не рекурсивны и мономорфны.
6. Эффекты в типах функций — ряды: конечное множество атомов плюс не более одной эффект-переменной ранга 1 (D70, [effects.md §2–3](effects.md#2-ряд-эффектов)). Неявного function subtyping нет. Лямбда проверяется по включению «фактический ⊆ ожидаемого» и получает ожидаемый ряд. Это не создаёт capability.

Это конкретное предложение V1; совместимость с прежними реализациями не требуется (D64). Эксперимент проверяет подпрофиль, в котором все аннотации и type_args уже явны, а effects пусты.

## 2. Monotype, схема и окружения

```text
τ ::= Bool | Int64 | String | Bytes | Unit | Never
    | rigid(TypeParamId)
    | Nominal(TypeEntityRef, [τ])        -- record, enum, opaque; регулярная рекурсия допустима (D69)
    | Option(τ) | Result(τ, τ) | Seq(τ) | Map(τ, τ)
    | Fn([τ], τ, ρ)
    | Table(τ, τ)                        -- только параметры std.store (EFFECTS-1 EFF-07)
ρ ::= { atom… } | { atom… } ∪ effvar(EffectParamId)      -- EFFECTS-1 §2
σ ::= forall [TypeParamId : Bounds] [EffectParamId]. τ
Bounds ::= finite subset of {Eq, Key, Persistable}
```

`TypeEntityRef` включает точную сущность и её revision в ProgramSnapshot; одинаковое отображаемое имя не делает nominal types равными. Record и Sum определяются в таблице номинальных типов через список полей либо вариантов с payload type. Типовые конструкторы имеют фиксированную арность и kind `* ... * → *`; параметр не может занимать место конструктора. Option/Result — заранее объявленные closed sums: `Option = None | Some(T)`, `Result = Ok(T) | Err(E)`, ordinals None=0, Some=1, Ok=0, Err=1 (D79). `Never` — пустой тип выражений `return`; он совместим с любым ожидаемым типом (§7). Пользовательского значения типа Never нет. Capability и HostHandle не являются типами пользовательской программы V1 (EFFECTS-1 EFF-11).

Служебные `meta(i)` существуют только во время inference; их нет в принятом typed IR. `Γ` связывает разрешённый BinderId со схемой; `Δ` задаёт доступные rigid type parameters и их bounds; `Σ` — точная таблица типов/функций/примитивов из snapshot. Исходные имена разрешаются до этой проверки. Диагностика содержит source ref, но source span не является идентичностью binding.

Well-formedness проверяет: известность и арность каждого типа, доступность параметров, отсутствие forall в monotype, отсутствие повторных ID деклараций, уникальность field/tag ID, корректность effects и bounds. Рекурсивные пользовательские типы допускаются (D69), если каждое рекурсивное обращение к типу внутри его группы деклараций использует те же параметры в том же порядке. Нерегулярная рекурсия → `IRREGULAR_RECURSIVE_TYPE`. Значения конечны: вычисление строгое и неизменяемое. В CORE допустимо только конечное дерево типов из его API.

## 3. Разрешение имён и рекурсивные области

```text
resolve(block, outer_scope):
    allocate distinct BinderId for each declaration in the block
    reject duplicate declaration in the same source namespace
    predeclare exactly the members of each explicit recursive group together
    resolve each ordinary initializer only in the preceding lexical scope
    resolve each recursive member body in preceding_lexical_scope + whole_group + its_params
    resolve the following body in outer_scope + completed_bindings
    preserve the resolved IDs in IR; a later rename changes display text only
```

Nested source shadowing допустим: новое имя получает другой BinderId. Глобальная уникальность BinderId внутри CORE artifact позволяет проверить отсутствие скрытого aliasing. Область Let initializer не включает создаваемый binding. Lambda parameter виден только в её теле. Binder варианта Match виден только в соответствующей ветви. Группа не читает «будущие» объявления вне своей lexical scope.

**r26 (D74).** Объявления верхнего уровня модуля видны во всём модуле без порядка и образуют одну рекурсивную группу. Код `RecursiveGroupRequired` выведен из употребления. Каждая функция имеет явную схему, поэтому полиморфная рекурсия проверяется, а не выводится. Локальные binding видны только после объявления. Циклы импорта модулей запрещены (`MODULE_IMPORT_CYCLE`). У CORE нет module lookup: lexical resolution непосредственно исключает внешние циклы.

Разрешённая ссылка закрепляется за snapshot. Runtime не ищет функцию заново по имени и не подставляет актуальный accepted head.

## 4. Равенство типов и унификация

Равенство monotypes структурное после разрешения alias, но nominal constructors сравниваются по точному TypeEntityRef. Порядок аргументов, арность Fn и точное множество latent effects входят в сравнение. Никаких numeric widening, Bool→Int64, record width subtyping или nominal→underlying cast.

```text
unify(a, b, subst):
    a := prune(subst, a); b := prune(subst, b)
    if a == b: return subst
    if a is meta:
        if occurs(a, b): fail InfiniteType
        if rigid_free_vars(b) not subset allowed_rigids(a): fail SkolemEscape
        restrict every unresolved meta in b to intersection with allowed_rigids(a)
        bind a := b; return updated subst
    if b is meta: return unify(b, a, subst)
    if either is rigid: fail RigidTypeMismatch
    if constructor/nominal_ref/arity/effect_set differ: fail TypeMismatch
    for paired type arguments in declaration order:
        subst := unify(left, right, subst)
    return subst
```

Rigid parameter унифицируется только с тем же rigid ID. Допустима привязка новой meta к доступному rigid, например внутри generic-тела; запрещён выход этого rigid за его lexical scope. При создании meta сохраняется множество rigid IDs, доступных в её lexical scope. Связывание meta с типом разрешено только при допустимости всех rigid в этом типе; allowed sets вложенных metas сужаются пересечением и никогда не расширяются. Поздняя привязка также проходит эту проверку. Так ограничение действует на substitutions в outer Γ, а не только на итоговый тип, и fresh meta внутренней функции не может протащить её skolem наружу через старую meta. При выходе из scope проверяются нормализованные result, outer Γ и pending substitutions; оставшийся недоступный rigid даёт SkolemEscape. После решения все metas и aliases нормализуются. Occurs check запрещает `α = Fn([α], β)`, а не пытается создать неявный recursive type.

Чтобы алгоритм был конечным, вход — конечное well-formed дерево; каждая meta связывается однократно, новые meta создаются только для конечного числа instantiation sites. `prune` не создаёт циклов. Физические лимиты compiler/type-checker учитываются отдельно; отказ их защиты не превращается в TypeMismatch.

## 5. Специализация и generalization

Для `Γ[b] = forall [a1…an]. τ`:

1. Если type_args указаны, проверить их количество, well-formedness и bounds; выполнить capture-avoiding substitution по TypeParamId.
2. Если type_args отсутствуют в source, создать n свежих meta, не общих с другим использованием `b`.
3. Instantiation возвращает monotype, свежие metas и отложенные bounds; сам Var не выдаёт premature ambiguity. Вызов добавляет уравнения между фактическими и ожидаемыми типами аргументов. Известный ожидаемый тип результата также добавляет уравнение.
4. Унифицировать доступные уравнения в source order, откладывая окончательные bounds/ambiguity до границы полного initializer, function body или entry (§7). Это позволяет позднему аргументу или ожидаемому типу уточнить раннюю instantiation.
5. На этой границе применить общую substitution ко всем pending instantiations, проверить bounds; любой оставшийся неопределённый meta параметра — `AmbiguousTypeArgument` с индексом/ID параметра. Typed IR получает только явные, полностью определённые type_args; неизвестный будущий контекст следующего binding не угадывается.

Например, `identity<Int64>(3)` и `identity<Bool>(true)` — два использования одной схемы. В CORE оба type_args явны; реализации source inference здесь ещё нет. Функция `make<A>() -> Option<A>`, вызванная без ожидаемого типа и без явного A, не выбирает тип по привычке компилятора.

**Explicit generalization.** Объявление `f<A…>(params) -> result ! effects = body` создаёт свежие rigid IDs для заявленных параметров. Проверяется body в этом `Δ`, все свободные типовые переменные должны принадлежать заявленным параметрам либо внешнему lexical `Δ`. Экспорт запрещает свободные внешние параметры. Только после проверки наружу выдаётся схема forall. Неиспользованные параметры разрешены, но их нельзя автоматически восстановить при вызове; они требуют type_args или достаточного ожидаемого контекста.

RHS explicit generic local binding должен быть функцией, создание которой не вычисляет её body. Произвольный эффектный initializer не получает forall. Обычный Let сохраняет полученный monotype; его последующее использование не создаёт новые metas. Lambda- и pattern-bound параметры также monomorphic. Благодаря этому generic-функция не может неявно поступить как `forall`-значение в поле или аргумент другого вызова.

## 6. Проверка функции и взаимной рекурсии

```text
check_module(module, Γ, Δ):                 -- r26, D74
    for member in declaration order:
        validate member's explicit scheme σ_m = forall a_m, !e_m. τ_m under Δ
    Γmod := Γ + {member_id ↦ σ_m for every member}   -- схемы, не monotypes
    for member in declaration order:
        rigid a_m, e_m := fresh for this member
        reject duplicate parameter IDs
        check(member.body, member.result, Γmod + member.params, Δ + a_m)
        require actual_effects(body) ⊆ member.declared_row      -- EFFECTS-1 EFF-04
    reject any escaping rigid / unresolved meta
    return Γmod
```

Каждая ссылка на функцию модуля, в том числе рекурсивная, специализирует её явную схему свежими metas (§5). Значение-функция, переданное через Let или захваченное Lambda, — monotype: alias не восстанавливает схему. Модель CORE-0.1 использует прежнее правило общего вектора (`type_args=[]` на внутренних ссылках). Это её собственный исследовательский профиль, а не правило V1.

Type checker может проверить recursive body относительно явно объявленных effect bounds без выполнения функции. Для публикации более точного inferred effect summary отдельно решается монотонная система объединения effect sets по recursive SCC в конечном домене SEM-0.1; direct-call contribution берётся из summary target, indirect-call contribution — из указанного latent bound. Каждый summary должен оставаться под declared bound. Эта отдельная процедура не является проверенной частью pure CORE.

Рекурсивный вызов не выполняется при проверке типов, создании Lambda или создании группы. Static type checking не доказывает завершения. Runtime может вернуть значение, остановиться по budget/cancel или попасть в реализационный отказ — в последнем случае выполнение не считается подтверждением семантики программы.

Взаимно рекурсивные функции могут иметь независимые схемы: каждая проверяется против своей. Вывод полиморфной рекурсии не нужен, потому что схемы явные. Closure может захватить rigid внешней generic-функции; при вызове сохраняется его текущая специализация.

## 7. Синтез и проверка выражений

Суждения: `Γ;Δ;Σ ⊢ e ⇒ τ ! ε` синтезирует тип и эффекты; `Γ;Δ;Σ ⊢ e ⇐ τ ! ε` проверяет известный тип. Оба возвращают также общую substitution и pending instantiations. Check передаёт expected type внутрь Var, Call, Lambda, конструкторов, результата Let/If/Match/Seq; для остальных форм использует synth+unify. Все ветви проверяются до запуска, независимо от условия.

Finalization выполняется после полного initializer каждого Let, после каждого function body и после entry; внутри Call, Var или отдельного аргумента её нет. Аннотированный Let сначала `check(initializer, annotation)`, затем finalize и binding; неаннотированный — `synth(initializer)`, затем finalize и binding. Body Let не помогает угадывать тип уже завершённого initializer. Вызов сначала получает callee Fn с fresh metas, проверяет арность, унифицирует callee.result с известным expected result ДО проверки аргументов, затем передаёт уточнённые formal types в check аргументов и возвращает общие constraints наружу. Поэтому expected Fn результата generic choose<T>(x:T)->T может дать тип параметру переданной Lambda. Seq синтезирует первое выражение и передаёт expected type только последнему. В If/Match expected result передаётся всем ветвям, а без него синтезированные branch types унифицируются до finalization. Поэтому `let x: Option<Int64> = make<A>()` может вывести A=Int64, а `let x = make<A>()` без иного контекста получает ambiguity. В этой записи пропущенный A обозначает source inference site, не уже явный type argument IR.

| Форма | Алгоритм типов | Эффекты создания/вычисления |
| --- | --- | --- |
| Const | Проверить точное значение и declared type; Bool не Int64 | ∅ |
| Var | Найти BinderId, специализировать схему, проверить явные type_args | ∅ |
| Let | При annotation проверить initializer против неё; иначе синтезировать; finalize; связать monotype; проверить body | union initializer/body |
| Seq | Проверить первое, затем второе; результат второго | union обоих |
| If | Condition:Bool; обе ветви одного типа после унификации | union condition/обеих ветвей |
| Lambda | Из params annotations/expected Fn получить monotypes; проверить body/result и bound | Создание ∅; latent bound хранится в Fn |
| RecursiveGroup | Алгоритм §6, затем body в Γoutside | Создание группы ∅; body effects |
| Call | Синтезировать callee Fn; специализировать схему до monotype; проверить арность и аргументы по порядку | union callee/args/latent bound |
| Record | Найти nominal record и substitution; точный набор полей, без дублей; каждый initializer заданного типа | union в source order |
| Field | Receiver заданного nominal record; field ID существует; тип через substitution | effects receiver |
| Variant | Tag принадлежит указанному closed sum; payload заданного типа | effects payload |
| Match | Scrutinee:closed sum; exact tag coverage; payload binders; единый тип ветвей | union scrutinee/всех ветвей |
| Sequence | Из annotation/expected type получить элемент; проверить каждый; пустая без ожидаемого типа — ambiguity | union элементов |
| MapBuild | K/V из annotations/context; require Key(K); проверить key/value каждого элемента | union всех выражений; result `Result<Map<K,V>, DataError>` с кодом `DuplicateKey` (D79). Литерал `Map {…}` исходника — MapBuild с Fault `DUPLICATE_KEY` при повторе (SURF-30) |
| Prim | Exact primitive revision и declared signature; explicit generic constraints | union аргументов + primitive declared effects |
| Perform | Точная сигнатура операции хоста или std.store / event.emit; аргумент Table — статический путь (EFF-07) | union аргументов + атом операции (EFFECTS-1 §1); runtime authority отдельно (EFF-11) |
| Return | Значение проверяется против результата объемлющей функции; тип выражения `Never` | эффекты значения |

Выражение типа `Never` проверяется против любого ожидаемого типа. В If/Match без ожидаемого типа ветвь типа Never принимает тип остальных ветвей. Для пустого record/variant payload Unit имеет определённый тип; отсутствие поля не приравнивается Unit. `Result.Err` и `Option.None` требуют известного полного sum type (или ожидаемого контекста), поскольку тип отсутствующего payload нельзя угадать. Short-circuit lowering в If происходит до этих правил. Ранний Result propagation `e?` — явное lowering в Match и Return (SURF-39, D73); внутреннего автоматического unwind для Err нет.

**Типы параметров лямбды (r26).**
- Аргументы вызова проверяются слева направо (выше). Лямбда-аргумент получает формальный fn-тип после подстановки уже решённых metas.
- Если тип параметра там ещё meta, параметр получает эту meta. Она решается по телу лямбды или по следующим аргументам и окончательно — на границе финализации.
- Операция, которой нужен известный тип операнда — обращение к полю, `match`, `==`/`<`, `++`, `?`, — на операнде с ещё не решённой meta параметра лямбды → `PARAMETER_TYPE_REQUIRED`.
- Поэтому `seq.map(xs, fn(x) => x.title)` проверяется, если xs стоит раньше лямбды, а `f(fn(x) => x.title, xs)` требует аннотации `fn(x: Article) => …`.

Частичный source inference никогда не принимает выражение с неразрешённым типом функции. Если callee не имеет выводимого Fn, ошибка `FunctionTypeRequired`; если Lambda parameter не имеет annotation/known expected type, `ParameterTypeRequired`. Такие отказы завершают алгоритм и являются частью предложения V1.

## 8. Полнота Match и типизированные отказы

В canonical typed IR для закрытого sum разрешён плоский набор `tag → (payloadBinder, body)`; каждый tag указан ровно один раз. Нет catch-all, guard, literal, nested или or-pattern на этом уровне. Исходный синтаксис шаблонов — [SURF-32](surface.md#4-выражения): ровно такой же плоский набор, без ветви «всё остальное».

```text
check_match(sum_ref, actual_arms):
    expected := ordered tags in exact declared sum revision
    reject arm with an unknown tag
    reject repeated tag
    missing := expected - actual_tags
    if missing nonempty: fail NonExhaustiveMatch(missing)
    for tag in expected declaration order:
        bind its exact payload type in a fresh branch scope
        check branch result against the same expected result type
```

Проверка tag coverage линейна по числу объявленных tags и arms после построения lookup table; стоимость проверки branch bodies учитывается отдельно. Coverage не перечисляет возможные payload values и не пытается решать arbitrary predicates. Empty sum разрешается только после отдельного решения о его значениях/элиминации; до него декларация требует хотя бы один tag. В CORE Result имеет ровно Ok и Err, API содержит обе обязательные ветви, payload Err:ArithmeticError.

Ошибки делятся по фазе:

| Случай | Исход |
| --- | --- |
| Нет ветви, повтор/чужой tag, неверный тип ветви | PrelaunchDiagnostic |
| Неверный внешний сериализованный tag | Ошибка versioned decoder до появления внутреннего значения |
| Неизвестный tag в уже принятом внутреннем value | ImplementationStop: нарушен invariant |
| Рекурсивный вызов с типом, несовместимым с явной схемой | PrelaunchDiagnostic `TYPE_MISMATCH` (D74) |
| Бесконечная корректно типизированная рекурсия | Шаги продолжаются до заданной SemanticStop; это не type error |
| Recursive group с не-функциональным initializer | PrelaunchDiagnostic; неисполненное рекурсивное значение не создаётся |

## 9. Eq, Key и Persistable

Закрытый проект правил структурных predicates (это не пользовательские type classes и не dispatch):

| Тип | Eq | Key / полный порядок | Persistable |
| --- | --- | --- | --- |
| Bool, Int64, String, Bytes, Unit | Да | Да | Да |
| Nominal record | Если все поля Eq | Если все поля Key; лексикографически по declaration order | Если все поля Persistable и codec зарегистрирован |
| Nominal closed sum / Option / Result | Если все payload Eq | Если все payload Key; tag по declaration ordinal, затем payload order | Если все payload Persistable и codec зарегистрирован |
| Seq<T> | Eq(T) | Key(T), лексикографически | Persistable(T) |
| Map<K,V> | Key(K) и Eq(V) | Нет в этой редакции | Key(K) и Persistable(K,V) |
| Opaque T (представление R) | Если Eq(R) | Если Key(R); порядок R | Если Persistable(R) и codec зарегистрирован |
| Fn, Capability, HostHandle | Нет | Нет | Нет |
| Rigid parameter A | Только из bound Eq или Key | Только из bound Key | Только из bound Persistable |

`Key ⇒ Eq`. Предикаты opaque-типа выводятся из представления и вне его модуля, но значения сравниваются только внутри того же opaque-типа: `PersonId` нельзя сравнить со `String` или с `ArticleId`. Persistable не означает Key и не является разрешением на запись. Nominal scalar wrappers сохраняют свою nominal identity: их порядок определён только внутри того же wrapper type. Сравнение значений разных nominal types статически отвергается. Capability/HostHandle не становятся persistable или сравнимыми, если поместить их глубже в контейнер.

Строковый порядок — по Unicode scalar values без normalization/locale; Bytes — по байтам; Bool: false < true; Unit имеет единственный элемент; Int64 — математический знаковый порядок. Для суммы ordinal/tag table относится к exact schema revision; изменение порядка tags может изменить порядок ключей и требует совместимости/миграции. Это не разрешает автоматически сравнивать два schema revisions.

Predicate проверяется обходом графа declared types с substitution и memoization по exact instantiated type. Для рекурсивных типов (D69) результат — наибольшая неподвижная точка: тип, встреченный повторно на текущем пути, считается удовлетворяющим, пока его поля не опровергнут предикат. Так `type List<T> = enum { Nil, Cons(Node<T>) }` с узлом-записью Eq, если Eq(T). Неопределённый codec даёт отказ persistability validation. Таблица не делает durable codec уже реализованным.

## 10. Детерминированная диагностика и пределы обещания

Checker идёт по порядку форм/полей из registry; первая ошибка — канонический ответ kernel (SURF-58). Коды — [DIAG-1](../diagnostics/registry.json). IDE может дополнительно собирать другие diagnostics после восстановления, но не считать их результатом успешного type check. У сообщения есть code, phase, node/source ref, expected/actual и связанные declaration refs. Выбор языка сообщения не меняет code.

Неизвестная версия, неизвестная форма, неизвестные/отсутствующие поля, неправильный kind, arity, malformed literal и unresolved binder диагностируются до выполнения. Счётчик исполнения равен нулю. Physical compiler guards имеют отдельный статус; отсечение анализа не становится доказательством ill-typed программы.

Проверяемые будущие обязательства: единственность разрешения имён; сохранение rigid scope при substitution; soundness instantiation; сохранение типов continuation/closure; полнота coverage для declared sums; primitive type preservation; effect bound inclusion; simulation lowering→typed IR. R06 не предъявляет universal proof и не запускает full source inference. Независимый CORE корпус проверяет конкретные типизированные и отклоняемые программы по его точной API.
