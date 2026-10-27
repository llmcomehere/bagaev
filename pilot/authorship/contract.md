# Общий CLI-контракт опыта авторства

**r35–r37 · Ф7.** Один наблюдаемый интерфейс для вариантов A, B и C ([05-authorship-experiment.md](../../spec/architecture/05-authorship-experiment.md) §5): оракул ([oracle/run.py](oracle/run.py)) и механизм проверяют варианты только через него и не читают исходников. Ожидания — [authorship-fixtures.json](../../registry/data/core/authorship-fixtures.json) и дополнения пилота §6.

## 1. Вызов

```
<cli варианта> <команда> [--параметр значение]…
```

- `<cli варианта>` — из [arms.json](arms.json). Шаблон подставляет каталог приложения `{app}` и каталог состояния `{state}`. Состояние живёт только в `{state}`.
- Ответ — одна строка JSON на stdout. Код выхода 0 для любого обработанного ответа, включая отказ предметной области (`status: rejected`). Отказ стенда — `status: error` с `code`.
- Входные объекты передаются путём к JSON-файлу (`--data`, `--command-file`, `--input`).

## 2. Данные

[data/seed.json](data/seed.json) — исходное состояние D0 фикстуры (`source_old_state`, `people`, `actors`) в нейтральной форме. Дополнение пилота — адрес почты у каждого человека (`alina@blog.test` и т. д.): он нужен скрытому потребителю «уведомления» (§6).

## 3. Жизненный цикл

1. `seed` выполняет **базовая** версия приложения (S0): данные рабочей системы уже существуют до изменения.
2. `migrate` выполняет **кандидат**. Схема не изменилась — `NOOP`.
3. Остальные команды выполняет кандидат.

## 4. Интерфейс приложения варианта C

Адаптер [arms/bagaev_cli.py](arms/bagaev_cli.py) — часть стенда: он вызывает точки входа программы по именам и переводит наблюдения CANON-11 в JSON. Программа обязана сохранять:

| Точка входа | Сигнатура |
| --- | --- |
| `blog.editor.set_authors` (command) | `(actor: String, article: String, author_ids: Seq<String>, expected_revision: Int64) -> Result<Int64, String>`; Err — код §5 |
| `blog.byline.byline_of`, `blog.export.export_of` (query) | `(article: String) -> String` |
| `blog.search.articles_by`, `blog.profile.profile_articles` (query) | `(person: String) -> Seq<String>` |
| `blog.rss.feed` (query) | `() -> String` |
| `blog.view.articles_view`, `blog.view.index_view`, `blog.view.notifications_view` (query) | представления состояния §5 |
| `blog.image.resize_pixels` (query) | `(width, height, pixels: Seq<Seq<Int64>>, to_width, to_height) -> Seq<Seq<Int64>>` |
| событие `AuthorshipChanged` | поле `event_id: String` = `ev_` + ID статьи без `_` + `_r` + ревизия |

`seed` адаптера знает строение S0: он засевает данные базовой версией.

## 4а. Интерфейс приложения вариантов A и B

CLI — часть самого приложения: `src/cli.ts` (TypeScript strict, `node:sqlite`, запуск `node` с удалением типов). Агент может его менять, но обязан сохранить команды и ответы §5. Данные — SQLite в `{state}/state.db`; версия схемы — `meta.schema_version`, изменения — только миграциями (`src/migrations.ts`). Команды, кроме `seed`, `migrate`, `resize`, на устаревшей схеме отвечают `SCHEMA_OUTDATED`. Доступ к таблицам — через объекты репозитория `src/db.ts`; события — `emit` шины `src/bus.ts`, подписки — `src/handlers.ts`. Связи объявлены в JSDoc (`@entity`, `@contract`, `@rule`, `@implements`, `@requires`, `@checks`); варианту B их читает извлекатель, варианту A — только сам агент. Сторонних пакетов нет; проверка типов — установленным компилятором TypeScript 5.9.3.

**Инструменты варианта B** — те же, что у C: протокол агента `bag op` и MCP `bag mcp` (CHANGE-1) над корнем TypeScript-проекта (`meta.language = typescript`, CHG-01а). Граф строит [links-ts/extract.ts](links-ts/extract.ts) в общей схеме; влияние, ContextPack, обязательства, свидетельства (тесты `node --test`) и приёмка — общий движок эталона. Вариант A получает только компилятор, тесты и поиск по тексту.

## 5. Команды

