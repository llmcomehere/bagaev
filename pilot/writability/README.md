# Пробник пишемости (Ф2, ворота K1)

Сравнение: насколько хорошо LLM пишет на bagaev по одной шпаргалке и на TypeScript. Протокол и порог K1 — [protocol.md](protocol.md).

| Файл | Назначение |
| --- | --- |
| [make_tasks.py](make_tasks.py) | источник 20 задач; пишет `tasks/` |
| `tasks/Wnn/task.md` | условие и требуемый интерфейс для обоих плеч |
| `tasks/Wnn/{c,t}/context/` | файлы проекта, которые видит модель |
| `tasks/Wnn/{c,t}/reference/` | эталонное решение (модели не показывается) |
| `tasks/Wnn/{c,t}/probe/` | скрытая проверка интерфейса |
| [run.py](run.py) | `--validate`, `--dry-run DIR`; `--run` — с явно заданными моделью и бюджетом |

Состояние r28:
- эталоны C проходят `bag check`, а контекст без решения — нет;
- эталоны T проходят `tsc` 5.9.3 (закреплён в `package.json`), а контекст без решения — нет;

```bash
python3 pilot/writability/run.py --validate
```
