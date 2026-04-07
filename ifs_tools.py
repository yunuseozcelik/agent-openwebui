"""IFS-backed tool surface limited to real FNSS endpoints."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any

from agent_framework import tool
from pydantic import Field

from ifs_client import (
    MOCK_MODE,
    MOCK_USER_EMAIL,
    get_empno_from_email,
    get_meal_list,
    get_part_detail,
    get_user_by_email,
    get_user_detail,
)


def _json_error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


def _normalize_user_email(user_email: str) -> str:
    email = (user_email or "").strip()
    if email:
        return email
    if MOCK_MODE:
        return MOCK_USER_EMAIL
    raise ValueError("Kullanıcı e-postası gerekli.")


def _normalize_badgeno(badgeno: str) -> str:
    value = (badgeno or "").strip()
    if not value:
        raise ValueError("Sicil numarası gerekli.")
    if len(value) == 4:
        return f"0{value}"
    if len(value) != 5:
        raise ValueError("Sicil numarası 4 veya 5 haneli olmalıdır.")
    return value


def _normalize_user_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "empNo": item.get("empNo"),
            "name": item.get("name"),
            "unit": item.get("unit"),
            "position": item.get("position"),
        }
        for item in records
    ]


def _normalize_user_detail_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "sicilNo": item.get("sicilNo"),
            "adSoyad": item.get("adSoyad"),
            "birim": item.get("birim"),
            "pozisyon": item.get("pozisyon"),
            "mail": item.get("mail"),
            "hizmetSuresi": item.get("hizmetSuresi"),
            "toplamIzin": item.get("toplamIzin"),
            "kullandigiIzin": item.get("kullandigiIzin"),
            "kalanIzin": item.get("kalanIzin"),
            "ecbSaat": item.get("ecbSaat"),
            "mazeretIzin": item.get("mazeretIzin"),
            "sonDurum": item.get("sonDurum"),
        }
        for item in records
    ]


def _normalize_part_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "parcaNo": item.get("parcaNo"),
            "aciklama": item.get("aciklama"),
            "eo": item.get("eo"),
            "teknikKoordinator": item.get("teknikKoordinator"),
            "urunKodu": item.get("urunKodu"),
            "tipKodu": item.get("tipKodu"),
        }
        for item in records
    ]


def _normalize_meal_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    today = datetime.now().strftime("%d.%m.%Y")
    normalized: list[dict[str, Any]] = []
    for item in records:
        normalized.append(
            {
                "tarih": item.get("tarih"),
                "yemek1": item.get("yemek1"),
                "yemek2": item.get("yemek2"),
                "yemek3": item.get("yemek3"),
                "yemek4": item.get("yemek4"),
                "toplamKalori": item.get("toplamKalori"),
                "salata1": item.get("salata1"),
                "salata2": item.get("salata2"),
                "salata3": item.get("salata3"),
                "salata4": item.get("salata4"),
                "salata5": item.get("salata5"),
                "salata6": item.get("salata6"),
                "salata7": item.get("salata7"),
                "salata8": item.get("salata8"),
                "salata9": item.get("salata9"),
                "salata10": item.get("salata10"),
                "salata11": item.get("salata11"),
                "salata12": item.get("salata12"),
                "salata13": item.get("salata13"),
                "is_today": item.get("tarih") == today,
            }
        )
    return normalized


@tool(approval_mode="never_require")
async def get_user_information(
    user_email: Annotated[str, Field(description="Çalışan e-posta adresi. Boş ise oturum kullanıcısı tercih edilir.")] = "",
) -> str:
    """IFS sisteminden temel kullanıcı bilgilerini getirir."""
    try:
        email = _normalize_user_email(user_email)
        records = await get_user_by_email(email)
        return json.dumps(_normalize_user_records(records), ensure_ascii=False)
    except Exception as exc:
        return _json_error(str(exc))


@tool(approval_mode="never_require")
async def get_user_detail_by_badgeno(
    badgeno: Annotated[str, Field(description="Sicil numarası. 4 veya 5 haneli olabilir.")] = "",
    user_email: Annotated[str, Field(description="Sicil numarası bilinmiyorsa kullanıcı e-postası.")] = "",
) -> str:
    """IFS sisteminden kullanıcı detay ve izin özet bilgilerini getirir."""
    try:
        resolved_badgeno = (badgeno or "").strip()
        if not resolved_badgeno:
            email = _normalize_user_email(user_email)
            resolved_badgeno = await get_empno_from_email(email)
        records = await get_user_detail(_normalize_badgeno(resolved_badgeno))
        return json.dumps(_normalize_user_detail_records(records), ensure_ascii=False)
    except Exception as exc:
        return _json_error(str(exc))


@tool(approval_mode="never_require")
async def get_part_detail_by_parcano(
    parcano: Annotated[str, Field(description="IFS parça numarası.")],
) -> str:
    """IFS sisteminden parça detay bilgilerini getirir."""
    try:
        value = (parcano or "").strip()
        if not value:
            raise ValueError("Parça numarası gerekli.")
        records = await get_part_detail(value)
        return json.dumps(_normalize_part_records(records), ensure_ascii=False)
    except Exception as exc:
        return _json_error(str(exc))


@tool(approval_mode="never_require")
async def get_meal_or_yemek_list(
    date: Annotated[str, Field(description="today veya DD.MM.YYYY formatında tarih.")] = "today",
) -> str:
    """IFS sisteminden yemek listesini getirir."""
    try:
        records = _normalize_meal_records(await get_meal_list())
        requested_date = datetime.now().strftime("%d.%m.%Y") if date == "today" else date
        selected_meal = next((item for item in records if item.get("tarih") == requested_date), None)
        payload = {
            "requested_date": requested_date,
            "selected_meal": selected_meal,
            "meal_list": records,
        }
        return json.dumps(payload, ensure_ascii=False)
    except Exception as exc:
        return _json_error(str(exc))


HR_TOOLS = [get_user_information, get_user_detail_by_badgeno]
IT_TOOLS = [get_part_detail_by_parcano]
GENERAL_TOOLS = [get_meal_or_yemek_list]
