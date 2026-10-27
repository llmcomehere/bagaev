# CALL-0.1 · API исследовательской композиции

R04 расширяет закрытый OBS-0.1 статическими типизированными вызовами. Это Python 3.10+ и standard library, не синтаксис или runtime bagaev. Модуль `engine.py` экспортирует `obs` — закреплённый OBS engine, `laws` — закреплённый R03, `ResourceState = obs.ResourceState` и `Type = obs.Type`. Для единой идентичности классов используйте эти экспорты.

## Область и закреплённая основа

Один immutable Authorship, одна точная compile-config на программу, встроенный `provider/v1`. Наблюдаются статус, значение/ошибка, упорядоченная trace и полнота исполнения. Время, память, количество внутренних шагов и host-ресурсные отказы не входят в эквивалентность.

Все OBS-конструкторы и их типовые правила сохраняются: signed64 int, Unicode scalar strings, строгий let, обе статически проверяемые ветви, ошибки и эффекты. Добавляется только:

```json
{"op":"call","target":"function-id","args":[],"type":"int"}
```

`target` — exact stable ID, не вычисляемое выражение. `type` — обязательная аннотация результата в формате OBS. Если определение присутствует, проверяются число и типы аргументов, аннотация результата и реальный тип тела. Для отсутствующего target тип результата берётся из этой аннотации, а анализ остаётся неполным. Динамическое разрешение, overloads, closures, function values, host I/O и поддержка рекурсивных функций не добавлены.

Закреплены SHA-256 OBS engine `9406e4faefd01def24d87f2316f0d21546ea971eb99194771d5ce9eafdca48da` и R03 laws `ab830682a35ac09d72bb319c26c7a0671c77a63f3e0a6e50f4842973207e7f37`. Проверки загрузки и контекста не разрешают незаметно сменить основу. Другой provider даёт incomplete use и UNKNOWN, включая случай одинаковой неподдержанной строки до/после.

## Неизменяемые записи входа

Все dataclasses frozen; AST, аннотации, config и requirements глубоко фиксируются. `dataclasses.replace` не делает запись доверенным основанием.

- `Param(name, type)` — имя и OBS-аннотация типа.
- `Function(stable_id, params, return_type, body, alias='')` — упорядоченные уникальные параметры, аннотация результата и тело. `body=None` означает signature-only external, который этот профиль не исполняет. `signature_revision` и `definition_revision` вычисляются из точных исходных данных; alias не отражается в семантике.
- `Registry(functions)` — последовательность Function с уникальными stable IDs. `manifest_stamp` закрепляет все определения; порядок записей не влияет на manifest.
- `Consumer(stable_id, program, compile_config={}, provider_revision='provider/v1', requirements={}, alias='')` — входная программа CALL, без свободных переменных. `program_revision` и `input_stamp` вычисляются автоматически.
- `Program(entry: Consumer, registry: Registry)` — единый вход функций анализа и исполнения.

Локальное имя параметра не совпадает с ID функции автоматически: это разные пространства. Caller-переменные не попадают в тело функции. В нём доступны только параметры и собственные lexical lets. Shadowing локальным let разрешён; initializer проверяется до ввода нового binding.

## Типы, исполнение и неполнота

`validate_program(program) → obs.Type` проверяет всю entry и все объявленные тела, включая невыбранные ветви и неиспользованные определения. Поэтому неверная unrelated функция — диагностический отказ; корректная unrelated функция не загрязняет reachable use/closure.

`execute(program, resource) → obs.Execution` исполняет CALL AST непосредственно. Все аргументы вычисляются один раз слева направо в caller env. Ошибка или unknown аргумента прекращает вызов и сохраняет уже полученную trace. Лишь после аргументов target включается в active stack, значения связываются с параметрами и тело исполняется в свежем env. Поэтому `f(f(x))` при нерекурсивном `f` допустимо.

Missing target после аргументов даёт runtime unknown `MISSING_CALLEE:<id>`, external — `EXTERNAL_CALLEE:<id>`, повторное вхождение target в active stack — `CALL_CYCLE:<id>`. Это не успешный pure result и не выполнение внешнего кода. Статический анализ сохраняет incomplete даже при фактически невыбранной такой ветви. Для unsupported provider исполнение возвращает явный unknown до выполнения программы.

## Автоматическая модульная композиция

`analyze(program) → Analysis(result_type, use, closure, closure_stamp, registry_stamp, function_summaries, entry_stamp, semantic_stamp)`.

