# CORE-0.1 — API чистой CEK-машины

Статус: согласованный исследовательский контракт R06. Это исполнимый конечный профиль над [SEM-0.1](../../spec/language/semantic-core.md), не полный V1, промышленный компилятор или доказательство type safety. Здесь нет host/effect/emit, persistent state и анализа изменения программ. Действующие OBS/CALL/AUTH результаты не переинтерпретируются.

## 1. Artifact, типы и закрытые формы

`PROFILE_REVISION = 'core-machine/r06-v1'`, `PRIMITIVE_REVISION = 'core-i64/r06-v1'`.

```text
Program(source_id, revision, result_type, entry,
        profile_revision=PROFILE_REVISION)
```

Program глубоко фиксирует входные JSON-compatible значения; дальнейшая мутация исходного dict/list не меняет программу. Source ID и revision — объявленные labels. Они не доказывают идентичность содержимого: `prepare` вычисляет SHA-256 canonical artifact вместе с exact primitive revision; digest входит в runtime receipt и code refs. Каждый expression имеет обязательный уникальный `nid`. Каждый объявляющий value binder имеет глобально уникальный внутри artifact `BinderId`; source shadowing использует разные IDs. SourceId, NodeId, BinderId и TypeParamId имеют отдельные поля и назначения.

Тип JSON `T`:

```text
"Bool" | "Int64" | "Unit" | "ArithmeticError"
{"tag":"var", "id": TypeParamId}
{"tag":"fn", "params":[T,...], "result":T}
{"tag":"result", "ok":T}
```

Result всегда имеет ошибку ArithmeticError. Type variables разрешены только в lexical scope объявившей их группы. Fn содержит monotypes; forall не является типом значения. Внутренний immutable `Type` выводится через `type_json(type)` обратно в этот формат.

Ниже **все** разрешённые поля. Общие `op,nid` обязательны. Неизвестное поле, отсутствующее поле или неизвестный tag диагностируется до запуска.

| op | Остальные поля |
| --- | --- |
| `const` | `type`, `value` |
| `var` | `binder`, `type_args` — список T, в том числе пустой |
| `let` | `binder`, `type`, `value`, `body` |
| `if` | `condition`, `then`, `else` |
| `lambda` | `params`, `result_type`, `body` |
| `call` | `fn`, `args` |
| `letrec` | `type_params`, `functions`, `body` |
| `prim` | `name`, `args` |
| `result` | `tag` (`Ok`/`Err`), `ok_type`, `value` |
| `match_result` | `value`, `ok_binder`, `ok_body`, `err_binder`, `err_body` |

Param — exact object `{"binder":BinderId,"type":T}`. Function в letrec — exact object `{"binder":BinderId,"params":[Param,...],"result_type":T,"body":Node}`. Functions непусты; params и type_params могут быть пустыми. Все Function и lambda сигнатуры, let types и Result constructors имеют обязательные аннотации. Match содержит ровно обе ветви; payload types выводятся из scrutinee, результат ветвей должен совпасть. Обе If/Match ветви проверяются статически.

Const разрешён для Bool (только bool), Int64 (настоящий int, не bool; −2^63…2^63−1), Unit (null), ArithmeticError (`Overflow` или `DivisionByZero`). Const функций, Result или type variables не поддержан: для них существуют соответствующие формы. Неявных преобразований нет.

## 2. Rank-1 и рекурсивная группа

Let и lambda мономорфны; implicit generalization и inference type arguments отсутствуют. Letrec объявляет общий список явно различных type_params для всех членов группы. Внешние ссылки на её функции имеют scheme `forall type_params. Fn(params,result)`. Var обязан передать ровно соответствующее число type_args и возвращает уже специализированную мономорфную функцию, которую можно передавать, возвращать и захватывать.

Каждый member body проверяется при rigid type_params. Ссылки на **всю свою recursive group** внутри member body имеют мономорфные сигнатуры с теми же rigid parameters и требуют `type_args=[]`. Это исключает polymorphic recursion, включая обход через alias. Вложенный letrec может захватить внешние rigid type variables; его собственные TypeParamIds отличны. Scope лексический: отдельная ранее объявленная группа не может сослаться вперёд на ещё не объявленную группу. Higher-rank/forall-as-value и свободные type variables диагностируются.

Runtime group хранит code ref родительского letrec, member slots и immutable outer environment/type environment. Связи членов — group slot + member slot. Создание группы не исполняет ни одного function body. При вызове окружение тела строится из captured outer environment, членов той же группы с одной specialization и готовых аргументов. Lambda также захватывает immutable lexical values и type environment. Ни accepted-head lookup, ни dynamic caller scope нет.

## 3. Закрытая таблица примитивов

Все аргументы вычисляются слева направо, каждый ровно один раз. Все шесть примитивов бинарные.

