# R23 · маршрут реализации и приёмки FFI

Все 42 случая в [integration-cases.json](../../registry/data/ffi/ffi-integration-cases.json) имеют конкретный expected outcome, независимый метод проверки и blocking inputs. Все **NOT_RUN** для production. Они раскрывают исходный T13-C04, но не создают новые критерии процентного счётчика.

## 1. Реестры и компилятор

Реализовать exact adapter/type/resource/callback manifests, ground type admission и effect closure. Закрепить полный ABI slot registry, диагностики и type/source bindings. Compiler сохраняет HostCall даже для native функции, названной pure. Выход: immutable accepted binding table и отказ до исполнения при несогласованности. Cases 01–03,09,34,37.

## 2. Кодирование и logical machine

Реализовать frame parser отдельно от language DATA codec. Нормативный incremental decode, size prepass, emit и Key comparator описаны в codec-machine.md; host parser не выбирает собственную стоимость. Независимо проверить full state/action sequence при каждом cutpoint, bad UTF8, map order, phantom fields, нулевые payload и trailing data. Cases 07–10,29,41.

## 3. Broker resources и authority

Реализовать ключи/epochs/generations, mode matrix, all-or-nothing reserve, move commit и current gate. Внешние ресурсы принадлежат broker; worker не получает native FD/pointer на них. Развести access revocation, close authority и cleanup scope. Проверить все переходы и отказ без побочного изменения ledger. Cases 04–06,11–15,20–22,27,33,38,39.

## 4. Native shim и SandboxFactory

Сгенерировать typed native wrappers из exact ABI declarations: conversions, ownership, retained buffers, allocator pairing, exception policy и callbacks. Реализовать actual confinement до constructors, loader binding и supervisor process-tree fencing. Оценивать real enforcement отдельным внешним observer, а не полем READY. Если platform не проходит admission, профиль не запускается. Cases 16,24,30–32,40.

## 5. Call machine и publication

Реализовать shared budget/cancel ordering, отдельную durable dispatch admission, bounded inbox, private decode arena, atomic multi-slot publication и pending resources. Неверный reply не превращается в отсутствие эффекта. Resource outputs ждут quiescence; late outputs дают cleanup obligation. Cases 14–19,23.

## 6. Callback scheduler

Реализовать scoped closure registry, foreign-thread ingress queue, общий budget и ограниченную authority, exact duplicate receipts и wait-graph cycle check. Закрытие admission отделить от quiescence захваченных значений. Отдельный Subscription resource нужен для long-lived callbacks. Cases 24–28.

## 7. Journal, settlement и recovery

Связать actual R16 idempotency/reconciliation и current authority adapters. Replay не создаёт live calls/resources. Физический crash после admission не объявляется rollback; unknown operations удерживают ledger и backpressure. Проверить late receipts и complete lease release независимо от caller termination. Cases 15,17,23,35,36,39,42.

## 8. Интеграция, доказательства и приёмка

Подключить новые stage/target admissions к actual compiler/runtime. Для общей корректности требуются инварианты ownership uniqueness, no-use-after-release, current effect admission, exact codec roundtrip/canonical rejection, preservation of type/effects, callback lifetime и replay separation. Показать как локальные доказательства составляются с upstream language/data/authority contracts.

После этого выполнить все 42 независимых production cases и разумные combinations реальных платформ, измерить overhead копирования, кодирования, очередей и cleanup. Результат finite Python-модели и synthetic metadata probes не подменяет эти gates. Stage 3 требует независимого подтверждения всей заявленной области; stage 4 — нормативной приёмки и закрытых зависимостей. R23 их не объявляет.

## Уже доступное исследовательское основание

Конечная модель имеет один call, до12events, до4bytes и до2handle slots. Проверяет reserve/dispatch/current authority, atomic output publication, late reply и отдельный trusted ack. Не реализует wire/codec, actual native memory/threads/confinement, callbacks, multi-call allocation/reuse, durable recovery или full V1. Независимый verifier ведёт отдельные frozen expectations и report; этот маршрут не заявляет заранее их результат.
