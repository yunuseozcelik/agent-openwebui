"""Development-only mock workflow tools for end-to-end testing."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated

from agent_framework import tool
from pydantic import Field


@tool(approval_mode="never_require")
def create_mock_test_request(
    title: Annotated[str, Field(description="Talep başlığı")],
    priority: Annotated[str, Field(description="Öncelik: düşük, orta veya yüksek")],
    target_date: Annotated[str, Field(description="Hedef tarih")],
    note: Annotated[str, Field(description="Opsiyonel not")] = "",
) -> str:
    """Creates a fake request record so the UI workflow can be tested end to end."""
    request_id = f"MOCK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    payload = {
        "status": "created",
        "request_id": request_id,
        "title": title,
        "priority": priority,
        "target_date": target_date,
        "note": note,
        "message": f"Mock test kaydı oluşturuldu. Numara: {request_id}",
    }
    return json.dumps(payload, ensure_ascii=False)


TEST_TOOLS = [create_mock_test_request]