| Name | Вход | Выход и границы |
| --- | --- | --- |
| `i64.eq` | Int64, Int64 | Bool: точное равенство |
| `i64.lt` | Int64, Int64 | Bool: математическое сравнение |
| `i64.add` | Int64, Int64 | Result<Int64>: Ok суммы либо Err Overflow |
| `i64.sub` | Int64, Int64 | Result<Int64>: Ok разности либо Err Overflow |
| `i64.div` | Int64, Int64 | Result<Int64>; нулевой делитель → DivisionByZero; MIN/−1 → Overflow; иначе quotient округлён к нулю |
| `i64.rem` | Int64, Int64 | Result<Int64>; нулевой делитель → DivisionByZero; иначе a−trunc(a/b)·b; MIN rem −1 → Ok(0) |

Математический quotient при вычислении остатка не обязан помещаться в Int64; сам допустимый остаток помещается. Host float division не используется. Err — обычное Returned value: его можно передать как аргумент Result, завернуть в другой Result и явно разобрать Match. Неявного terminal error propagation нет.

## 4. Публичные функции и записи

```text
prepare(program: Program) -> Prepared
decode_program(raw_json_object) -> Program       # exact Program keys
launch(program_or_prepared, budget, *, cancel_at=None,
       cancel_request_id='cancel') -> Machine
step(machine: Machine) -> Machine
run(program_or_prepared, budget, *, cancel_at=None,
    cancel_request_id='cancel') -> Execution
execution(machine: Machine) -> Execution       # только terminal machine
type_json(type) -> JSON type
observe_value(value) -> JSON diagnostic view
encode_data(value) -> JSON data                # Function запрещена рекурсивно
execution_json(execution) -> JSON receipt       # использует observe_value
canonical(value) -> JSON-compatible value
digest(value) -> SHA-256 hex
```

`decode_program` принимает JSON object ровно с пятью полями Program (включая явную profile_revision) и отклоняет неизвестные/пропущенные поля. Оно проверяет форму и замораживает данные; полная проверка типов происходит в prepare/launch. `Prepared` содержит immutable Program, actual `content_digest`, checked `result_type`, node/type indexes. Подготовка проверяет весь исходный artifact. Launch повторно получает проверенные indexes из замороженного Program, а не принимает присланные вручную type summaries за доказательство. Prelaunch validation не тратит semantic steps.

`Machine` содержит prepared input, control (node ID или Value), environment, type_environment, continuation, heap, steps, remaining, trace, cancel_at/cancel_request_id и termination/code. Environments, continuations и heap — immutable records/tuples. Heap хранит closure/group capture, а values используют ссылки; runtime recursion не использует host recursion stack. Внутренние записи машины не являются долговечным wire format.

`TraceEntry(step_index, rule, node_id)` фиксирует **каждый charged transition**. Индекс первого — 1. Continuation rule ссылается на nid исходного Let/If/Call/Prim/Result/Match, который создал frame.

`Execution(profile_revision, content_digest, termination, code, value, steps, remaining, trace, cancel_request_id)`:

- termination `RETURNED`, code `RETURNED`, value — immutable Value;
- termination `SEMANTIC_STOP`, code `BUDGET_EXCEEDED` или `CANCELLED`, value=None;
- termination `IMPLEMENTATION_STOP`, code `HEAP_LIMIT`, `CONTINUATION_LIMIT`, `VALUE_LIMIT` или `MACHINE_INVARIANT`, value=None.

cancel_request_id заполнен только при CANCELLED. Value содержит checked runtime type. `observe_value` для data возвращает `{type, value}` для скаляров и `{type, tag, value}` для Result с рекурсивным payload view. Для функции оно даёт `{type, kind:'Function', code:{content_digest,node_id,member}}`, где member — числовой slot члена группы с нуля в порядке functions, либо None у lambda; captured values скрыты. Такой вид функции — диагностическое описание code, **не** правило равенства замыканий. Проверка поведения closure должна вызвать её. `encode_data` проверяет Persistable структурно по всему runtime type и отвергает Function на любой глубине (`NON_PERSISTABLE_VALUE`), в том числе Err значения типа Result<Fn>, чей выбранный payload сам не является функцией. Отсутствие в profile equality/codec для функций не заменяется сравнением адресов.

## 5. Точная таблица CEK charges

Любое следующее правило потребляет ровно один step. Eval(Const) не является Value: CONST стоит один. Дополнительного RETURN перехода нет.