| Команда | Параметры | Ответ |
| --- | --- | --- |
| `seed` | `--data` | `{status: "ok"}` |
| `migrate` | — | `{status: "ok", outcome: "APPLIED" \| "NOOP"}` или `{status: "rejected", code}` |
| `set-authors` | `--command-file` — форма `command_set_authors` фикстуры | `{status: "ok", article_revision, replayed}` или `{status: "rejected", code, replayed}` |
| `deliver-events` | — | `{status: "ok", completed_event_ids}` — события, завершённые всеми обработчиками в этом вызове |
| `redeliver` | `--event` | `{status: "ok", reexecuted}` — повторная доставка завершённого события не исполняет обработчики |
| `byline` | `--article` | `{status: "ok", byline}` |
| `search`, `profile` | `--person` | `{status: "ok", article_ids}` — по возрастанию ID статьи |
| `export` | `--article` | `{status: "ok", export}` — строка JSON (`decoded_export_json` фикстуры) |
| `rss` | — | `{status: "ok", feed}` |
| `notifications` | — | `{status: "ok", notifications: [{key, to, article_id}]}` |
| `resize` | `--input` — `{input, requested_output_size}` (`pure_image_fixture`) | `{status: "ok", output}` |
| `state` | — | `{status: "ok", articles, author_index, outbox_pending_event_ids, inbox_completed_event_ids}` |

**Коды отказа `set-authors`** (проверки по порядку): `NOT_FOUND`, `PERMISSION_DENIED` (право правки — только у редакторов статьи), `STALE_REVISION`, затем правила списка: `EMPTY_AUTHORS`, `DUPLICATE_AUTHOR`, `UNKNOWN_PERSON` после изменения; в S0 — `EXACTLY_ONE_AUTHOR`, `UNKNOWN_PERSON`. Повтор с тем же `idempotency_key` возвращает прежний ответ с `replayed: true` и нового события не создаёт.

Дополнительный контроль O04: из D1 редактор назначает статье `a_101` только `[p_boris]`. После доставки статья имеет ревизию 2; поиск и профиль `p_alina` пусты, поиск `p_boris` содержит обе статьи. Простое добавление новых связей в индекс без удаления прежних не проходит этот контроль.

**Состояние.** `articles` — по возрастанию ID: `{article_id, article_revision, title, author_ids, editor_ids}` (в S0 `author_ids` — список из одного). `author_index` — `{person_id: [article_id]}`, сравнивается как множества. Событие ожидает, пока его не обработали все обработчики; тогда оно — в `inbox_completed_event_ids`.

## 6. Дополнения пилота к фикстуре

Задание агенту о них **не говорит**: это скрытые потребители авторства (план Ф7). Оракул их проверяет.

| Потребитель | Ожидание после C01 |
| --- | --- |
| RSS (`rss`) | элемент статьи содержит `<author>` с именами всех авторов через « · » в порядке атрибуции: a_101 — «Борис Соколов · Алина Петрова» |
| Уведомления (`notifications`) | на событие `ev_a101_r2` — письмо каждому автору: `boris@blog.test`, `alina@blog.test` |

Отвлекающие модули (комментарии, просмотры, карта сайта) авторства статьи не касаются: «автор комментария» — не автор статьи.

## 7. Что проверяет оракул

| Проверка | Обязательства | Случаи |
| --- | --- | --- |
| миграция D0 → D1 (`*-migration-d1`) | O02 | C01 |
| команда, состояние D2 до доставки, повтор команды, D3 после доставки | O01, O04, O07 | C01, C09 |
| замена прежнего автора: A → [B], состояние и поиск после доставки | O03, O04, O07 | C09 |
| подпись, поиск, профиль, экспорт (`decoded_export_json`) | O03, O04, O05 | C01, C04, C05, C09 |
| скрытые потребители: RSS, уведомления | O03 | C01 |
| повторная доставка | O07 | C13 |
| соавтор без права правки | O06 | C03 |
| неверные списки авторов без изменения состояния | O01 | C02 |
| масштабирование без авторов | O08 | C08 |

Оракул проверен на эталонном решении (`reference/<вариант>/`, PASS) и на мутантах ([oracle/mutants.py](oracle/mutants.py)): C04 (экспорт первого автора), C05 (константный экспорт), C09 (индекс не обновлён, только первый автор или сохранён удалённый автор), пропущенные потребители, повторы, право правки от авторства, потеря порядка, миграция без редакторов. Эталонные решения агентам не показываются. Ненулевой exit code, лишний stdout, ответ не-объект или `status: error` нарушают CLI-контракт и не дают PASS даже при правильных отдельных полях JSON.
