# STDLIB-WORK-0.1 — порядок, стоимость и продолжения

**R24 · проект reference schedules; integrated execution NOT_RUN.** Новая библиотечная revision не переименовывает traces прошлых CORE/DATA экспериментов. Каждая функция исполняется над уже вычисленными operands. Ссылки на семантику/алгоритм R07 означают письменные правила; его JSON job API не становится способом передачи closures или resources в общем runtime.

## 1. Общая машина вызова

Cursor: exact SymbolContractRef, monotypes, immutable operands, operation phase, item/byte/type stacks, private output, shared execution budget/cancellation ref, caller continuation. Нет заново разрешаемых имён или указателей на current catalog.

Boundary order: terminal whole execution → visible cancel → zero semantic budget → prospective physical guard → один зарегистрированный transition. Каждый указанный ниже LIB action стоит 1. `LIB_ENTER` начинает вызов, `LIB_RETURN` атомарно публикует всё typed значение в caller continuation. Сформированное Err тоже проходит LIB_RETURN. После этого caller может продолжать: terminal подвыражение не означает terminal всей программы. Если cancellation появилась перед LIB_RETURN, partial result не публикуется. Cost convention отличается от standalone DATA, где faulting action мог сразу вернуть Err; адаптер обязан сохранить новую revision, не заявлять trace identity старых профилей.

Физическое sharing/metadata/cache не удаляет логические actions. И наоборот, logical cost не обещает точное число machine instructions/выделенных bytes. Нельзя bulk-compute результат до первой разрешённой boundary и потом выдавать фиктивные шаги. Cursor выполняет текущую action после gate. Output bounds включают wrapper/temporary value nodes; checked арифметика размеров до allocation. Нехватка ресурсов не превращается в BoundsError/OutOfRange/ValueMismatch.

## 2. Закрытые pure schedules

Каждый schedule ниже окружён LIB_ENTER и LIB_RETURN. Internal result сначала private. При обычной ошибке remaining actions тела не выполняются; следующий action — LIB_RETURN. Все item ranges идут по возрастанию index. Условие loop/состояние следующего action вычисляется из уже полученных metadata; оно не вызывает пользовательский код и не обходит необработанные данные. Используемые length/type/tag metadata были validated при создании value; неизвестный metadata invariant — ImplementationStop.

