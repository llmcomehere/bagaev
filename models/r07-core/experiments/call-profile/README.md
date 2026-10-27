# R04 · Композиция summaries статических функций

CALL-0.1 добавляет к исследовательскому OBS-0.1 типизированные функции, строгие вызовы и транзитивные зависимости от точных определений. Это исполнимый Python-профиль для проверки одного механизма. Полный язык bagaev, его компилятор и runtime здесь не исполняются.

Точный контракт записей, конструкторов и диагностик — в [API.md](API.md). Модуль [engine.py](engine.py) импортирует закреплённые исходники [OBS](../observation-profile/engine.py) и [R03](../law-profile/laws.py); их байты не изменены.

## Что реализовано

У Function есть stable ID, уникальные typed params, результат и тело; у Program — entry Consumer и immutable registry. Call содержит exact target, arguments и обязательную result annotation. Аргументы вычисляются один раз слева направо, затем создаётся свежее окружение параметров. Переменные caller не становятся свободными переменными функции.

Автоматический анализ объединяет use всех аргументов и callee body, включая ошибки, эффекты, config keys и неполноту. Неиспользованный параметр не разрешает удалить ошибку или emit его аргумента. Обе ветви анализируются. Missing/external/cycle/opaque остаются неполными даже при фактически невыбранной ветви. Static nested `f(f(x))` не считается рекурсией: внешний target добавляется в active stack после аргументов.

Closure хранит все транзитивные exact definition/signature bindings и lookup misses. Поэтому правка листа цепочки `entry → f → g → h` меняет semantic input при неизменном entry AST; разрешение прежнего отсутствующего target тоже требует нового анализа. Корректная unrelated функция не добавляет наблюдений достижимому потребителю.

Это консервативный modular union. Например, `f(xs) = size(xs)` при `f(read ordered_members)` продолжает требовать порядок: анализа потребности параметра и специализации по текущим аргументам нет.

## Отдельный проверяемый мост

Для полного resolved DAG строится bounded hygienic expansion в закрытый OBS AST. Временные имена свежи; каждый аргумент становится отдельным strict let, а тело получает только parameter bindings. Source lets alpha-renamed с сохранением lexical scope. Исходная CALL-программа при этом сохраняется.

`verify_expansion` заново реконструирует детерминированное дерево из source registry/entry, сверяет точный context, полное дерево и bindings. Присланный use не принимается. Затем выполняется frozen OBS typecheck/inference; исходный modular use должен совпасть с use проверенного expansion.

На этом закрытом дереве можно отдельно применить replay R03. Например, zero-argument тело `size(read ordered_members)` получает локальное основание зависимости только от `count` и `read_status`. Закон не проталкивается через `size(var parameter)`, strict let или произвольный effectful код.

Привязка expansion включает полный registry manifest. Поэтому прежняя запись после даже unrelated registry edit отвергается как stale; свежая модульная оценка всё ещё может показать неизменную reachable closure. Это разные области применимости, а не принятие устаревшего certificate.

Обычный `assess` сравнивает entry, транзитивную closure, config, provider и требования. `assess_refined` сохраняет эти же gates и лишь для неизменных полных входов использует проверенный bridge/R03. Изменённые функции не получают автоматическую эквивалентность из случайно одинакового expansion. Новые требования остаются OPEN, отменённые — REMOVAL_OPEN; semantic EXCLUDED не означает acceptance или satisfaction.

## Project snapshots

`extract_project` выполняет полный пересчёт всех consumers. Reverse query перед использованием сверяет snapshot с новым полным rebuild. Его premise включает весь consumer set и registry, в том числе при пустом ответе. Подмена сохранённого analysis или manifest диагностируется.

`assess_project` использует объединение старых и новых IDs. Добавленный consumer, прежний nonconsumer с новым вызовом, удалённый consumer и удалённое callee definition не исчезают из рассмотрения. Исторические snapshots остаются самостоятельными входами; поколения не смешиваются. Persistent incremental cache и ускорение project-query не заявляются.

## Запуск независимой проверки

Из корня комплекта R04:

```bash
python -B experiments/call-profile/verify.py --output results/call-profile/report.json
```

Отдельный [oracle.py](oracle.py) исполняет CALL AST собственными правилами и не импортирует engine, laws или lowering. Verifier использует authored outcomes, проверяет прямое исполнение, композицию, strict-let bridge, исходный и уточнённый assessment, stale/forged evidence и full rebuild snapshots. Намеренно неверные варианты должны давать различимые нарушения: потеря strict аргумента, дублирование effectful аргумента и игнорирование транзитивной версии.

Фактические количества и source hashes находятся в [отчёте](../../results/call-profile/report.json). Число тестов не является метрикой производительности или полезности всего языка. Документация не подставляет ожидаемые результаты вместо выполненного прогона.

## Пределы вывода

Поддержаны один immutable ресурс, одна закреплённая config, `provider/v1`, конечный source и статические targets. Registry ограничен 64 функциями, функция 16 параметрами, source Program 4096 AST-узлами, глубина вызовов 32. Expansion проверяет предел 8192 AST-узла и JSON-глубину 128 **до** allocation полного дерева. Другие ограничения входа перечислены в API.

Анализ и direct interpreter ограничены каждый 65536 посещениями CALL AST-узлов; общая вложенность обхода через AST и callee bodies — 128. `ANALYSIS_STEP_LIMIT`, `EXECUTION_STEP_LIMIT`, `ANALYSIS_DEPTH_LIMIT`, `EXECUTION_DEPTH_LIMIT` и `EXPANSION_DEPTH_LIMIT` — явные диагностические отказы исследовательского инструмента, а не частичное успешное исполнение или модельная ошибка программы. Они не дают evidence эквивалентности по времени, памяти или бюджету. Такие каналы отсутствуют в выбранной OBS-семантике; сравнение подразумевает нормальное исполнение в указанной области.

Обоснование strict-call composition и hygiene — аргумент по структуре AST и независимый конечный корпус. Structural checker проверяет конкретное преобразование, но не является machine-checked универсальным доказательством. Нет рекурсивных summaries, interprocedural demand analysis, живого provider, alias/reflection, асинхронности, миграций или интеграции с приёмкой bagaev.

`bagaev_execution=false`, `research_ast_execution=true`, `hypothesis_tested=false`. T08/T09 остаются открытыми. Следующий содержательный шаг требует собственных семантических решений; его нельзя считать реализованным наличием этого профиля.
