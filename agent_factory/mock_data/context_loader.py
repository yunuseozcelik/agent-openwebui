"""Agent için ilgili mock veriyi context olarak yükler."""

from __future__ import annotations

import json
from pathlib import Path

from .lunch_menu import get_weekly_lunch_menu, get_lunch_menu

_MOCK_DATA_DIR = Path(__file__).parent


def _load_json(filename: str) -> dict | list | None:
    path = _MOCK_DATA_DIR / filename
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _name_matches(agent_name: str, keywords: list[str]) -> bool:
    name_lower = agent_name.lower()
    return any(kw in name_lower for kw in keywords)


def get_mock_context(agent_name: str, agent_id: str) -> str:
    """Agent adına göre ilgili mock veriyi döndürür. Yoksa boş string."""
    name = (agent_name or "").lower()

    # Yemek menüsü agentı
    if _name_matches(name, ["yemek", "menu", "menü", "lunch", "öğle", "ogle"]):
        weekly = get_weekly_lunch_menu()
        today = get_lunch_menu()
        lines = ["## MEVCUT YEMEKHANE VERISI (bu veriyi kullan, uydurma)\n"]
        if today:
            lines.append(f"**Bugünün menüsü ({today['date']}, {today['weekday']}):**")
            lines.append(f"- Çorba: {today['soup']}")
            lines.append(f"- Ana yemek: {today['main']}")
            lines.append(f"- Yan yemek: {today['side']}")
            lines.append(f"- Salata: {today['salad']}")
            lines.append(f"- Tatlı: {today['dessert']}")
            lines.append(f"- Kalori: {today['calories']} kcal\n")
        if weekly:
            lines.append("**Bu haftanın menüsü:**")
            for day in weekly:
                lines.append(
                    f"- {day['date']} {day['weekday']}: "
                    f"{day['soup']} | {day['main']} | {day['side']} | "
                    f"{day['salad']} | {day['dessert']} ({day['calories']} kcal)"
                )
        return "\n".join(lines)

    # HR agentı
    if _name_matches(name, ["hr", "personel", "insan", "izin", "leave"]):
        data = _load_json("hr_data.json")
        if data:
            return f"## MEVCUT HR VERİSİ\n```json\n{json.dumps(data, ensure_ascii=False, indent=2)[:2000]}\n```"

    # Satış/raporlama agentı
    if _name_matches(name, ["satis", "satış", "rapor", "report", "sales"]):
        data = _load_json("sales_data.json")
        if data:
            return f"## MEVCUT SATIŞ VERİSİ\n```json\n{json.dumps(data, ensure_ascii=False, indent=2)[:2000]}\n```"

    # Excel/veri analiz agentı
    if _name_matches(name, ["excel", "analiz", "veri", "data"]):
        data = _load_json("excel_data.json")
        if data:
            return f"## MEVCUT VERİ\n```json\n{json.dumps(data, ensure_ascii=False, indent=2)[:2000]}\n```"

    return ""
