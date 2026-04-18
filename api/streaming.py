"""SSE streaming helpers — pipeline + chat canli akisi icin."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator


def sse_event(event: str, data: Any) -> str:
    """SSE formatli event metni olustur."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


async def heartbeat(interval: float = 15.0) -> AsyncIterator[str]:
    while True:
        await asyncio.sleep(interval)
        yield ": heartbeat\n\n"
