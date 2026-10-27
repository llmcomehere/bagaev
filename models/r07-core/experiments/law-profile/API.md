# R03 API: локальные законы наблюдений

Это исследовательский слой над замороженным OBS-0.1 из R02. Он преобразует **только вход анализа**. Исполняемый исходный AST, его revision и stable ID не заменяются нормализованной формой. Python 3.10+, standard library. Объекты R02 экспортируются через `laws.engine`, `laws.Consumer`, `laws.ResourceState`; это позволяет использовать одну идентичность классов.

## Закреплённая область

Поддержан ровно профиль `authorship-observation-profile/r02-v1`, исходник R02 engine с SHA256 `9406e4faefd01def24d87f2316f0d21546ea971eb99194771d5ce9eafdca48da` и встроенная привязка `provider/v1`. Другие providers не получают основания локальных законов. Предпосылки взяты из фиксированной семантики движка: ресурс неизменяем, ID уникальны, чтения чисты, все представления возвращают согласованный исход ошибки, `count` — длина исходной последовательности.

Наблюдаемый исход — статус, значение/ошибка, упорядоченная закрытая trace и полнота исполнения OBS. Стоимость CPU, allocation, счётчик чтений и исполнение на произвольном host не входят в этот исход. Изменение выбранных каналов наблюдения требует другого каталога и проверки условий. Сохранение source-структуры или satisfaction произвольного требования не выводится.

R02 проверяет исходный AST и конфигурацию **до** преобразования: signed64 int-литералы, Unicode scalar strings, точные типы, обязательные поля и ограниченная вложенность сохраняются. Нельзя стереть ошибочное выражение переписыванием.

## Каталог

| `rule_id` | Точный исходный узел | Проверенное преобразование |
|---|---|---|
| `SIZE_ORDERED_TO_COUNT` | `size(read ordered_members)` | `read count` |
| `TO_SET_ORDERED_TO_MEMBER_SET` | `to_set(read ordered_members)` | `read member_set` |
| `SIZE_MEMBER_SET_TO_COUNT` | `size(read member_set)` | `read count` |
| `TO_SET_MEMBER_SET_IDENTITY` | `to_set(read member_set)` | `read member_set` |

Третий закон использует уникальность ID. В цепочке `size(to_set(read ordered_members))` это условие требуется на втором шаге. Остальные три закона не выводят уникальность из декларации пользователя. Ни один закон не применяется к `head`, произвольному `to_set(x)` или `size(x)`.

Подстановка разрешена только на месте точного AST-child. Родители, порядок вычислений, initializer `let`, условия и эффекты сохраняются. Генератор обходит детей снизу вверх в порядке грамматики: `let.value/body`, `if.condition/then/else`, операнды слева направо, `items` по индексу, `emit.value/then`. Под `opaque`/`unknown` преобразование не спускается; это ограничение checker, а не доказательство неэквивалентности известных аргументов. Непрозрачный соседний контекст продолжает давать incomplete use.

## Запись derivation

Все записи — frozen dataclasses; вложенные AST глубоко фиксируются. `dataclasses.replace` подходит для отрицательных проверок, но не делает поддельную запись допустимой.

`ProofContext` содержит `stable_id`, `program_revision`, `config_stamp`, `provider_revision`, `requirements_stamp`, `profile_revision`, `semantics_id`, `engine_sha256`, `law_kernel_sha256`, `catalog_revision`, `catalog_sha256`. Это точные входы конкретного исходного потребителя и текущего kernel. Хеши не заменяют проверку шагов.

`RewriteStep(rule_id, path, before, after, guard_stamp)` содержит точный redex и его замену. `path` — tuple ключей/индексов от корня **текущего промежуточного дерева**. Например, `('items', 1, 'value')`. Индексы имеют настоящий тип int; bool не считается индексом. Путь обязан указывать на AST-child, а не на поле литерала, метку эффекта или metadata.

`Derivation(context, original_ast, normalized_ast, steps)` закрепляет исходное и полученное дерево. Поле `normalized_ast` обозначает проверенную преобразованную форму; пользовательская цепочка может быть частичной. Флаг насыщенности не принимается из derivation.

`normalize(consumer) → Derivation` генерирует детерминированную насыщенную цепочку снизу вверх. Каждый закон удаляет один AST-узел. Число шагов ограничено числом узлов исходного конечного дерева; обход ограничен глубиной поддержанного AST.

`replay(consumer, derivation) → VerifiedDerivation(derivation, summary, saturated)` заново проверяет исходный AST/config, все context stamps, исходное дерево и каждый шаг. Для шага checker разрешает path в текущем дереве, сверяет before, самостоятельно применяет фиксированное правило и его guards, сверяет after и заменяет только этот узел. Итоговое дерево сравнивается целиком с заявленным `normalized_ast`; затем заново проверяются тип и use. `saturated` вычисляется checker. Корректная частичная или нулевая цепочка допустима и обычно даёт менее точный use.

