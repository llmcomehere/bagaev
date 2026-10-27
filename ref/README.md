# ref — эталонная реализация bagaev

Исполнимая спецификация языка на Python ≥ 3.11, только стандартная библиотека. Это точка сравнения для conformance-корпуса и для будущего компилятора на Rust (решение D65), а не промышленная реализация.

```bash
cd ref && python3 -m unittest discover -s tests -q   # тесты эталона
python3 -m bagaev_ref version                 # из каталога ref/ или с PYTHONPATH=ref
pip install --no-build-isolation -e ref       # команда bag; без изоляции сборки ничего не скачивается (нужен setuptools)
python3 conformance/run.py --impl ref         # корпус (из корня репозитория)
```

## Состав по фазам [плана](../registry/PLAN.md)

| Пакет | Фаза | Содержание |
| --- | --- | --- |
| `cli.py` | Ф0 | `version`, контракт `conformance-exec` (пока честный `NOT_IMPLEMENTED`) |
| `syntax/`, `sema/` | Ф2 | лексер, lossless CST, парсер, форматтер; разрешение имён, типы, эффекты |
| `ir/`, `machine/`, `stdlib/` | Ф3 | BIR-1, MACHINE-1 (уровни L1/L2), ядро stdlib |
| `host/` | Ф4 | SQLite, command/handler-транзакции, события, миграция, точки сбоя |
| `links/` | Ф5 | извлечение связей, граф, влияние, ContextPack |
| `change/`, `protocol/` | Ф6 | SourceEdit, ChangeContract, приёмка, WorkState, CLI `--json` и MCP |

## Правила

- Поведение задаёт спецификация `spec/`. Эталон её исполняет и ничего не дополняет: при расхождении правится спецификация или эталон, а не ожидание случая.
- Код моделей `models/` в эталон не копируется. Модели — независимая вторая реализация, с ней сверяются через `conformance/bridges/`.
- Каждая новая форма языка появляется вместе со случаями `conformance/`, положительными и отрицательными.
