# API конечного профиля наблюдений R02

Этот документ описывает исполнимую исследовательскую модель `engine.py`. Это **не синтаксис bagaev и не нормативная спецификация его языка**. Все входы интерпретируются внутри одного закреплённого профиля `authorship-observation-profile/r02-v1`; код провайдеров, произвольные схемы и внешние эффекты модель не исполняет.

## Вход ресурса и наблюдения

`ResourceState(members, read_error=None)` принимает tuple/list уникальных непустых строк AuthorId. Порядок значим; пустая последовательность допустима. Повтор ID отвергается с `DUPLICATE_AUTHOR_ID`. `None` вместо состояния означает недоступный ресурс с ошибкой `MISSING_RESOURCE`. Непустой `read_error` задаёт код ошибки чтения, даже если сохранённые `members` не изменились.

`observe(resource, name) → Observation(status, value, error)` — тотальная функция для допустимого состояния и поддерживаемого имени:

| Имя | Успешное значение | При недоступности или ошибке |
|---|---|---|
| `ordered_members` | tuple ID в исходном порядке | `Observation('error', error=code)` |
| `member_set` | frozenset ID | Та же форма ошибки |
| `count` | число ID | Та же форма ошибки |
| `read_status` | строка `ok` | Успешное значение строки `error:` + code |

`exact_delta(before, after) → ObservationDelta(changed, before, after)` вычисляет все четыре наблюдения и сравнивает их значения, включая статус и код ошибки. `changed` — frozenset имён различающихся наблюдений; `before` и `after` — неизменяемые отображения имён в `Observation`. Это точный результат **для данной пары конечных состояний данного профиля**. Наблюдения связаны функциями над одним ресурсом: количество не становится произвольной независимой координатой, а множество не теряет свою связь с упорядоченной последовательностью.

## Закрытый JSON AST

Каждый узел — объект с полем `op`. В таблице перечислены остальные допустимые поля; неизвестное поле — ошибка, а не игнорируемая декларация. Программы не содержат ручных `dependencies`, сертификатов полноты или обещаний потребителя.

| `op` | Поля | Тип и вычисление |
|---|---|---|
| `const` | `value` | Только bool, int, string или null; тип соответственно `bool`, `int`, `string`, `unit` |
| `read` | `view` | Одно из четырёх имён выше; первые три чтения возвращают значение либо завершаются ошибкой ресурса |
| `var` | `name` | Значение лексической переменной; несвязанное имя отвергается |
| `config` | `key` | bool из точной compile-config; отсутствующий ключ отвергается |
| `let` | `name`, `value`, `body` | Сначала вычисляется initializer; затем body с новой привязкой; затенение разрешено |
| `if` | `condition`, `then`, `else` | Условие bool; типы ветвей совпадают; исполняется одна выбранная ветвь |
| `contains` | `collection`, `item` | Последовательность/множество ID и string → bool |
| `size` | `value` | Аналог `len`: последовательность/множество ID → int |
| `to_set` | `value` | Последовательность/множество ID → множество ID |
| `head` | `value` | Упорядоченные ID → string; пустой вход даёт `EMPTY_HEAD` |
| `eq` | `left`, `right` | Два значения одного типа → bool; множества сравниваются как множества, последовательности как последовательности |
| `pair` | `left`, `right` | Кортеж из двух значений с соответствующими типами |
| `tuple` | `items` | Кортеж значений; пустой кортеж допустим и отличается от `unit` |
| `seq` | `items` | Непустая последовательность выражений; возвращает последнее значение |
| `emit` | `label`, `value`, необязательное `then` | После успешного вычисления value добавляет событие в trace; затем вычисляет continuation либо возвращает unit |
| `fail` | `code`, `type` | Известное завершение ошибкой; type задаёт тип несуществующего нормального результата |
| `opaque` | `name`, `type`, необязательные `kind`, `args` | kind = `external` по умолчанию либо `hidden_read`; аргументы вычисляются слева направо, затем явный unknown |
| `unknown` | `type`, необязательное `reason` | Явный runtime unknown без угадывания значения |

