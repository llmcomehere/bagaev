# FFI-BOUNDARY-0.1 — явная граница внешнего кода

**R23 · WORKING_DESIGN.** Владелец: исходный T13-C04. Область — политика FFI всего V1: типизированные зарегистрированные адаптеры, значения, ресурсы, callbacks, эффекты, память, отказы и включение в toolchain. Документ задаёт предлагаемые правила; actual platform/runtime conformance остаётся отдельной обязательной работой.

## 1. Граница и состав

Переносимый ABI описывает значения и протокол, а не layout структур host-языка. Основной профиль `FFI-BOUNDARY-0.1` использует отдельный worker адаптера и копирование данных. Только broker держит реальные capability и системные ресурсы. Worker получает сообщения и ограниченные идентификаторы выданных ему leases. Нативные указатели VM, адреса её heap, C++ vtable и замыкания за границу не передаются.

Контракты разделены:

- [wire-abi.md](wire-abi.md): точные значения, перенос и проверка кадров;
- [ownership-lifecycle.md](ownership-lifecycle.md): владение, borrow, move, close и quiescence;
- [calls-effects-callbacks.md](calls-effects-callbacks.md): переходы, authority, callbacks, ошибки и replay;
- [isolation-adapters.md](isolation-adapters.md): точный worker image, native shim, изоляция и реальные пределы;
- [ffi-bridge.md](../toolchain/ffi-bridge.md): стадии компилятора и загрузчик;
- [ffi-route.md](ffi-route.md): реализация и независимая приёмка.

## 2. Идентичности и обязательные контракты

`ExactRef = (kind, schema_revision, byte_length, sha256)`. Digest относится к точным байтам, которые читает загрузчик. Имя, версия semver, URL, путь и подпись автора не заменяют exact identity; хеш сам по себе не даёт authority или корректности реализации.

`AdapterManifest` закрепляет worker image и всю исполняемую closure зависимостей, ABI/profile, platform admission, registry типов, функции, ресурсные типы, callback signatures, допустимые broker operations, limits и происхождение. Выбор worker по изменяемому поисковому пути запрещён.

Каждый `FunctionContract` содержит:

1. `FunctionId`, stable AdapterId и exact заранее существующая InterfaceDeclarationRef; manifest связывает контракт с конкретным worker image позднее, по ациклическому порядку ffi-bridge §6.
2. Упорядоченные входные и выходные slots; DATA имеют ground type/codec, RESOURCE — resource type и ownership mode, CALLBACK — exact signature и lifetime.
3. Верхнюю границу эффектов, селекторы фактических ресурсов, необходимые runtime capability checks и допустимые broker operations. Эффекты callbacks и cleanup включаются отдельно и транзитивно.
4. Обычный return type, включая объявленный `Result<T,E>`, и перечень boundary faults.
5. Правила подготовки, dispatch, владения, quiescence, cancellation, late result, reconciliation, replay и отсутствие автоматического retry.
6. Лимиты, incremental codec/charge profile, точные требуемые платформенные свойства и неизменяемые source/origin refs.

Генерик инстанцируется до ABI boundary. Полиморфная функция не передаётся как «универсальный указатель». Типы после инстанцирования и resource/callback modes входят в interface identity.

## 3. Три вида передаваемых значений

| Slot | Представление | Разрешение |
| --- | --- | --- |
| DATA<T> | Новая копия значения по точному WireDataCodec | Ground тип целиком принадлежит WireData, включая все варианты суммы |
| RESOURCE<R,mode> | Token в broker registry с type/generation/lease/call binding | Проверяется runtime, не выводится из корректного JSON/хеша |
| CALLBACK<S> | Token регистрации callback; closure остаётся в VM | Exact signature, call scope, ограниченные эффекты и current authority |

`WireData` включает Unit, Bool, Int64, String, Bytes, Seq, Map с Key, зарегистрированные ациклические records/sums, Option и Result после ground instantiation. Рекурсивные пользовательские типы, float и bigint сохраняют исходный pending status V1: отсутствующий утверждённый контракт даёт INPUT_NOT_READY, а не приблизительный host codec.

