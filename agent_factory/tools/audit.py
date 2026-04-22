"""Basit JSONL audit log. Her action tool cagrisi buraya bir satir yazar."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_AUDIT_PATH = Path("generated") / "audit.log"
_LOCK = Lock()


def log_action(
    *,
    user_email: str,
    agent_name: str,
    action: str,
    params: dict,
    result: dict,
) -> None:
    """Action tool cagrisini JSONL dosyasina ekle."""
    _AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": user_email,
        "agent": agent_name,
        "action": action,
        "params": params,
        "result": result,
    }
    line = json.dumps(entry, ensure_ascii=False)
    with _LOCK:
        with _AUDIT_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