| Work ID | Точная последовательность действий тела |
| --- | --- |
| SCALAR | LIB_SCALAR один раз; mathematical arithmetic + range gate. Для фиксированной Int64 domain допустим widened arithmetic без host overflow |
| TAG | LIB_TAG один раз, выбрать заранее вычисленный payload/значение; никакого скрытого вызова |
| LENGTH | LIB_LENGTH_ITEM по одному для каждого scalar/octet/item/entry; final count накоплен с checked addition |
| GET | LIB_INDEX_CHECK; invalid index → None; иначе LIB_READ_ITEM для каждого index0..requested, последняя action фиксирует Some(item/scalar/octet). Это выбранная reference стоимость, не обещание O(1) |
| COPY_ITEMS | LIB_COPY_ITEM на каждый element/scalar/octet, затем LIB_ASSEMBLE |
| VALIDATE_ITEMS | LIB_VALIDATE_ITEM на каждый Int64; первый недопустимый фиксирует indexed Err; допустимый сразу помещается в private builder. После всех — LIB_ASSEMBLE для Ok |
| APPEND | LIB_COPY_ITEM на каждый прежний item; LIB_APPEND_ITEM для нового; LIB_ASSEMBLE |
| CONCAT | LIB_COPY_ITEM по левому operand, затем по правому; LIB_ASSEMBLE; capacity headroom проверяется до первой публикации/private allocation, без wrap |
| SLICE | LIB_SLICE_CHECK использует validated length и start/end; invalid → BoundsError; иначе LIB_COPY_ITEM для source[start..end); LIB_ASSEMBLE |
| PARSE_DECIMAL | LIB_PARSE_BEGIN; LIB_SYNTAX_SCALAR по каждому scalar до первой syntax error, включая знак/leading-zero state; LIB_SYNTAX_END проверяет Empty/SignOnly; при успехе LIB_DIGIT_ACCUMULATE для каждой цифры и LIB_PARSE_FINISH. Range error прекращает accumulation; грамматика к этому моменту проверена полностью |
| FORMAT_DECIMAL | LIB_FORMAT_BEGIN; для ненулевого x LIB_FORMAT_DIGIT на каждое извлечение decimal digit из неположительного accumulator; для 0 одна LIB_FORMAT_DIGIT с 0; LIB_FORMAT_SIGN для отрицательного x; LIB_FORMAT_COPY по итоговым символам в правильном порядке; LIB_ASSEMBLE |
| COMPARE | Work traversal COMPARE_NODE/UNIT/NEXT/END по DATA API §4.2; каждый 1, без JOB_START/JOB_FINISH; Eq проверяет все required type predicates до runtime admission, а traversal останавливается на первом различии |
| MAP_BUILD | Work MAP_STAGE/PROBE/DECIDE/COPY/ADD/COMMIT и вложенный comparator по DATA API §4.3; каждый 1, без JOB_START/JOB_FINISH. Duplicate создаёт private DataError, затем LIB_RETURN |
| MAP_GET | MAP_LOOKUP + comparator + MAP_LOOKUP_DECIDE слева направо; first equal → Some; key меньше current → None; end → MAP_LOOKUP_END. Все actions1, затем LIB_RETURN |
| MAP_ENTRIES | LIB_ENTRY_COPY по canonical pairs, создавая Entry<K,V>; LIB_ASSEMBLE |
| MAP_PUT | LIB_MAP_PROBE + comparator + LIB_MAP_DECIDE для каждого existing entry до equal/first greater/end; затем LIB_ENTRY_COPY по всем old pairs кроме заменяемого, LIB_ENTRY_INSERT ровно в выбранной позиции, LIB_ASSEMBLE. Equal сохраняет position, но кладёт новые key/value |
| MAP_REMOVE | Такой же bounded search; затем LIB_ENTRY_COPY по всем оставшимся entries, LIB_ASSEMBLE. Если absent — копируются все entries; никакого pointer-equality shortcut в trace |
| UTF8_ENCODE | UTF8_SCALAR и UTF8_WRITE по DATA API §5; каждый 1, без JOB_START/JOB_FINISH; ошибки typed input невозможны после проверки String |
| UTF8_DECODE | UTF8_READ по одному octet + UTF8_END по DATA API §5; каждый 1, без JOB_START/JOB_FINISH; malformed input создаёт private DataError; LIB_RETURN |
| LOCKED_CODEC | Exact VALUE-CODEC-V1 supplies полный inner action registry, traversal/error offsets и caps. Его start/finish действия не угадываются по DATA/R07; отсутствие/неподдержка exact codec → INPUT_NOT_READY до запуска |
| TEST_CHECK | LIB_TEST_CHECK один раз; case_id сохраняется как immutable String; результат Pass/Fail |
| TEST_EQUAL | Полный COMPARE для Eq, затем LIB_TEST_CHECK; никаких host repr/serialization values |
| TEST_ALL | LIB_TEST_ITEM для каждого Check с сохранением source index и failed list; LIB_ASSEMBLE summary; нет остановки на первом Fail |

Результат comparison/map/UTF8 переносится на internal Value representation общим typed adapter; сам public DATA job не принимает functional container values. Eq/comparator Fn запрещён whole-type predicate, а map values/seq elements типа Fn допускаются там, где операция лишь переносит VM values. Никакого JSON descriptor вместо capture.

Перенос правил R07 — по алгоритму обхода над **новыми exact type descriptors**. Error construction map/UTF8 переводит допустимый label L в DataErrorCode.L(Unit), сохраняя first/second; String field старого DataError не вставляется в новый record. Comparator нового DataError посещает code sum/tag по новой registry и затем first/second. Старые work counts/ordinals/wire errors не выдаются за новые автоматически; именно библиотечный schedule и описанное отображение составляют subject будущих проверок. Для Option/Result используются закреплённые в types.md ordinals None/Some и Ok/Err.

FORMAT_DECIMAL использует q=trunc(x/10), digit=−(x−q×10) на неположительном x; полученные digits разворачиваются в output builder. Так MIN не требует промежуточного +9223372036854775808. PARSE_DECIMAL после grammar pass держит неположительный accumulator: limit=MIN при минусе, иначе −MAX. До `acc*10−digit` проверяет `acc ≥ trunc(limit/10)` и затем `acc*10 ≥ limit+digit`; после всех цифр положительный результат получается negation допустимого accumulator. Пустота/sign/leading zero не интерпретируются как default0.

