# MACHINE-CORE-0.1 — шаг, окружение и остановка

**R06 · исследовательский контракт.** Машина исполняет ровно [CORE-0.1 API](../../models/r07-core/experiments/core-machine/API.md). Авторитетные поля входа, типы внутренних записей публичного Python API и названия диагностик определены там. Это эталон выбранного pure kernel; runtime всего V1, host adapters, память и native backend ещё не закрыты.

## 1. Состояние и инварианты

```text
M = (prepared_artifact, control, env, type_env, K, captures,
     steps, remaining, trace, cancellation, termination)
control = Eval(NodeId) | Value(T, payload)
K = immutable stack of typed continuation frames
```

`prepared_artifact` закрепляет content digest и exact profile/primitive revisions. `env` связывает BinderId со значением либо generic group reference; `type_env` связывает доступные TypeParamId с текущими runtime-specializations. Capture record содержит код и сохранённые immutable environments; рекурсивная группа дополнительно содержит member slots. Слот локален запуску и не сериализуется как значение программы.

Для принятого состояния ожидаются инварианты: каждый читаемый binder имеет правильный тип; каждый continuation принимает именно тип текущего результата; current type parameters разрешены в scope; call arity/types согласованы; любой Result имеет известный tag и payload нужного типа. Нарушение инварианта сообщает ImplementationStop, а не вводит новый допустимый путь программы.

Вычислительный runtime не использует стек рекурсивных вызовов host для пользовательской рекурсии. Step — переход явного состояния. Декодер/type checker может использовать собственный стек в пределах опубликованных input guards; это другой этап и не semantic call depth языка.

## 2. Создание и вызов замыканий

Lambda создаёт запись `(code_ref, captured_env, captured_type_env)`, возвращая function value. Код тела ещё не исполняется. Letrec создаёт одну запись группы `(group_code_ref, members, outer_env, outer_type_env)` и доступные ссылки на участников. Внутригрупповая ссылка определяется парой group/member slots, а не бесконечной копией окружения.

При обычном вызове:

1. Вычислить выражение callee в окружении вызывающего.
2. Вычислить все аргументы в том же caller environment слева направо, каждый один раз.
3. Взять сохранённое окружение callee и расширить параметрами с уже готовыми значениями.
4. Для recursive member добавить monomorphic refs всех членов этой группы с текущей specialization.
5. Начать body. Caller environment не подменяет capture.

В `f(f(x))` выражение outer callee вычисляется первым, но outer body не начинается до завершения inner call. Неиспользуемый параметр не отменяет вычисление его аргумента. Result.Err в аргументе остаётся значением и не пропускает последующие strict arguments.

Группа может иметь ноль параметров типов и её функция может иметь ноль value-параметров. Generic member снаружи специализируется явными type_args; внутренние references monomorphic. Тело generic definition проверено под rigid параметрами, а runtime environment хранит конкретизацию. Повторное применение схемы к другому типу не изменяет прежнюю closure.

## 3. Continuation frames

| Frame | Что сохраняется | Что происходит при Value |
| --- | --- | --- |
| Let | Source node, binder, body, caller environments | Bind готовое значение и войти в body |
| If | Source node, обе ветви, caller environments | Выбрать одну Bool-ветвь |
| CallFn | Source node, args, caller environments | Для ненулевой арности начать первый arg; иначе войти в body |
| CallArgs | Source node, function value, готовые args, remaining args, caller environments | Следующий arg либо вход в body |
| Prim | Source node, primitive ref, готовые/оставшиеся args, environments | Следующий arg либо применить primitive |
| Result | Source node, tag, instantiated result type | Построить Result с готовым payload |
| Match | Source node, два binders/body, caller environments | Войти в выбранную ветвь с payload binding |

Type parameters не берутся из текущей глобальной таблицы compiler. Они сохраняются в каждом frame, которому предстоит снова вычислять код в его lexical scope. Иначе return из nested generic call способен испортить ожидаемый тип следующего аргумента.

## 4. Закрытый каталог переходов

Ровно 21 charged rule ID, каждый с ценой 1:

| Категория | Rule IDs |
| --- | --- |
| Literal / binding / capture | CONST, VAR, LAMBDA, LETREC |
| Let | LET_ENTER, LET_BIND |
| If | IF_ENTER, IF_THEN, IF_ELSE |
| Call | CALL_ENTER, CALL_ARGS, CALL_NEXT, CALL_BODY |
| Primitive | PRIM_ENTER, PRIM_NEXT, PRIM_APPLY |
| Result | RESULT_ENTER, RESULT_WRAP |
| Match | MATCH_ENTER, MATCH_OK, MATCH_ERR |