`use` — обычный `obs.UseSummary`. Тело функции анализируется с `params → Type`; чтение параметра не создаёт нового resource observation. Каждый call обязательно объединяет use **всех** strict аргументов и callee body: required observations, may_errors, effects, config_keys и incomplete reasons. Это сохраняет ошибки/эффекты unused аргументов. Summary тела применим при равных значениях параметров, а не при одном лишь совпадении их типов между исполнениями.

Нет demand-specialization: `f(xs)=size(xs)` при аргументе `read ordered_members` сохраняет зависимость от порядка. Полный union консервативен, а не минимален. Внутри одного анализа возможно повторное использование уже вычисленного тела при том же контексте; persistent incremental cache не реализован.

`LookupBinding(target_id, state, signature_revision, definition_revision)` имеет state `PRESENT`, `EXTERNAL` или `MISSING`. Для MISSING обе revision равны None. `closure` — отсортированное множество **всех транзитивных lookup bindings**, включая вызовы в обеих ветвях и аргументах, и отрицательные lookup misses. Конечный обход closure отделён от обнаружения active recursion, чтобы ранний цикл не скрывал другие определения. `FunctionSummary(function_id, definition_revision, result_type, use, closure, closure_stamp)` содержит автоматически выведенное описание тела.

`registry_stamp` служит provenance всего registry. `semantic_stamp` включает точный entry input, reachable closure, config/provider/requirements и версии профиля/исходников. Добавление корректного unrelated определения меняет registry_stamp, но не обязано менять semantic_stamp. Изменение leaf callee или разрешение прежнего lookup miss изменяет semantic_stamp при неизменном entry AST.

Обычный API не принимает caller-supplied UseSummary и не использует R02 test analyzer hook.

## Проверяемый мост к OBS/R03

`expand(program) → Expansion(context, expanded_ast, bindings)` поддерживает полный resolved acyclic анализ. Missing, external, cycle, opaque/unknown и неподдержанный provider дают `BRIDGE_UNSUPPORTED`. Неполное дерево не подставляется как complete результат.

`ExpansionContext(entry_stamp, registry_stamp, closure_stamp, profile_revision, obs_sha256, laws_sha256, call_engine_sha256)` закрепляет точные входы и checker. `ExpansionBinding(call_path, target_id, definition_revision, parameter_names, temporary_names)` описывает каждое развёрнутое место вызова. `call_path` — provenance исходного места и вложенного тела; это не исполняемый текст.

Для вызова создаются уникальные временные имена, затем nested strict lets в порядке аргументов. Аргументы преобразуются в исходном caller scope до добавления callee в active stack. Тело преобразуется только с отображением его параметров и собственных lexical lets. Все создаваемые binders свежи относительно исходных имён и друг друга. Перемещение, дублирование и удаление вычисления аргумента не разрешены.

`verify_expansion(program, certificate) → VerifiedExpansion(expansion, consumer, summary)` заново валидирует исходную программу, реконструирует единственное детерминированное hygienic expansion и сравнивает **полное** дерево, context и bindings. `consumer` — закрытый OBS Consumer с теми же config/provider/requirements. Затем checker заново получает `obs.infer_use`. Этот structural checker задаёт конечный проверяемый мост; он не является универсальным машинно проверенным доказательством компилятора.

`refined_bridge_use(program, *, expansion=None, derivation=None) → BridgeRefinement(expansion, derivation, summary, saturated)` всегда проверяет expansion, затем вызывает R03 replay/refined_use на закрытой OBS-копии. Присланная derivation привязана к этому точному OBS Consumer. Сохраняются ограничения R03: exact local redexes; нет проталкивания законов через параметры или новых правил substitution.

Ожидаемое свойство для supported DAG: исходный modular use равен `obs.infer_use` проверенного expansion. Независимый direct CALL interpreter/oracle дополнительно сравнивается с OBS execution. Law refinement может дать более узкий use на том же проверенном expansion.

## Оценка изменения

`assess(before, after, before_resource, after_resource) → obs.Assessment`; Program допускает None с одной стороны для добавления/удаления entry. Обе стороны анализируются заново. Incomplete даёт UNKNOWN; изменение entry/callee/signature/closure/config/provider/requirements — RECHECK, если анализ полон. EXCLUDED требует неизменного semantic_stamp и равенства всех необходимых наблюдений на конкретной паре ресурсов.