| Rule | Переход |
| --- | --- |
| CONST | Eval const → Value |
| VAR | Lexical lookup + exact explicit specialization → Value |
| LAMBDA | Capture immutable environment → function Value |
| LET_ENTER | Eval let → Eval initializer, push Let frame |
| LET_BIND | Value + Let frame → Eval body с binding |
| IF_ENTER | Eval if → Eval condition, push If frame |
| IF_THEN / IF_ELSE | Bool Value + If frame → Eval выбранной ветви |
| LETREC | Создать group/environment → Eval letrec body |
| CALL_ENTER | Eval call → Eval fn, push CallFn frame |
| CALL_ARGS | Function Value + CallFn frame с args → Eval первого arg |
| CALL_NEXT | Готовый не последний arg → Eval следующего arg |
| CALL_BODY | Function Value для zero-arg call или последний arg → Eval function body в captured environment |
| PRIM_ENTER | Eval prim → Eval первого arg, push Prim frame |
| PRIM_NEXT | Готовый не последний arg → Eval следующего arg |
| PRIM_APPLY | Последний arg → typed primitive Value |
| RESULT_ENTER | Eval constructor → Eval payload, push Result frame |
| RESULT_WRAP | Payload Value → Result Value |
| MATCH_ENTER | Eval match_result → Eval scrutinee, push Match frame |
| MATCH_OK / MATCH_ERR | Result Value → Eval соответствующей ветви с payload binding |

Сначала проверяется уже terminal состояние, включая Value с пустым K. Затем — видимая отмена, затем нулевой budget. `cancel_at=k` означает видимость после ровно k completed transitions, до следующего. Поэтому const с budget=1 возвращается после CONST; cancel_at=1 его не отменяет. При budget=0 и cancel_at=0 выигрывает CANCELLED. Terminal, cancellation и budget stop не добавляют charged trace entry. Уже terminal Machine при step возвращается неизменной.

Физический guard перед публикацией следующего transition может дать ImplementationStop без нового charged entry. Его нельзя приравнивать к budget stop или успешному data outcome. Переписывание AST может менять charges; здесь не заявлена cost-preserving оптимизация.

## 6. Диагностики и ограничения реализации

`CoreError(code, path=(), detail='', kind='PrelaunchDiagnostic')` — отказ до запуска при неверной форме/типе/неподдержанном вводе. Основные коды: `UNSUPPORTED_PROFILE`, `UNKNOWN_FORM`, `UNKNOWN_FIELD`, `MISSING_FIELD`, `INVALID_LITERAL`, `INVALID_ID`, `INVALID_UNICODE_SCALAR`, `DUPLICATE_NODE_ID`, `DUPLICATE_BINDER`, `DUPLICATE_TYPE_PARAMETER`, `UNBOUND_VARIABLE`, `UNBOUND_TYPE_VARIABLE`, `TYPE_MISMATCH`, `TYPE_ARGUMENT_ARITY`, `CALL_ARITY`, `UNKNOWN_PRIMITIVE`, `INVALID_RESULT_TAG`, `INVALID_BUDGET`, `INVALID_CANCELLATION`, `PROFILE_LIMIT`. Некорректный discriminator/type shape даёт `INVALID_TYPE`/`INVALID_SHAPE`. Unsupported higher-rank type не превращается в monotype. CoreError `NON_PERSISTABLE_VALUE` при encode_data — явный отказ codec, kind=`CodecDiagnostic`.

Предельный вход этого исследовательского исполнителя: 1 024 expression nodes; expression depth 64; 1 024 value binders; 128 TypeParamIds; arity/group members 16; type_params одной группы 8; type nesting 32; ID/labels 128 Unicode scalars. Budget — целое 0…65 536; больший запрос вне опубликованного input profile, а не semantic stop. Cancel_at — неотрицательное целое ≤65 536, bool запрещён. Type nodes во всех явных annotations/type_args суммарно ≤8 192.

До разбора форм raw JSON freezing отдельно ограничен 65 536 посещёнными значениями, глубиной 256 и длиной строковых значений 512 scalars; для допустимых ID затем действует более узкий предел 128. Program constructor и decode_program применяют эту границу к целому artifact. Она также даёт PROFILE_LIMIT до запуска; неизвестные или циклические host containers не обходятся безгранично.

Runtime guards: не более 4 096 heap capture records и 4 096 continuation frames. Развёрнутый тип создаваемого runtime Value ограничен глубиной 64 и 8 192 посещёнными type nodes; это отдельно учитывает подстановку generic arguments. Глубина в этих таблицах — число рёбер от root, у root ноль. Guard VALUE_LIMIT не превращает чрезмерную подстановку в program Err. Эти границы физические. Счётчик steps — единственный semantic resource данного профиля; полная V1 memory/resource policy этим не задаётся.

Канонизация artifact использует JSON UTF-8, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False. SHA-256 preimage: `{profile_revision:PROFILE_REVISION, primitive_revision:PRIMITIVE_REVISION, program:canonical(program)}`. Порядок args/functions/params/constructor payload сохраняется; dict key sorting не меняет source evaluation order.

Отчёт сохраняет `bagaev_execution=false`, `research_core_execution=true`, `universal_proof=false`, `hypothesis_tested=false`. Конечные traces и independently authored cases не закрывают T03/T04/T06/T16 всего V1.
