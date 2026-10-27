# Пробный харнесс Ф7

Минимальный локальный прогон на Python ≥ 3.11, Node ≥ 22 и Linux `bwrap`. Модель не вызывается. Нужен уже установленный `pilot/writability/node_modules/typescript`; установка зависимостей здесь не выполняется. Нормативные ограничения опыта — [protocol.md](../authorship/protocol.md).

```bash
python3 -m unittest discover -s pilot/harness/tests -v
python3 pilot/harness/run.py schedule --output .bagaev/harness/schedule.json
python3 pilot/harness/run.py dry-run --output .bagaev/harness/dry-run-01
```

Выходной каталог должен быть новым. `schedule` по умолчанию даёт 5 × 8 × 3 строк; dry-run выполняет 3 независимые копии каждого варианта и отдельные инъекции, сброс сессии, сдвиг head и недоступный экспорт. `result.json` отделяет `outcome` проверок от `pilot_status: NOT_RUN`; LLM-метрики остаются `null`.

В `inputs.json` — точные SHA-256 и размеры входов, в `versions.json` — версии и состояние Git. В каждой копии `workspace/` содержит только приложение и разрешённый guide; `control/` хранит checkpoint, журнал `actions.jsonl`, результаты, квитанции и posthoc. Provider получает только JSON-контекст и ответы посредника. Контроллер, oracle и prepared reference не монтируются в процесс provider; исполнение кандидата тоже изолировано от oracle.

После сбоя `Session(repo, session_dir, resume=True)` проверяет checkpoint, журнал и входы. Несовпадение не исправляется автоматически. C06 проверяет отдельно перезапуск provider при сохранённом состоянии инструментов. `live` всегда выключен; этот код не является готовым Claude SDK-адаптером.

Commit-reveal закрытого задания:

```bash
python3 pilot/harness/commit_reveal.py commit --payload /private/tasks.json --nonce-file /private/nonce.bin
python3 pilot/harness/commit_reveal.py verify --payload /private/tasks.json --nonce-file /private/nonce.bin --sha256 HASH
python3 pilot/harness/closed.py verify --payload /private/tasks.json --nonce-file /private/nonce.bin --sha256 HASH
python3 pilot/harness/closed.py prepare --payload /private/tasks.json --nonce-file /private/nonce.bin --sha256 HASH --task ID --arm C --session .bagaev/harness/closed-C
python3 pilot/harness/closed.py probe --payload /private/tasks.json --nonce-file /private/nonce.bin --sha256 HASH --task ID --arm C --session .bagaev/harness/closed-probe-C
```

Payload первой версии: объект `format: bagaev-pilot-closed/1`, непустой `tasks`; у задачи поля `id`, `case: C10`, `initial: multi-author`, `public: {instruction, separator}`, `expected: {bylines: {a_101, a_102}}`. Значения готовит независимый автор. `prepare` копирует стартовое приложение с несколькими авторами, сохраняет commitment и предъявляет только `public`; target-правку не делает. После окончательного решения `closed.py evaluate` использует тот же payload/nonce/commitment и `--session`, сравнивая с независимыми ожиданиями. Закрытые C08/C11 пока не поддерживаются.

`probe` проверяет совместимость выбранного закрытого C10: исходный старт не должен выполнить новую задачу; одна подготовленная локальная правка — должна. Это controller-only проверка без provider, с `NOT_RUN` и `null` измерениями. Она поддерживает точный исходный шаблон разделителя и отказывается при его несовпадении.

Полные captures находятся в `.bagaev/`, не в Git. Обычные unit tests и dry-run не меняют приложения репозитория. Компактные итоги итерации фиксирует её владелец.