В `fail`, `opaque`, `unknown` аннотация `type` — строка `bool`, `int`, `string`, `unit`, `ordered_members`, `member_set` либо объект `{"tuple": [type, ...]}`. Типизированные литералы коллекций не поддержаны: коллекции поступают из ресурса или `to_set`. Int-литералы ограничены signed 64-bit: от `-2**63` до `2**63-1`; float не входит в профиль. Все входные строки содержат только Unicode scalar values; отдельные surrogate code points `U+D800…U+DFFF` отвергаются. Ограничения распространяются также на ID, ключи конфигурации и metadata. Нарушения дают `INTEGER_OUT_OF_RANGE` и `INVALID_UNICODE_SCALAR`, до канонического hash и исполнения.

`validate_program(ast, config=None) → Type(name, args)` проверяет **все** подтермы и типы, включая недостижимую ветвь. Config — mapping непустых строк в настоящий bool; `0`, `1`, строки и отсутствующие ключи не превращаются в логические значения. У `eq` типы `bool` и `int` различаются. Верхняя граница вложенности AST/аннотаций — 128; превышение имеет явную диагностику.

Неизвестные операции, поля, виды ресурса и типы вызывают `ProfileError`; поля исключения: `code`, `path`, `detail`. Основные коды: `UNSUPPORTED_AST_OPERATION`, `UNKNOWN_AST_FIELD`, `MISSING_AST_FIELD`, `UNSUPPORTED_RESOURCE_VIEW`, `UNSUPPORTED_TYPE`, `TYPE_MISMATCH`, `UNBOUND_VARIABLE`, `INVALID_COMPILE_CONFIG`, `MISSING_COMPILE_CONFIG`, `AST_DEPTH_LIMIT`, `TYPE_DEPTH_LIMIT`. Это ошибки входной программы, а не её runtime-результат.

## Исполнение и автоматический use

`execute(ast, resource, config=None) → Execution` сначала проверяет типы. `Execution` содержит:

- `status`: `ok`, `error` или `unknown`;
- `value`: нормальное значение, иначе null;
- `error`: код известной runtime-ошибки, иначе null;
- `trace`: tuple из `Effect(label, value)` в порядке выполнения;
- `complete`: true для известного нормального либо ошибочного завершения, false для unknown;
- `unknown_reason`: причина unknown либо null.

Все операнды вычисляются слева направо. Ошибка или unknown прерывает текущую последовательность. Trace сохраняет уже выполненные события; при unknown это только известный префикс, не полная внешняя история. `emit` не отправляет данные за пределы процесса. `opaque` не выполняет внешний код. Значения последовательностей и кортежей — tuple, множеств — frozenset. `to_data(value)` преобразует dataclasses и значения в JSON-совместимую форму; множество получает тег `{"$set": [...]}`.

`infer_use(ast, config=None) → UseSummary` получает зависимости из того же закрытого AST, без запуска на конкретном состоянии. Поля:

| Поле | Значение |
|---|---|
| `required_observations` | frozenset необходимых имён наблюдений |
| `complete` | Полнота вывода в этом профиле |
| `may_errors` | Возможные коды ошибок, `RESOURCE_READ_ERROR` либо `*` |
| `effects` | Статические метки emit либо `*` |
| `config_keys` | Прочитанные ключи закреплённой конфигурации |
| `reasons` | tuple причин неполноты |

Чтение `ordered_members`, `member_set`, `count` добавляет соответствующее наблюдение **и `read_status`**. Чтение статуса добавляет только `read_status`. Все составные узлы объединяют use всех детей: initializer `let`, условие и обе ветви `if`, аргументы, payload/continuation `emit`, все члены `seq`. `head` дополнительно учитывает `EMPTY_HEAD`; `fail` — свой код. `opaque` и `unknown` делают результат неполным; внешний/скрытый код также имеет неизвестные ошибки и эффекты.

В R02 нет оптимизирующих сужений. `size(read ordered_members)` сохраняет потребность в порядке; `to_set(read ordered_members)` тоже. Более узкий `read count` — отдельный builtin с собственной семантикой. Неиспользованная переменная не позволяет удалить чтение, ошибку или эффект initializer. Сам `var` не добавляет наблюдений: в закрытом eager `let` вся зависимость уже включена через initializer; рассуждение о теле опирается на равенство значений в лексическом окружении.

## Потребитель и решение о пересмотре

