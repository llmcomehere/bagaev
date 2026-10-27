# DATA-TYPES-0.1 — неизменяемые данные V1

**R07 · WORKING_DESIGN.** Этот документ раскрывает обязательные data forms из [V1](../profiles/v1.md) и [TYPES](types.md). Это общий проект: исследовательский DATA исполняет отдельные операции над уже готовыми значениями, а не полный исходный язык. Точные JSON-формы, конечные лимиты и исполняемые операции задаёт [API DATA](../../models/r07-core/experiments/data-core/API.md). CORE R06 и его результаты не изменены. **r26:** рекурсивные пользовательские типы включены (D69), Float и BigInt исключены из V1 с `UNSUPPORTED_FEATURE` (D71); 

## 1. Типовая идентичность и неизменяемость

Значение имеет один monotype. Типы Bool, Int64, Unit, String, Bytes, Seq<T>, Map<K,V>, Option<T>, Result<T,E>, nominal record/sum и Fn определяются по [TYPES](types.md). Нет автоматической конверсии Bool→Int64, Bytes→String, record→record по похожим полям или ArticleId→PersonId. Значения неизменяемы; обновление возвращает новое значение и не меняет старое наблюдение. Физическое sharing допускается, когда не меняет семантическое равенство, порядок и lifetime.

Nominal instance задаётся `(TypeEntityRef, ordered type arguments)`, где TypeEntityRef закрепляет exact entity и revision из snapshot. Имя для отображения не определяет тип. Два nominal types с одинаковой раскладкой различны. Замена revision также не выполняется автоматически: миграция имеет явный source/target type и отдельные доказательства.

Registry закрепляет body каждой декларации: kind, ordered parameters/bounds, ordered fields или tags с payload types. Один exact ref не может иметь два body в одном snapshot. Содержимое registry включается в snapshot binding; совпадение произвольного revision label не заменяет проверку содержимого.

Поле и tag имеют устойчивый ID; имя и позиция отдельно. Declaration order влияет на канонический обход record, сравнение composite key и порядок tags суммы. Поэтому перестановка деклараций может быть семантической правкой даже при сохранённых названиях. Type/field/tag changes входят в прямые зависимости программы и требуют обновления обратного индекса.

## 2. Проверка declaration registry

Порядок проверки фиксируется для данного frontend/profile; диагностика содержит exact ref и путь к ошибке. Проверка не исполняет выражения программы.

1. Проверить конечную структуру, известные schema tags, непустые допустимые ID, уникальность refs и parameter/field/tag IDs. Record допускает ноль полей; sum требует хотя бы один tag. Повтор не перезаписывается host dictionary.
2. Для каждого type expression проверить constructor kind/arity, существование nominal ref, lexical доступность параметров и отсутствие forall в monotype. Unknown nominal ref — `UnknownType`; неверная arity — `TypeArityMismatch`.
3. Построить dependency graph nominal declarations по всем type positions, включая Fn annotations и аргументы конструкторов. Циклы допустимы при регулярной рекурсии (D69); нерегулярная → `IRREGULAR_RECURSIVE_TYPE`. Исследовательский DATA-0.1 сохраняет своё прежнее требование DAG и код `PENDING_RECURSIVE_DATA` — это ограничение его профиля, не правило V1.
4. Проверить bounds при каждой instantiation. Проверять structural predicates по алгоритму §5. No defaulting: отсутствующий type argument должен быть определён source inference до появления accepted typed IR.
5. Создать неизменяемый registry с exact content binding. Запуск не читает новый accepted head и не подменяет registry текущими одноимёнными объявлениями.

Проверка DAG конечна по числу деклараций и рёбер; проверка instantiated fields также ограничена явными compiler limits. Ацикличность деклараций не обещает маленького unfolded type: repeated products могут расти, поэтому полная развёртка не является реализационным алгоритмом. Использовать memoized type nodes и явный лимит работы; отказ защиты — отдельный `ImplementationLimit`, не отрицательное заключение о типе.

## 3. Record, sum, Option и Result

Record содержит ровно объявленные поля. В исходном конструкторе каждый field ID встречается один раз; неизвестное, пропущенное или повторное поле — prelaunch diagnostic. Инициализаторы выполняются в исходном порядке, после чего значения раскладываются по declaration order. Сортировать выражения до вычисления нельзя. Field(receiver, field_id) сначала вычисляет receiver; чтение поля не вызывает пользовательский getter и не имеет скрытых эффектов.

Sum value содержит exact instantiated sum type, tag и один payload требуемого типа. Для варианта без содержательных полей payload=Unit; отсутствие payload не является неявным Unit. Option и Result — закрытые предопределённые суммы `None | Some(T)` и `Ok(T) | Err(E)` с порядком тегов None=0, Some=1, Ok=0, Err=1 (D79; так же в DATA API, STDLIB-TYPES-0.1 и WIRE-FFI-0.1). Порядок tags исследовательских/исторических API не переносится на другую revision по имени.

