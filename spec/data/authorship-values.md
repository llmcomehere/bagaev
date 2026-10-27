# AUTH-DATA-0.1 — чистые данные авторства и обратный индекс

**R07 · WORKING_DESIGN.** Предметный мост строится из ordinary [DATA jobs](../../models/r07-core/experiments/data-core/API.md). Исполнимая orchestration: [authorship_bridge.py](../../models/r07-core/experiments/data-core/authorship_bridge.py). У неё нет imports engine/oracle: caller передаёт runner; тот же набор requests может исполняться двумя независимыми реализациями. Python coordinator не является source program bagaev. Durable операции [AUTH-TX](authorship-transition.md), migration/activation, ACL и реальный T15 этим опытом не исполняются.

## 1. Exact пример schema

В registry опыта зарегистрированы четыре nominal type entities revision1:

```text
PersonId      { value: String }
ArticleId     { value: String }
LegacyArticle { id: ArticleId, author: PersonId }
Article       { id: ArticleId, author_ids: Seq<PersonId> }
```

PersonId и ArticleId различны независимо от совпадения String payload. Внешнее читаемое представление использует strings для удобства fixtures; каждый такой input превращается в nominal value обычным record job. Названия и revision относятся к этому эксперименту, не объявляются актуальными DB schema IDs существующего bagaev.

Input: конечный явный universe людей и конечная последовательность статей. Для статьи допускается ровно одна форма: `article_id + author_ids` либо `article_id + author_id`. Обе одновременно/неизвестные поля недопустимы. ID — непустая последовательность до128 scalar values; без normalization/locale folding. Предел fixture harness: ≤32 people, ≤32 articles, ≤16 authors на статью. Bound не является новым ограничением языка V1.

## 2. Policy и порядок отказов

1. Сначала полностью проверить input shape/пределы: `InputRejected(INVALID_BRIDGE_INPUT)` без запуска jobs.
2. Построить PersonId values и Map<PersonId,Unit>; duplicate → `Rejected(DUPLICATE_PERSON)`.
3. Преобразовать все статьи в typed Article; LegacyArticle.author проходит field→singleton sequence→новый record. Построить Map<ArticleId,Article>; duplicate ID → `Rejected(DUPLICATE_ARTICLE)`.
4. Затем проверять каждую статью в **исходном input order**, отдельно от canonical article map order:
   - length(author_ids)=0 → EMPTY_AUTHORS;
   - map_build author membership set → первый DUPLICATE_AUTHOR с exact pair positions;
   - для каждого author в исходном порядке map_get в people map; None → UNKNOWN_PERSON с article/author indices.
5. Только после всех успешных проверок строить полный обратный индекс.

Так заданы неоднозначные сочетания: duplicate article имеет приоритет перед empty authors; внутри одной статьи duplicate authors имеет приоритет перед unknown person. Shape/type correctness отдельно от domain validity: nominal Article с пустым Seq<PersonId> является типизированным значением, но не проходит этот предметный policy. Наличие typed value не заменяет validation.

Отказ не публикует accepted snapshot/index. Уже выполненные чистые jobs могут присутствовать в диагностическом отчёте; это не committed store state. Budget/implementation stop любого job даёт `JobStopped` и не маскируется предметным Rejected.

## 3. Полное построение индекса

```text
people_map := unique typed map of all supplied people
articles_map := unique typed map of all validated typed articles
for person in canonical people_map order:
    article_ids := empty Seq<ArticleId>
    for article in canonical articles_map order:
        authors := field(article, author_ids)
        membership := unique map of each author to Unit
        if map_get(membership, person) is Some:
            article_ids := seq_append(article_ids, field(article,id))
    index_entries.append(person, article_ids)
index := map_build(index_entries)
```

Внешние циклы и branching реализованы Python coordinator; type/constructor/selector/comparison/map/codec work выполнен public DATA jobs. Просмотр готового JSON-result, выбор последующего request и переход между jobs находятся вне runtime steps. Каждый job получает собственный budget65536. Это не сквозной budget программы, не folded loop implementation V1 и не performance benchmark.

Выбран full rebuild для конечного supplied universe, а не incremental update. Индекс включает каждого supplied person, в том числе `[]` для человека без статей. ArticleIds внутри index values отсортированы по Key order, поскольку обход article map канонический. Authors внутри Article **не сортируются**: их исходный порядок остаётся существенным.

## 4. Инварианты результата

Для каждого supplied person p и принятой статьи a:

```text
p in a.author_ids   iff   a.id in index[p]
```

Каждая index list содержит unique ArticleId и расположена в их Key order. Каждый author относится к supplied people universe. Каждый ArticleId уникален. Каждая author list непуста и без повторов. Входной ordered authors list сохраняется полностью; при legacy conversion результат содержит ровно прежнего single author.

Эти утверждения относятся к полному **переданному fixture**, не к неизвестной части live project. Пропущенная из input статья не превращается в доказательство отсутствия связи в реальной базе. Future knowledge provider обязан прикрепить coverage/universe binding, иначе full rebuild локального списка можно ошибочно выдать за полный проектный индекс.

## 5. Codec boundary и receipts

Оба final values — articles map и index — последовательно проходят encode, decode в exact том же registry/type и equal с исходным value. Returned Bytes сохраняются в результате; decode roundtrip должен сохранить nominal identities, ordered authors и canonical index. Source ID каждого job включает роль и порядковый номер; каждый receipt содержит exact raw request и полную execution observation.

Job receipts не являются криптографической подписью, capability или правом на фиксацию состояния. Будущий durable adapter обязан самостоятельно проверять policy на exact candidate/state version либо проверять связанное доверенное evidence по отдельному протоколу. Этот bridge не выполняет store reads/writes, transactions, receipts AUTH-TX, outbox/inbox, recovery или activation.

## 6. Независимые ожидаемые данные

Основной authored fixture:

- люди: p_alina, p_boris, p_vera;
- a_101: [p_boris,p_alina]; a_102: [p_boris];
- index: p_alina→[a_101], p_boris→[a_101,a_102], p_vera→[].

Обратный индекс не должен менять порядок [p_boris,p_alina] в a_101. Дополнительные обязательные cases: empty authors, duplicate author, unknown person, duplicate article, legacy singleton preservation и пустой supplied universe. Case roster/ожидаемые observations и фактическое исполнение принадлежат [fixtures](../../models/r07-core/fixtures/data-core.json) и [report](../../models/r07-core/results/data-core/report.json); описание плана не означает PASS.

Whole pipeline сравнивается через два independent DATA runners и отдельно с authored domain view. Общий coordinator может содержать общую ошибку; authored expected values/priority failures нужны именно для её обнаружения. Совпадение двух runners не доказывает сам policy для всех возможных inputs.

## 7. Путь к реализации на языке

До переноса coordinator в bagaev нужны единая CORE+DATA машина, DataPrim bridge без budget reset, обычные loops/folds через recursion, primitive для canonical map entries и exact source/type elaboration. После этого тот же policy выражается обычными функциями, а её output идёт в отдельный guarded durable ChangeContract. Этот путь явно остаётся в roadmap; standalone jobs не выдаются за уже написанное приложение bagaev.
