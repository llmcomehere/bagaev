#!/usr/bin/env python3
"""Доверенная квитанция запуска CLI внутри sandbox; ожиданий oracle здесь нет."""
import json
import subprocess
import sys
import tempfile

request = json.load(sys.stdin)
with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
    try:
        child = subprocess.Popen(request["argv"], stdout=out, stderr=err)
    except OSError as exc:
        result = {"started": False, "code": "CLI_LAUNCH_FAILED", "detail": type(exc).__name__}
    else:
        child.wait()  # весь sandbox ограничен таймаутом контроллера
        out.seek(0)
        err.seek(0)
        result = {"started": True, "returncode": child.returncode,
                  "stdout": out.read().decode(errors="replace"), "stderr": err.read().decode(errors="replace")}
print(json.dumps(result, ensure_ascii=False))
