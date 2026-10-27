#!/usr/bin/env bash
# Окружение для проверок bagaev: pinned зависимости schema-проверок моделей.
#   bash tools/setup.sh
# Ставит в .venv (если доступен модуль venv), иначе в .deps; оба каталога в .gitignore.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
req="$root/tools/requirements.txt"

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    sys.exit(f"нужен Python >= 3.10, сейчас {sys.version.split()[0]}")
PY

if python3 -m venv "$root/.venv" >/dev/null 2>&1 && [ -x "$root/.venv/bin/python" ]; then
  "$root/.venv/bin/python" -m pip install --quiet --disable-pip-version-check -r "$req"
  "$root/.venv/bin/python" -c 'import importlib.metadata as m; print("jsonschema", m.version("jsonschema"), "-> .venv")'
else
  rm -rf "$root/.venv"
  echo "venv недоступен (пакет python3-venv?) — ставлю в .deps" >&2
  python3 -m pip install --quiet --disable-pip-version-check --target "$root/.deps" --upgrade -r "$req"
  PYTHONPATH="$root/.deps" python3 -c 'import importlib.metadata as m; print("jsonschema", m.version("jsonschema"), "-> .deps")'
fi
echo "Готово: python3 tools/check.py --models"