Точный source/target смысл каждой строки — в API §5. У каждого charged transition сохраняется `(step_index, rule, node_id)`. Administrative frame transitions также платные: их нельзя скрыть только потому, что backend выполнил работу одним машинным instruction. Таблица конечна; unknown opcode/frame/rule внутри принятой машины является invariant fault.

Нет отдельного RETURN transition. Eval(Const) отличается от Value и требует CONST; после него `Value + empty K` уже terminal. Для функции, возвращённой как значение, используется тот же terminal test; диагностическое описание Function не заменяет её последующий вызов и не задаёт equality замыканий.

## 5. Один наблюдаемый шаг

```text
step(M):
    if M is terminal or (control is Value and K is empty):
        return unchanged/returned terminal M
    if scheduled cancellation is visible after M.steps:
        return stop(Cancelled, same prefix and remaining)
    if M.remaining == 0:
        return stop(BudgetExceeded, same prefix)
    choose exactly one applicable rule by control and top frame
    calculate candidate immutable successor
    if implementation guard/invariant fails:
        return ImplementationStop with the published valid prefix
    publish successor with steps+1, remaining-1 and one TraceEntry
```

Проверка terminal/cancel/budget не создаёт новый charged entry. Для обычного semantic перехода steps+remaining сохраняет начальный budget. ImplementationStop не является переходом семантической reference machine; API определяет, что непубликованный переход не добавляет trace entry и не списывает шаг.

`cancel_at=k` в модели означает видимость после k завершённых переходов. У terminal `step` идемпотентен. Событие отмены на той же границе, где бюджет равен нулю, выигрывает у BudgetExceeded; на уже terminal boundary оно не меняет Returned.

## 6. Примеры точных стоимостей

Имена выражений ниже — математические сокращения, не утверждённый source syntax. Полный IR и authored traces находятся в [фикстурах](../../models/r07-core/fixtures/core-machine.json).

| Выражение | Переходы без ограничивающего прерывания | Минимальный step budget |
| --- | --- | ---: |
| `7` | CONST | 1 |
| `let x = 1 in 2` | LET_ENTER, CONST, LET_BIND, CONST | 4 |
| `if true then 1 else 2` | IF_ENTER, CONST, IF_THEN, CONST | 4 |
| `i64.add(2,3)` | PRIM_ENTER, CONST, PRIM_NEXT, CONST, PRIM_APPLY | 5 |
| `(lambda x:Int64 -> x)(7)` | CALL_ENTER, LAMBDA, CALL_ARGS, CONST, CALL_BODY, VAR | 6 |
| `(lambda () -> 7)()` | CALL_ENTER, LAMBDA, CALL_BODY, CONST | 4 |

Для literal `7`: budget=0 даёт BudgetExceeded без переходов; budget=1 возвращает 7 после одного перехода; budget=1 и cancel_at=1 тоже возвращают 7. При cancel_at=0 даже budget=0 даёт Cancelled. Для Let из таблицы budget=3 останавливается до последнего CONST; budget=4 возвращает 2. Замена Let на `2` меняет эту границу и потому не сохраняет cost semantics автоматически.

## 7. Опубликованные ограничения и гарантии

Input bounds и runtime guards перечислены в API. Semantic budget относится только к steps, принимает ограниченный опубликованный диапазон research runner. AST node/depth/arity/type-node guards — prelaunch ограничения этой реализации; capture/continuation/value guards могут дать ImplementationStop. Они не называются логическим бюджетом памяти V1 и не доказывают, что та же программа не исполнима на другом backend.

Рекурсивное значение closure/group не является persistable. `encode_data` сначала структурно проверяет весь runtime type: Fn запрещён даже в невыбранной ветви Result. Поэтому Err<Fn> не становится persistable из-за отсутствия Function в его фактическом payload. После проверки типа codec обходит payload; нельзя выдавать diagnostic code view за восстановимое значение. CORE не реализует generic nominal durable codecs и не принимает capabilities/handles.

При одинаковом подготовленном artifact, initial budget и cancellation schedule, внутри допустимых guards каждый следующий rule и наблюдаемый prefix однозначны. Это обоснование структуры детерминизма; конечные сравнительные runs проверяют конкретные случаи, не заменяя доказательство для всех допустимых artifacts.

## 8. Как использовать результаты дальше

Независимый oracle применяет другое представление вычисления и не вызывает `engine.step`. Authored traces дополнительно закрепляют смысл cost rules, чтобы две реализации не согласились на одну и ту же неверную новую цену. Mutation witnesses показывают конкретную чувствительность этих проверок; число mutants не оценивает процент всех возможных ошибок.

Будущий backend должен предъявить соответствие результата и logical schedule выбранному profile. Tail-call elimination, inlining и type erasure не получают бесплатного разрешения менять budget/cancel outcomes. Будущий effectful profile добавляет dispatch/reply/wait/settlement transitions отдельной версией; он не получает подтверждение из pure CORE report.