`None` или `Err(e)` не позволяют восстановить отсутствующий type parameter из actual payload. Нужен expected type либо явные type arguments. `Result.Err` — обычное значение, не exception/unwind. Обработка раннего отказа выполняется явным Match/Call или отдельно специфицированным source lowering.

Match использует exact tag coverage из TYPES: неизвестные, повторные и отсутствующие ветви отвергаются до launch; все branch types проверяются. Во время исполнения вычисляется только выбранная ветвь с отдельным lexical payload binding. Внешний недопустимый tag обрабатывается decoder как ошибка входа; такой tag в уже принятом внутреннем значении означает нарушение реализации.

## 4. Seq и Map

Seq<T> — конечная упорядоченная последовательность. Длина, порядок и повторения существенны. Пустая последовательность имеет определённый T; сама пустота не выбирает тип. Источником T служит annotation/expected context, затем pending constraints финализируются на границах TYPES. Индекс — неотрицательный Int64; выход за диапазон даёт определённый Option/Result API, не host exception. Размеры, не представимые Int64, запрещены до образования значения соответствующим resource contract.

Map<K,V> допускает только `Key(K)`. Его абстрактное значение — конечное множество пар с уникальными ключами. Внутреннее наблюдаемое представление и обход упорядочены семантическим `compare_K`, независимо от hash seed, расположения bucket и source insertion order. Равные карты имеют одинаковый канонический порядок. `Map` не является Key в этой редакции; Eq и Persistable определяются по §5.

### Две отдельные фазы MapBuild

```text
for each source pair in source order:
    evaluate key expression
    evaluate value expression
    append completed pair to immutable operand sequence
only after all operands complete:
    build ordered map by the profile's explicit work machine
    if any duplicate: return Err(DuplicateKey)
    else: return Ok(map)
```

Следовательно, более ранний повтор ключа не позволяет пропустить более поздний initializer. Если поздний initializer расходится, исчерпывает бюджет или производит разрешённый эффект, это предшествует результату duplicate checking. DATA-0.1 принимает уже готовые пары и проверяет только вторую фазу; source order/effects этим опытом не подтверждены.

При нескольких повторах возвращается первая повторная позиция во входной последовательности; для неё — первая предшествующая равная позиция. Это определение не зависит от алгоритма сортировки. Diagnostic payload содержит исходные позиции. Ключ допускается только если это явно предусмотрено exact error type; fixed DATA error ключ не содержит. Точный result type формы MapBuild — `Result<Map<K,V>,DataError>`, а `DuplicateKey` является значением code, не отдельным типом (D79; так же TYPES-0.1 §7). Литерал `Map {…}` исходника превращает повтор в Fault `DUPLICATE_KEY` (SURF-30); проверяемая форма — `std.map.build`. Другой error representation потребует отдельной signature/revision; они не смешиваются по имени ошибки.

Канонический порядок **не равен автоматически лексикографическому порядку bytes codec**. Например, signed Int64 сравнивается математически; two's-complement encoding отрицательных чисел может иметь другой byte order. Codec maps должны использовать semantic Key order данного schema revision.

## 5. Eq, Key, Persistable: алгоритм по типу

Это встроенные структурные predicates; пользователь не может подменить их кодом, dynamic dispatch или случайным hash.

| Тип | Eq | Key | Persistable |
| --- | --- | --- | --- |
| Bool / Int64 / Unit / String / Bytes | true | true | true |
| Seq<T> | Eq(T) | Key(T) | Persistable(T) |
| Map<K,V> | Key(K) ∧ Eq(V) | false | Key(K) ∧ Persistable(K) ∧ Persistable(V) |
| Nominal record | conjunction instantiated fields | conjunction instantiated fields | registered exact codec ∧ conjunction instantiated fields |
| Nominal sum / Option / Result | conjunction всех instantiated payload types | conjunction всех instantiated payload types | registered exact codec ∧ conjunction всех instantiated payload types |
| Fn / Capability / HostHandle | false | false | false |
| Rigid A | stated Eq or Key bound | stated Key bound | stated Persistable bound |

`Key(T)` влечёт `Eq(T)`. `Persistable(T)` не означает полномочие сохранить значение. Предикат проверяется по всему типу, а не только по выбранной ветви или непустым элементам. Поэтому `Option<Fn>.None`, пустой `Seq<Fn>` и пустой `Map<String,Fn>` не проходят соответствующее Persistable/Eq правило.