## 3. Вызовы pure closures

Таблица содержит MAP_OPTION, MAP_RESULT, MAP_ERROR, MAP_SEQ, FOLD_SEQ. Это не foreign callbacks и не разновидность effect-row polymorphism. Fn уже специализирован до exact monotype и имеет bound `{}`. Pure означает отсутствие внешних эффектов, но не тотальность: closure может рекурсировать, исчерпать бюджет или получить ImplementationStop.

MAP_OPTION/RESULT/ERROR: LIB_TAG выбирает вариант; для выбранного payload LIB_CALL_PREPARED создаёт обычную VM activation с готовыми аргументами, сохраняя library continuation; затем выполняются реальные transitions тела по MACHINE-V1; LIB_CALL_RECEIVE принимает returned value; LIB_WRAP строит нужный sum. Невзятая ветвь не выполняет CALL, RECEIVE или WRAP: сохраняется старый payload под точным выходным sum type в LIB_TAG. Вариант None с другим type argument при пустом текущем payload создаёт соответствующий typed wrapper, не меняет identity прежнего values. T у Option<T> не является phantom всего типа: Some(T) учитывается whole-type predicate даже для текущего None.

MAP_SEQ/FOLD_SEQ: LIB_ITERATE выбирает следующий item по source index. Если item есть, LIB_CALL_PREPARED вызывает f с одним item либо accumulator+item; body выполняется обычной машиной; LIB_CALL_RECEIVE получает value; LIB_ITERATE_STORE записывает output либо новый accumulator. Затем следующая LIB_ITERATE. Финальная LIB_ITERATE обнаруживает конец; LIB_ASSEMBLE выдаёт Seq либо accumulator. Empty выполняет одну LIB_ITERATE и LIB_ASSEMBLE, ни одного вызова f.

Все LIB actions стоят 1. `LIB_CALL_PREPARED` является entry уже вычисленного closure call; fn/arg выражения повторно не вычисляются и CORE source `CALL_ARGS` задним числом не имитируются. Тело исполняется с прежними exact closure captures, type args, execution budget и logical cancellation identity. `LIB_CALL_RECEIVE` — отдельная граница перед переносом результата. До общего V1 MACHINE contract, который поддерживает этот prepared-call entry и перечисляет собственные body/return transitions, integrated запуск блокируется. R24 не создаёт общий evaluator и не объявляет source lowering проверенным.

## 4. Сервисы и host waiting

SERVICE_READ/WRITE: LIB_SERVICE_PREPARE(1) → pinned service codec traversal → LIB_SERVICE_ADMIT(1) → service dispatch по exact STORE/EVENTS/JOURNAL contracts → recorded waiting/response events → decode/validate → LIB_SERVICE_RECEIVE(1) → LIB_RETURN. Waiting не бесконечный loop semantic ticks. Реальные authority/intent/commit barriers описывает services.md и обязательный adapter; полный перечень его states/checks/charges должен быть в exact зависимости. Unknown dependency нельзя подменить одними именами actions R24.

Перед admission cancellation не начинает новую service command. После admission termination caller не уничтожает intent/receipt/dedup/frontier, cleanup или knowledge. Replay использует сохранённое service observation, не вызывает live adapter. Здесь выбран trusted registered VM/broker service primitive с объявленными Store/Event effects и текущими authority gates. Замена на native FFI требует нового explicitly admitted closed effect contract с R23 HostCall; прежняя signature не разрешает такую подмену. Pure catalog lookup/ref не даёт доступа.

## 5. Проверка и оптимизации

Для каждого расписания нужно сравнивать result/error, полный порядок действий, completed work, semantic stop/cancel point и отсутствие partial publication. Cut перед LIB_RETURN должен отличаться от успешного return. Shortcuts, vectorization, fused UTF8/parse passes и parallel map требуют admission по R22 preservation contract. Value-only совпадение не даёт права менять cost/cancel observation. Старые DATA tests подтверждают лишь старую конечную область; дальнейшие случаи перечислены в acceptance.md со статусом NOT_RUN.
