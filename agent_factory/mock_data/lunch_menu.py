"""Date-based mock lunch menu helpers."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

DATA_PATH = Path(__file__).with_name("lunch_menu_2026.json")


def _load() -> list[dict]:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return list(payload.get("menus", []))


def _parse_date(value: str | date | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_lunch_menu(target_date: str | date | None = None) -> dict | None:
    """Return the menu for a specific date, defaulting to today."""
    selected = _parse_date(target_date).isoformat()
    for item in _load():
        if item.get("date") == selected:
            return item
    return None


def get_weekly_lunch_menu(start_date: str | date | None = None) -> list[dict]:
    """Return the business-week menu for the week containing start_date."""
    selected = _parse_date(start_date)
    monday = selected - timedelta(days=selected.weekday())
    friday = monday + timedelta(days=4)
    return [
        item for item in _load()
        if monday.isoformat() <= str(item.get("date")) <= friday.isoformat()
    ]