`assess_refined(before, after, before_resource, after_resource)` сохраняет те же original/closure gates; лишь для неизменных полных входов использует автоматически replay-проверенный bridge и уточнённый use. Эквивалентность изменённых функций/entry в R04 не реализуется, даже если expanded формы случайно равны.

Requirements сохраняют `OPEN`, `REMOVAL_OPEN`, `UNCHANGED_UNASSESSED`. Ни один результат не означает satisfaction, capability или acceptance.

## Полный project rebuild

`extract_project(registry, consumers) → ProjectGraph(registry, consumers, analyses, manifest_stamp)` строит новый полный snapshot. Consumers — iterable или mapping stable_id→Consumer; дубликаты и несовпадение ключа запрещены. Порядок входного iterable несущественен.

`reverse_query(graph, target, *, kind='function') → ReverseResult(target, kind, items, complete, premise_stamp)`. Function-query находит consumers, в closure которых есть target, включая lookup miss. `kind='resource'` поддерживает только `target='authorship'` и находит явных потребителей ресурса. При incomplete analysis результат также incomplete; возможные неизвестные зависимости не превращаются в доказанное отсутствие.

Перед запросом сохранённый ProjectGraph сверяется с полным rebuild из его frozen исходников; поддельные analyses или manifest отвергаются. `premise_stamp` зависит от **всего** project manifest с consumer set и registry, включая пустой ответ. Это полный пересчёт, не заявление эффективности incremental индекса.

`assess_project(old, new, before_resource, after_resource, *, refined=False) → tuple[obs.Assessment,...]` валидирует оба snapshots и рассматривает объединение старых/новых consumer IDs. Удалённый consumer и старый callee edge остаются причиной пересмотра; удаление definition при сохранённом call даёт неполноту, а не потерю вызывающего из результата.

## Пределы и диагностика

Профиль ограничивает registry 64 функциями, функцию 16 параметрами, один Program 4096 AST-узлами source, source JSON 32768 значениями/контейнерами, суммарные исходные строки 1 MiB UTF-8 и глубину JSON/AST пределом OBS 128. Глубина chain вызовов ограничена 32. В project допускается 64 consumers.

Expansion предварительно считает размер/глубину с ранней проверкой верхней границы, до выделения полного дерева. Предел — 8192 AST-узла и JSON-глубина 128. Exponential DAG не разворачивается до превышения памяти: выдаётся `EXPANSION_NODE_LIMIT` или `EXPANSION_DEPTH_LIMIT`. Превышение лимита никогда не считается complete результатом.

Один проход анализа ограничен 65536 посещениями CALL AST-узлов (`ANALYSIS_STEP_LIMIT`). Direct interpreter ограничен 65536 такими посещениями (`EXECUTION_STEP_LIMIT`). Общая вложенность обхода через AST и callee bodies ограничена 128: `ANALYSIS_DEPTH_LIMIT`, `EXECUTION_DEPTH_LIMIT`, а для expansion — `EXPANSION_DEPTH_LIMIT`. Это диагностический отказ исследовательского исполнителя, а не объект runtime error или complete Execution. Он не становится основанием эквивалентности по времени/ресурсам. Итоги семантического сравнения относятся к выбранному исходу при нормальном исполнении в области профиля. Статический call-depth guard проверяет всю достижимую цепочку независимо от memoization summaries.

CALL-ошибки — `CallError(code, path='$', detail='')`, подтип ValueError с явными полями; исходные ошибки `obs.ProfileError` сохраняются отдельно. Основные коды: `SOURCE_LIMIT`, `FUNCTION_LIMIT`, `PARAMETER_LIMIT`, `CALL_DEPTH_LIMIT`, `DUPLICATE_FUNCTION_ID`, `DUPLICATE_PARAMETER`, `CALL_ARITY_MISMATCH`, `CALL_ARGUMENT_TYPE_MISMATCH`, `CALL_RESULT_TYPE_MISMATCH`, `FUNCTION_RETURN_TYPE_MISMATCH`, `BRIDGE_UNSUPPORTED`, `EXPANSION_CONTEXT_MISMATCH`, `EXPANSION_AST_MISMATCH`, `EXPANSION_BINDINGS_MISMATCH`, `PROJECT_GRAPH_MISMATCH`, `SEMANTICS_SOURCE_MISMATCH`.

Окончательные фактические результаты находятся в независимом отчёте. Корпус не доказывает корректность произвольного IR; `bagaev_execution=false`, `research_ast_execution=true`, `hypothesis_tested=false`. T08/T09 не закрываются.
