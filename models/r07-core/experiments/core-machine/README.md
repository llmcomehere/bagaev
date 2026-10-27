# CORE-0.1 · Типизированное чистое ядро и шаги исполнения

R06 проверяет совместимость конкретных правил типов и вычислений: lexical closures, настоящая рекурсия, явно специализированные rank-1 generic functions, checked Int64 arithmetic и точные шаговые границы отмены. Исходный материал — закрытый JSON AST; это исследовательский профиль SEM-0.1, а не parser/компилятор всего bagaev или реализация V1.

[API.md](API.md) определяет все JSON fields, types, primitive signatures, runtime records, диагностики и таблицу charges. [engine.py](engine.py) содержит checker и CEK-машину. Общая [runtime-спецификация](../../spec/runtime/core-machine.md) связывает этот профиль с дальнейшей V1-работой.

## Что исполняется

Программа имеет десять закрытых форм: const, var, let, if, lambda, call, letrec, prim, result и match_result. Значения включают Bool, Int64, Unit, ArithmeticError, Result и функции. Все параметры и результаты функций, let bindings и Result constructors аннотированы. Checker проверяет обе ветви, lexical bindings, арности и точные monotypes до создания runtime.

Letrec задаёт общий список type parameters своей группы. Внешняя ссылка явно специализирует scheme и получает мономорфную функцию. Внутри member body вся группа имеет monomorphic signatures с теми же rigid parameters: polymorphic recursion не допускается. Lambda и let не generalize. Вложенная группа может захватить внешние rigid types, но не получить forward reference на будущую лексическую группу. Полный source inference V1 проектируется отдельно.

Runtime хранит immutable lexical environments. Функция возвращается из factory вместе с захваченными значениями, даже когда соответствующих BinderIds уже нет в caller environment. Рекурсивная группа хранит outer environment, code ref и member slots; её создание не запускает тела. При вызове сначала вычисляется функция, затем каждый аргумент слева направо, затем начинается тело. Аргумент вычисляется и при неиспользуемом параметре.

Checked add/sub/div/rem возвращают Result<Int64,ArithmeticError>. Переполнение и деление на ноль — значения Err, которые можно передавать и разбирать явно. Они не являются автоматической остановкой машины. Деление округляется к нулю; `MIN / -1` возвращает Err Overflow, `MIN rem -1` — Ok(0). Bool не является Int64. Неподдержанные формы и неявные преобразования не получают приблизительного исполнения.

## CEK и точные границы

Control — текущий NodeId либо готовое Value; environment связывает BinderIds; continuation содержит явные frames. Function/group capture хранится в отдельной immutable arena, values ссылаются на её slots. Runtime call/recursion выполняется циклом переходов, независимо от глубины host stack. Рекурсивные обходы ограниченного AST/type tree относятся к подготовке и внутренним структурным операциям, а не к стеку вызовов программы.

Каждый из 21 опубликованных transition rules расходует ровно один semantic step. Trace содержит индекс шага, rule ID и исходный node_id: это позволяет различить порядок вычисления двух одинаковых по форме аргументов. Eval(Const) требует CONST transition; готовое Value с пустым continuation терминально без дополнительного RETURN.

| Выражение | Charged transitions |
| --- | --- |
| Const | 1 |
| Let(Const, Var) | 4 |
| Бинарный primitive с двумя Const | 5 |
| Call(lambda identity, Const) | 6 |
| Zero-argument Call(lambda returning Const) | 4 |

На каждой границе порядок таков: уже terminal состояние; видимая отмена; нулевой budget; следующий transition. `cancel_at=k` означает видимость после k completed transitions. Поэтому const с budget=1 успевает вернуть значение, и cancel_at=1 его уже не переписывает. При budget=0 и cancel_at=0 исход — CANCELLED. Остановка не добавляет charged trace entry.

Шаги не измеряют Python instructions, время или расход памяти. Результаты преобразования AST нельзя считать эквивалентными по budget/cancel только потому, что на большом бюджете они возвращают одно значение.

## Подготовка, identity и data encoding

`decode_program` проверяет exact top-level JSON keys. `prepare` глубоко фиксирует программу и проверяет её; исходные dict/list после этого можно менять без изменения prepared input. Source labels и revision отделены от actual content digest. NodeId определяет expression внутри exact artifact; BinderId определяет lexical binding. Они не подменяют друг друга.

Launch перестраивает checked indexes из immutable Program. Присланная вручную таблица типов не является доверенным разрешением на запуск другого AST. Machine и execution receipt закрепляют actual digest и фиксированную primitive revision.

`observe_value` представляет data вместе с типом. Для функции оно показывает только code descriptor; совпадение такого отображения не означает равенства captured environments. Проверка поведения замыкания вызывает его и сравнивает результат/trace. `encode_data` проверяет весь тип и отказывает при Function, в том числе в Result<Fn> независимо от выбранного Ok/Err payload. Этот маленький encoding не заменяет будущие versioned durable codecs V1.

## Воспроизведение проверки

Из корня R06-пакета:

```sh
python -B experiments/core-machine/verify.py --output results/core-machine/report.json
```

Independent oracle и authored corpus находятся в отдельной проверочной части. Oracle не импортирует checker/step из этой модели. Для ground data outcomes сравниваются значение или остановка, exact trace, число шагов и остаток бюджета. Ручные ожидаемые трассы служат отдельным ориентиром; два интерпретатора, воспроизводящие один дефект, сами по себе его не опровергают. Изменённые намеренно неверные варианты должны действительно расходиться на различающих примерах.

Actual числа проверок, hashes и исходы находятся только в созданном report. Эта инструкция не выдаёт запланированный запуск за выполненный. Profile reports прежних R01–R05 не меняются и не получают новые свойства задним числом.

## Ограничения результата

Checker принимает ограниченный размер AST/types/arity и конечный requested budget. Отдельные runtime guards ограничивают число heap captures, continuation frames и развёрнутый тип Value. Такой guard даёт ImplementationStop без нового semantic charge; это не Result.Err, не Cancelled и не BudgetExceeded. Полные пределы и коды заданы в API.

Область не включает String/Bytes/collections, общие пользовательские sums, recursive types, capabilities, host effects, storage, concurrency, memory ownership или native compilation. Они сохраняют собственные позиции в полном V1 scope. Из этого профиля не следует их окончательное исключение из языка.

Обязательные report flags: `bagaev_execution=false`, `research_core_execution=true`, `universal_proof=false`, `hypothesis_tested=false`. Конечный корпус проверяет конкретные правила и обнаруживает отдельные ошибки. Он не предъявляет универсальное preservation/progress доказательство и не закрывает целиком T03/T04/T06/T16.
