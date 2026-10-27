#!/usr/bin/env python3
"""Scripted provider: JSON-вызовы из сценария; ни SDK, ни модели, ни сети."""
import json
import os
import sys
import uuid

session = uuid.uuid4().hex
print(json.dumps({"session": session, "pid": os.getpid(), "provider": "scripted"}), flush=True)
for line in sys.stdin:
    envelope = json.loads(line)
    # Контекст действительно передан процессу; он не выдаёт его за входные токены LLM.
    print(json.dumps({"session": session, "action": envelope["next_action"]}), flush=True)
