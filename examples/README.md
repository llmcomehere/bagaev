# Примеры программ на bagaev

Иллюстративные программы — не тесты. Проверки живут в [conformance/](../conformance/README.md). Синтаксис — [spec/language/](../spec/language/surface.md), шпаргалка — [guide-llm.md](../spec/language/guide-llm.md).

| Каталог | Содержание |
| --- | --- |
| `basics/` | арифметика и FAULT, строки, записи и перечисления, Option и Result с `?`, рекурсивный тип и эффект-переменная, литерал карты |
| `authorship/blog/` | предметная область опыта «один автор → несколько»: люди, статьи и прежняя схема, сущность и контракты авторства, хранилище, права, событие, редактор (`command`), индексатор (`handler`), поиск (`query`), подпись, экспорт, изображения, миграция, тест |

Корень проекта `authorship/`: файл `blog/editor.bag` объявляет `module blog.editor` (SURF-01).

## Что проверено

| Проверка | Как | Статус |
| --- | --- | --- |
| Синтаксис по грамматике | `python3 tools/grammar_lint.py --parse-dir examples` — независимый лексер по lexical.md и распознаватель Earley по grammar.ebnf | все файлы распознаются (входит в `tools/check.py`) |
| `@id`: форма и уникальность (SURF-07) | там же | проходит |
| Имена, типы, эффекты | эталон `bag check examples/basics`, `bag check examples/authorship` ([CHECK-1](../spec/language/checking.md)) | проходит (r28) |
| Канонический формат | эталон `bag fmt --check examples` ([FORMAT-1](../spec/language/format.md)) | проходит (r28) |
| Исполнение | эталон `bag run` / `bag test` | **NOT_RUN**: Ф3–Ф4 |

## Функции std, которых нет в каталоге STDLIB-API-0.1

Примеры используют каталог R24, кроме этих функций. Они входят в stdlib при её встраивании.

| Функция | Почему | Фаза |
| --- | --- | --- |
| `seq.map<T, U, !e>(xs, f) -> Seq<U> uses e`, `seq.fold<T, A, !e>(xs, init, f) -> A uses e` | заменяют `map_pure`/`fold_pure` (D70, CL-115) | Ф3 |
| `result.map_error<T, E, F, !e>(r, f) -> Result<T, F> uses e` | заменяет `map_error_pure` (D70) | Ф3 |
| `json.quote(String) -> String` — строковый литерал BAG-CJSON-1 (CANON-04) | экспорт без ручного экранирования | Ф3 |
| `store.get(t, k) -> Option<V> uses { reads t }`, `store.all(t) -> Map<K, V> uses { reads t }`, `store.put(t, k, v) uses { writes t }`, `store.replace_all(t, m) uses { writes t }` | заменяют STD-052…054 и capabilities (D81, EFF-07) | Ф4 |
| `test.expect(label, Bool)`, `test.expect_equal<T: Eq>(label, a, b)` — FAULT `TEST_ASSERTION` при нарушении | тест — тело типа Unit (SURF-14) | Ф3 |

События — языковая форма `emit` и объявление `handler`; они заменяют STD-055…057 (D81).