`Consumer(stable_id, program, compile_config={}, provider_revision='provider/v1', requirements={}, alias='')` копирует и замораживает входы. `stable_id` — идентичность потребителя; `program_revision` — SHA256 канонического AST. `input_stamp` закрепляет ID, AST, всю compile-config, revision провайдера, opaque требования и revision профиля. Alias не отражается программой и не участвует в семантическом stamp. Requirements — mapping `requirement_id → revision`; изменение текста требования должно дать новую revision.

`assess(before, after, before_resource, after_resource) → Assessment`; один из before/after может быть None для добавленного/удалённого потребителя. Два присутствующих потребителя обязаны иметь одинаковый stable_id. Поля результата: `consumer_id`, `decision`, `reasons`, `changed_observations`, `required_observations`, `requirements`, `basis`.

- `EXCLUDED`: AST, вся config, provider revision и requirements неизменны; автоматический use полон; все требуемые наблюдения равны. Это сохранение исхода в данном сравнении, включая возможную ошибку и trace, а не успешность программы.
- `RECHECK`: потребитель добавлен/удалён, изменён один из закреплённых входов либо изменилось требуемое наблюдение.
- `UNKNOWN`: хотя бы один use неполон. Это TOP, запрещающий исключение, даже если конкретный запуск случайно завершился известным результатом.

Причины содержат точные revisions или хеши изменённых входов. `requirements` — tuple `RequirementReview(requirement_id, status, before_revision, after_revision)`. Новое/изменённое требование всегда `OPEN`; прежнее — `UNCHANGED_UNASSESSED`; удалённое — `REMOVAL_OPEN` с отдельной причиной `REQUIREMENT_REMOVAL_OPEN`. Удаление требует пересмотра и не означает принятую отмену требования. Состояния satisfaction этот API не выдаёт.

Провайдер — закреплённая предпосылка наблюдений, не загружаемый исполняемый модуль. Его изменение принудительно даёт пересмотр даже при равных данных. Произвольная миграция схемы находится вне типа `ResourceState` и не может быть признана невлияющей на основании этого delta; нужен новый профиль/провайдер и отдельная проверка.

Обычный `assess` не принимает чужой summary. Только `assess_with_test_analyzer(..., infer_fn=...)` позволяет внедрить намеренно плохой анализ для мутационных проверок; его результат явно помечен `basis='TEST_ONLY_UNTRUSTED'` и не является обычным свидетельством.

## Registry, граф и обновление

`extract_project(project) → ProjectGraph` принимает mapping `stable_id → Consumer` либо конечный iterable потребителей. Несовпадающие ID и дубли отвергаются. Весь registry, включая текущих непотребителей, входит в `manifest_stamp`; generation производна от manifest и revision извлекателя.

`ProjectGraph` содержит `manifest_stamp`, `generation`, `consumers`, `summaries`, `edges`, `unknown_consumers`, `extractor_revision`, `reused`, `reextracted`. `summaries` — tuple пар `(id, UseSummary)`. `Edge(source, target, observation)` автоматически возникает для каждого необходимого наблюдения; target известного ресурса — `authorship`. Неполный summary дополнительно создаёт `target=None, observation='TOP'`.

`incremental_extract(previous, project)` сначала проверяет прежний граф полным повторным выводом, затем повторно использует summary только при точном равенстве `input_stamp`. Новый manifest всегда охватывает **весь** новый registry. Это исследовательская проверка корректности повторного использования, без обещания ускорения. `graph_content(graph)` исключает только счётчики работы `reused/reextracted`, позволяя сравнить результат с полным извлечением.

`validate_graph(graph)` сравнивает реальное содержание с повторно выведенным графом, а не доверяет его stamp. Ошибки: `GRAPH_CONTENT_MISMATCH`, `EXTRACTOR_REVISION_MISMATCH`. `reverse_query(graph, target='authorship') → ReverseResult(consumers, complete, manifest_stamp)` возвращает известных и возможных потребителей; неизвестная цель делает complete=false. Полнота относится только к данному замкнутому registry.

`graph_delta(old, new) → GraphDelta(added, removed, union, old_generation, new_generation)` сохраняет снятые старые рёбра. `assess_project(old, new, before_resource, after_resource)` возвращает tuple решений для **объединения старых и новых ID**, включая удалённых потребителей и прежних непотребителей с новым телом. Исторические согласованные графы можно использовать одновременно; появление нового manifest не изменяет старый объект.
