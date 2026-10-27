# Опыт авторства A/B/C

Статус: **подготовка Ф7** ([план](../../registry/PLAN.md)); прогонов нет — **NOT_RUN**.

| Путь | Содержание | Состояние |
| --- | --- | --- |
| [contract.md](contract.md) | общий CLI-контракт вариантов: команды, коды, состояние, скрытые потребители | r35 |
| [data/seed.json](data/seed.json) | исходное состояние D0 из фикстуры | r35 |
| [arms.json](arms.json), `arms/` | как вызвать CLI каждого варианта; адаптер варианта C поверх хоста bagaev | r35: C; r36: A, B |
| `app-bagaev/` | вариант C, исходная программа S0: 68 деклараций, отвлекающие модули (комментарии, просмотры, карта сайта), скрытые потребители (RSS, уведомления) | r35 |
| `reference/` | эталонные решения изменения для проверки оракула; агентам не показываются | r35: C; r36: TS |
| [oracle/](oracle/) | чёрный ящик по контракту; ожидания из [authorship-fixtures.json](../../registry/data/core/authorship-fixtures.json); мутанты для проверки оракула | r35 |
| `app-ts/` | варианты A и B, исходная программа S0 на TypeScript strict (`node:sqlite`, `node:test`, без сторонних пакетов): те же модули, отвлекающие и скрытые потребители, связи в JSDoc | r36 |
| [links-ts/extract.ts](links-ts/extract.ts) | вариант B: извлекатель связей TypeScript (компиляторный API) в общую схему графа; протокол, влияние, свидетельства и приёмка — общий движок (`meta.language = typescript`, CHG-01а) | r37 |
| [mechanism/](mechanism/README.md) | детерминированные C02, C03, C07, обнаружение C09, C13 без LLM; A — обычный Git CAS, B/C — CHANGE-1 | r39 |
| [protocol.md](protocol.md), [preregistration.json](preregistration.json) | черновик H1–H3, лимитов и учёта стоимости; после `pilot-freeze-1` меняется только через `amendments/` | r39, DRAFT |
| [harness](../harness/README.md) | изолированные инструменты, пробные сессии и отдельный posthoc; live отключён | r39 |
| [closed-commitments.json](closed-commitments.json) | публичный commitment 3 независимых C10; payload и nonce вне Git | r39, DRAFT |
| `results/`, `receipts/`, `report.md`, `decision.md` | фактические прогоны и вывод | Ф8 |

```bash
python3 pilot/authorship/oracle/run.py --arm C
```

Модель — только Claude, с точным ID версии; выводы ограничены этим семейством. Прогоны — только после явного задания модели и бюджета.
