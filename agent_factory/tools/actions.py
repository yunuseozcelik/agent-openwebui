"""Mock action tools — MAF Agent tarafindan LLM tool-call olarak cagrilir.

Her tool:
  1. generated/requests/ altina JSON dosya yazar,
  2. audit log'a satir ekler,
  3. LLM'e referans numarasi + ozet dondurur.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Callable

from pydantic import Field

from .audit import log_action

_REQUEST_DIR = Path("generated") / "requests"


def _write_request(kind: str, payload: dict) -> str:
    _REQUEST_DIR.mkdir(parents=True, exist_ok=True)
    ref = f"{kind}-{uuid.uuid4().hex[:6].upper()}"
    payload = {
        "ref": ref,
        "kind": kind,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    (_REQUEST_DIR / f"{ref}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return ref


def build_action_tools(user: dict, agent_name: str) -> list[Callable]:
    """Kullaniciya bagli action tool fonksiyonlari olustur."""
    user_email = user.get("email", "unknown")
    user_name = user.get("name", "Kullanici")

    def request_leave(
        start_date: Annotated[str, Field(description="Izin baslangic tarihi YYYY-MM-DD")],
        end_date: Annotated[str, Field(description="Izin bitis tarihi YYYY-MM-DD")],
        reason: Annotated[str, Field(description="Kisa gerekce")] = "",
    ) -> str:
        """Yillik izin talebi olusturur. Onay icin IK'ya iletilir."""
        params = {"start_date": start_date, "end_date": end_date, "reason": reason}
        ref = _write_request("LV", {"user": user_email, "user_name": user_name, **params})
        result = {"ref": ref, "status": "PENDING_APPROVAL"}
        log_action(
            user_email=user_email, agent_name=agent_name,
            action="request_leave", params=params, result=result,
        )
        return (
            f"Izin talebi olusturuldu. Referans: {ref}. "
            f"{start_date} - {end_date} tarihleri arasi, onay bekliyor."
        )

    def request_advance(
        amount_try: Annotated[float, Field(description="TL cinsinden avans tutari")],
        reason: Annotated[str, Field(description="Gerekce")],
        repayment_months: Annotated[int, Field(description="Geri odeme ay sayisi")] = 3,
    ) -> str:
        """Maas avansi talebi olusturur."""
        params = {"amount_try": amount_try, "reason": reason, "repayment_months": repayment_months}
        ref = _write_request("AV", {"user": user_email, "user_name": user_name, **params})
        result = {"ref": ref, "status": "PENDING_APPROVAL"}
        log_action(
            user_email=user_email, agent_name=agent_name,
            action="request_advance", params=params, result=result,
        )
        return (
            f"Avans talebi olusturuldu. Referans: {ref}. "
            f"{amount_try} TL, {repayment_months} ay geri odemeli, onay bekliyor."
        )

    def create_ticket(
        title: Annotated[str, Field(description="Ticket basligi")],
        description: Annotated[str, Field(description="Sorunun detayli aciklamasi")],
        priority: Annotated[str, Field(description="low|medium|high")] = "medium",
    ) -> str:
        """IT destek ticket'i acar."""
        params = {"title": title, "description": description, "priority": priority}
        ref = _write_request("TKT", {"user": user_email, "user_name": user_name, **params})
        result = {"ref": ref, "status": "OPEN"}
        log_action(
            user_email=user_email, agent_name=agent_name,
            action="create_ticket", params=params, result=result,
        )
        return f"Ticket acildi. Referans: {ref}. Oncelik: {priority}."

    return [request_leave, request_advance, create_ticket]