`refined_use(consumer, derivation=None) → RefinedUse(summary, derivation, saturated)` при отсутствии записи вызывает normalize; в любом случае затем вызывает replay. Ручной узкий summary входом не является. Обычный R02 `assess_with_test_analyzer` не используется.

## Обычный assessment: source остаётся неизменным

`assess(before, after, before_resource, after_resource, *, before_derivation=None, after_derivation=None) → engine.Assessment` допускает None на одной стороне для добавленного/удалённого потребителя. Предоставленная derivation проверяется перед использованием; ошибка не превращается в EXCLUDED.

Изменение исходного AST, полной config, provider или requirements остаётся `RECHECK`, либо `UNKNOWN` при incomplete use. При неизменных исходных потребителях и поддержанном provider решение использует replay-проверенный refined use. `EXCLUDED` требует равенства всех его наблюдений на конкретной паре состояний. Unsupported provider сохраняет консервативный `RECHECK/UNKNOWN`, без law refinement. `basis='r03_replayed_use'` отличает проверенное сужение от исходного консервативного анализа.

Requirements сохраняют R02-состояния `OPEN`, `REMOVAL_OPEN`, `UNCHANGED_UNASSESSED`; никаких satisfied/accepted этот API не выдаёт.

## Отдельное основание для ограниченной правки кода

`derive_equivalence(before, after, *, before_derivation=None, after_derivation=None) → EquivalenceResult(status, reasons, certificate)` относится к двум Consumer одного stable ID. Статус — `PROVED` либо `UNPROVED`. Требуются одинаковые config/provider/requirements и закреплённая семантика; обе исходные программы валидны, обе цепочки replay-проверены, fresh use полон, полученные формы буквально равны. Разные формы означают только `UNPROVED`.

`EquivalenceCertificate(before_derivation, after_derivation, common_form, observation_domain)` хранит обе исходные привязки и общую проверенную форму. `observation_domain` равен `status/value/error/ordered_trace/completeness:OBS-0.1`. Обе формы могут быть корректными частичными результатами: для достаточного основания нужна их проверенная одинаковость, а не утверждение confluence или каноничности всего языка.

`verify_equivalence(before, after, certificate) → VerifiedEquivalence(certificate, summary, saturated)` независимо повторяет проверку обеих цепочек и общего контекста. `saturated` означает насыщенность обеих цепочек и не усиливает статус требований.

`assess_equivalent_edit(before, after, before_resource, after_resource, *, certificate=None) → engine.Assessment` — **отдельный** API, явно выбирающий дополнительное основание. При проверенной общей форме и равных необходимых ресурсных наблюдениях он может вернуть semantic `EXCLUDED` даже при разных исходных AST; `basis='r03_common_normal_form'` помечает этот путь. Обычный assess такую правку по-прежнему направляет на пересмотр. Источники не сливаются: обе original revisions остаются в certificate.

Если основание не получено, сохраняется исходный `RECHECK/UNKNOWN`; это не доказательство неэквивалентности. Смена config/provider/requirements не обходится общей формой. Новое/усиленное требование остаётся OPEN, предложенная отмена — REMOVAL_OPEN. Эта проверка не принимает программу и не устанавливает base satisfaction.

## Ошибки и область результата

Неверный исходный AST даёт `engine.ProfileError`. Проверка derivation даёт `LawError` с полями `code`, `detail`. Основные коды: `SEMANTICS_SOURCE_MISMATCH`, `UNSUPPORTED_PROFILE`, `UNSUPPORTED_PROVIDER_REVISION`, `PROOF_CONTEXT_MISMATCH`, `ORIGINAL_AST_MISMATCH`, `UNKNOWN_RULE`, `INVALID_REWRITE_PATH`, `STEP_BEFORE_MISMATCH`, `RULE_NOT_APPLICABLE`, `STEP_AFTER_MISMATCH`, `GUARD_STAMP_MISMATCH`, `NORMAL_FORM_MISMATCH`, `TYPE_CHANGED_BY_REWRITE`, `REWRITE_LIMIT`. Для сертификата эквивалентности добавлены `EQUIVALENCE_CONTEXT_MISMATCH`, `INCOMPLETE_EQUIVALENCE`, `COMMON_FORM_MISMATCH`, `OBSERVATION_DOMAIN_MISMATCH`.

Доверенное основание — выбранная семантика фиксированного каталога и корректность checker; это не присланные флаги unique/pure и не машинно доказанная общая теорема. Тесты и независимый oracle подтверждают только объявленный корпус. Runtime программы исполняет original AST; runtime speedup не заявляется. Проектный граф и его incremental извлечение в R03 заново не реализуются.