Fn, Capability, HostHandle и Callback не являются WireData ни непосредственно, ни в реальных payload positions контейнера. Предикат структурно раскрывает ground fields, как DATA-0.1: phantom type argument без собственного поля не создаёт передаваемого значения; например, зарегистрированный Phantom<Fn>{} допустим при точном кодируемом описании типа. Пустая Seq<Handle> или None типа Option<Fn> не обходят проверку полного типа. `Persistable` не даёт полномочия и не является wire admission сам по себе. Resource/callback slots объявляются явно в сигнатуре; для структуры с ресурсом wrapper объявляет отдельные slots, а не выдаёт её за сериализуемую DATA.

Иммутабельные значения языка не приобретают скрытую мутабельность. Copy-out публикует новые выходные значения; native inout buffer wrapper превращает в явный вход и новый выход. Скрытой записи обратно в исходную DATA VM нет.

## 4. Наблюдения и три независимых состояния

Состояние вызова содержит:

- `caller`: Active / Waiting / Returned(value) / SemanticStop / BoundaryFault / ImplementationStop;
- `external`: NotDispatched / MayHaveRun / Known(receipt,outcome), где outcome может быть Committed, Failed или ConfirmedNotApplied только при достаточном отдельном основании;
- `resources`: Reserved / LentOrMoved / ReleasePending / Quiescent / Closed, с точным ledger каждого lease.

Эти оси не склеиваются. `Cancelled + MayHaveRun + ReleasePending` допустимо. `Returned(Err(...)) + MayHaveRun` тоже допустимо: обычный ответ адаптера не обязательно является подтверждённым settlement внешнего действия. Quiescence доказывает конец доступа к данным/ресурсу в данной области, но не откат эффекта. Process death может подтвердить прекращение доступа процесса к памяти, но не отсутствие удалённой операции.

Наблюдаемая запись содержит execution/source/node/occurrence, adapter/function/interface identity, направление и порядок сообщений, logical boundary, request binding, transfer ledger, resource checks, caller termination, отдельные effect receipts и release evidence. Она не содержит секретные credentials или сырые адреса.

## 5. Ошибки по фазам

| Категория | Примеры | Что разрешено после неё |
| --- | --- | --- |
| Prelaunch rejection | UnknownAdapter, IncompatibleABI, UnknownFunction, InvalidSignature, MissingPlatformAdmission | Внешнее исполнение не начато |
| Обычное значение | Объявленный Result.Err приложения | Обычное продолжение языка, без неявного trap |
| SemanticStop | Cancelled, BudgetExceeded по logical policy | Caller не возобновляется; settlement/release продолжаются отдельно |
| BoundaryFault | AdapterContractFault, invalid token, stale generation, undeclared broker request, invalid callback | Ошибка границы с точным origin; неизвестный эффект остаётся неизвестным |
| ImplementationStop | Host OOM, physical timeout, decoder invariant failure, platform control failure | Не маскируется под domain Err или semantic budget |
| Pending knowledge | MayHaveRun, ReleasePending, отсутствующий receipt | Нет нового эффекта через replay или автоматический retry |

Malformed входной artifact отклоняется до запуска. Malformed сообщение worker — нарушение контракта адаптера. Если malformed состояние создано самой VM, это внутренняя ошибка реализации; одинаковые байты в разных фазах не обязаны иметь одинаковый код.

## 6. Политика полноты и применимость evidence

Ни reference fallback, ни зарегистрированное имя не реализуют неизвестный ABI. Обязательный неизвестный type/form/effect/ownership/platform contract даёт INPUT_NOT_READY. Неподдерживаемый объявленный профиль даёт UNSUPPORTED_PROFILE. Неизвестная версия никогда не декодируется «как ближайшая».

Конечная модель R23 исследует copy publication, transfer и отдельный ack на малом количестве ресурсов. Она не реализует wire codec, native wrapper, callbacks, изоляцию ОС, durable broker или весь V1. Ее успешные проверки не являются общей memory-safety theorem и не закрывают stage 3/4 T13-C04.

Документ не меняет запреты V1 на shared mutable threads и произвольную dynamic loading. Worker может иметь внутренние native threads только при явном platform contract, но не получает общий mutable heap языка и не исполняет VM callback в чужом потоке.