При nominal instantiation аргументы подставляются в **поля**, затем выполняется обход. Неиспользуемый phantom parameter не становится скрытым полем: `Phantom<Fn>{}` может быть Persistable/Eq/Key при зарегистрированной схеме без данных Fn. Exact Fn type descriptor всё равно входит в идентичность instance и должен быть кодируемой метаинформацией. Это сериализация описания типа, не function value, code pointer, capture или authority. `Phantom<Fn>{}` и `Phantom<Int64>{}` не равны как типы.

```text
predicate(P, T, registry, memo):
    normalize exact aliases; check well-formed ground type / allowed rigid bound
    if memo contains (registry_binding,P,T): return it
    for primitive / Fn / Handle / rigid: return closed table result
    for nominal: instantiate declaration fields/payloads by TypeParamId
    for containers: apply their exact predicate dependencies
    evaluate dependencies using explicit work stack and compiler limits
    cache result for exact (registry_binding,P,T)
```

Одинаковый type name в другой registry не использует старый memo. Все branches суммы учитываются. Codec registration — наличие exact supported codec contract, не произвольного пользовательского executable encoder. В DATA только поддерживаемые данные имеют runtime values; возможность описать Fn как phantom argument не означает поддержку исполнения функций в DATA.

## 6. Полный порядок Key

Сравнивать можно только значения одного exact Key type. Результат — Less/Equal/Greater (или exact signed comparator API), без неявного cross-type order.

| Тип | Порядок |
| --- | --- |
| Bool | false < true |
| Int64 | математический signed order |
| Unit | единственное значение равно себе |
| String | lexicographic по числовым Unicode scalar values, shorter prefix first |
| Bytes | lexicographic по unsigned octets, shorter prefix first |
| Seq<T> | lexicographic по compare_T, shorter prefix first |
| Record | lexicographic по declaration order instantiated fields |
| Sum | declaration tag ordinal, затем payload compare одного tag |

Eq(Map) сопоставляет канонические пары по Key и сравнивает values по Eq. Map с Eq values, но без Key values, остаётся Eq. Eq суммы допускается только после проверки всех payload types; совпадение tag не разрешает спрятать запрещённый тип в другом варианте.

Comparator выполняет bounded leaf work и сохраняет continuation. При первом различии дальнейшее содержимое не просматривается. Число charged шагов и trace paths определяются профилем машины; математический порядок сам по себе не задаёт стоимость. Физическое сравнение целого host string за один шаг не считается доказательством bounded work.

## 7. String, Bytes и границы Unicode

String — конечная последовательность scalar values из `[0,D7FF] ∪ [E000,10FFFF]`. Surrogates D800–DFFF запрещены; noncharacters, unassigned и U+0000 не исключаются лишь по отсутствию display glyph. Это выбор value domain, не правило идентификаторов исходного языка. Locale, case folding, grapheme segmentation и normalization не участвуют в Eq/Key.

`é` (U+00E9) и `e + ◌́` (U+0065 U+0301) могут выглядеть одинаково, но остаются разными String values/keys. Нормализация предметного имени должна быть отдельным явным преобразованием с версией алгоритма и обработкой возникших duplicate keys. Скрытая нормализация при чтении меняет данные и запрещена.

`scalar_length`, `byte_length` и будущая grapheme length — разные API. Emoji за пределами BMP имеет один scalar и четыре UTF-8 octets. Byte offsets codec errors не выдаются за scalar index. String slice использует scalar boundaries, Bytes slice — byte boundaries; half-open interval и bounds должны быть указаны в каждой сигнатуре.

UTF-8 encode не добавляет BOM. U+FEFF внутри значения сохраняется как данные. Decode строгий: нельзя молча заменять invalid sequence на U+FFFD, принимать overlong forms, surrogate encodings, stray continuation, обрезанную sequence или scalar >10FFFF. Для каждой ошибки фиксируются категория и byte offset по exact decoder contract. Decode error — обычный Result, отмена и budget stop — отдельные runtime outcomes.

Scalar range основан на Unicode 16.0, §3.9 D76: [официальная спецификация](https://www.unicode.org/versions/Unicode16.0.0/core-spec/chapter-3/). Строгие UTF-8 ограничения описаны в [RFC 3629, §§3–4](https://www.rfc-editor.org/rfc/rfc3629). Числовой scalar domain не зависит от таблицы assigned characters; version-dependent Unicode algorithms потребуют отдельного закреплённого профиля.

## 8. Что остаётся открытым

Полный stdlib, производительный persistent container backend, формальное type-safety доказательство и единая интеграция DATA с CORE не закрыты этим документом. Полная binary schema/migration/activation V1 включает больше, чем value codec. Никакое совпадение данных в чистом опыте не доказывает атомарность DB, доставку событий или crash recovery.
