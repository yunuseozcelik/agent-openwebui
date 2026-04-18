"""In-memory session store — chat state ve wizard progresi."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from time import time
from typing import Any


@dataclass
class Session:
    id: str
    created_at: float = field(default_factory=time)
    last_active: float = field(default_factory=time)
    # Wizard state
    wizard: dict[str, Any] = field(default_factory=dict)
    # Chat runner (per agent)
    runners: dict[str, Any] = field(default_factory=dict)
    # Pending build
    pending_spec_id: str | None = None
    pending_definition: dict | None = None


class SessionStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: dict[str, Session] = {}

    def get(self, session_id: str) -> Session:
        with self._lock:
            s = self._sessions.get(session_id)
            if s is None:
                s = Session(id=session_id)
                self._sessions[session_id] = s
            s.last_active = time()
            return s

    def cleanup(self, ttl_seconds: int = 3600) -> int:
        """Eski oturumlari sil."""
        now = time()
        removed = 0
        with self._lock:
            expired = [sid for sid, s in self._sessions.items() if now - s.last_active > ttl_seconds]
            for sid in expired:
                del self._sessions[sid]
                removed += 1
        return removed


session_store = SessionStore()
