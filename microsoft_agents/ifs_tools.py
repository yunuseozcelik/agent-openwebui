"""
Microsoft Agent Framework icin IFS tool tanimlari.
Gercek IFS ERP API'sine baglanir (tools/ifs_client.py uzerinden).
"""

import sys
import os
import json
import random
from datetime import datetime
from typing import Annotated

from agent_framework import tool
from pydantic import Field

# Root projedeki tools/ paketinden ifs_client'i import et
# (Bu dosyanin adi da "tools" oldugu icin importlib ile yukleriz)
import importlib.util

_ifs_client_path = os.path.join(os.path.dirname(__file__), "..", "tools", "ifs_client.py")
_spec = importlib.util.spec_from_file_location("ifs_client", _ifs_client_path)
_ifs_client = importlib.util.module_from_spec(_spec)

# ifs_client icindeki config import'u icin root'u path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_spec.loader.exec_module(_ifs_client)

get_user_by_email = _ifs_client.get_user_by_email
get_user_detail = _ifs_client.get_user_detail
get_empno_from_email = _ifs_client.get_empno_from_email
get_part_detail = _ifs_client.get_part_detail
get_meal_list = _ifs_client.get_meal_list


# ============================================================
# HR TOOLS
# ============================================================

@tool(approval_mode="never_require")
def get_employee_info(
    user_email: Annotated[str, Field(description="Calisan e-posta adresi")],
) -> str:
    """Kullanicinin detayli personel bilgilerini IFS sisteminden getirir.
    Sicil no, ad soyad, birim, pozisyon, hizmet suresi, izin ozeti ve durum bilgilerini doner."""
    try:
        users = get_user_by_email(user_email)
        basic = users[0] if users else {}

        empno = basic.get("empNo", "")
        detail = {}
        if empno:
            details = get_user_detail(empno)
            detail = details[0] if details else {}

        info = {
            "sicil_no": detail.get("sicilNo", basic.get("empNo")),
            "ad_soyad": detail.get("adSoyad", basic.get("name")),
            "birim": detail.get("birim", basic.get("unit")),
            "pozisyon": detail.get("pozisyon", basic.get("position")),
            "mail": detail.get("mail", user_email),
            "hizmet_suresi_yil": detail.get("hizmetSuresi"),
            "toplam_izin": detail.get("toplamIzin"),
            "kullanilan_izin": detail.get("kullandigiIzin"),
            "kalan_izin": detail.get("kalanIzin"),
            "ecb_saat": detail.get("ecbSaat"),
            "mazeret_izin": detail.get("mazeretIzin"),
            "son_durum": detail.get("sonDurum"),
        }
        return json.dumps(info, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool(approval_mode="never_require")
def check_leave_balance(
    user_email: Annotated[str, Field(description="Calisan e-posta adresi")],
) -> str:
    """Kullanicinin gercek izin bakiyesini IFS sisteminden getirir.
    Toplam izin, kullanilan izin, kalan izin, mazeret izni ve ECB saat bilgilerini doner."""
    try:
        empno = get_empno_from_email(user_email)
        details = get_user_detail(empno)
        if not details:
            return json.dumps({"error": "Kullanici detay bilgisi bulunamadi."}, ensure_ascii=False)

        d = details[0]
        balance = {
            "sicil_no": d.get("sicilNo"),
            "ad_soyad": d.get("adSoyad"),
            "toplam_izin": d.get("toplamIzin"),
            "kullanilan_izin": d.get("kullandigiIzin"),
            "kalan_izin": d.get("kalanIzin"),
            "mazeret_izin": d.get("mazeretIzin"),
            "ecb_saat": d.get("ecbSaat"),
            "son_durum": d.get("sonDurum"),
        }
        return json.dumps(balance, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool(approval_mode="never_require")
def request_leave(
    start_date: Annotated[str, Field(description="Baslangic tarihi (YYYY-MM-DD)")],
    end_date: Annotated[str, Field(description="Bitis tarihi (YYYY-MM-DD)")],
    leave_type: Annotated[str, Field(description="Izin tipi: annual, sick, unpaid")] = "annual",
    reason: Annotated[str, Field(description="Izin nedeni")] = "",
) -> str:
    """Izin talebi olusturur."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    days = (end - start).days + 1

    request_id = f"LEAVE-{datetime.now().strftime('%Y%m%d%H%M')}"
    response = {
        "status": "pending_approval",
        "request_id": request_id,
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
        "type": leave_type,
        "approver": "Departman Muduru",
        "message": f"{days} gunluk izin talebiniz olusturuldu. Onay bekliyor.",
    }
    return json.dumps(response, ensure_ascii=False)


@tool(approval_mode="never_require")
def check_salary_slip(
    month: Annotated[str, Field(description="Ay (YYYY-MM formatinda, ornegin 2025-01)")] = "current",
) -> str:
    """Maas bordrosunu gosterir."""
    if month == "current":
        month = datetime.now().strftime("%Y-%m")

    slip = {
        "month": month,
        "gross_salary": 50000,
        "deductions": {"tax": 7500, "sgk": 5000, "other": 500},
        "net_salary": 37000,
        "payment_date": f"{month}-28",
        "status": "paid",
    }
    return json.dumps(slip, ensure_ascii=False)


# ============================================================
# IT TOOLS
# ============================================================

@tool(approval_mode="never_require")
def create_support_ticket(
    title: Annotated[str, Field(description="Talep basligi")],
    description: Annotated[str, Field(description="Detayli aciklama")],
    category: Annotated[str, Field(description="Kategori: hardware, software, network, access")] = "hardware",
    priority: Annotated[str, Field(description="Oncelik: low, medium, high, critical")] = "medium",
) -> str:
    """IT destek talebi olusturur."""
    ticket_id = f"INC-{random.randint(100000, 999999)}"
    sla_hours = {"low": 72, "medium": 24, "high": 8, "critical": 2}

    response = {
        "status": "created",
        "ticket_id": ticket_id,
        "category": category,
        "priority": priority,
        "sla": f"{sla_hours.get(priority, 24)} saat icinde cozulecek",
        "assigned_to": "IT Destek Ekibi",
        "created_at": datetime.now().isoformat(),
        "message": f"Talebiniz olusturuldu. Numara: {ticket_id}",
    }
    return json.dumps(response, ensure_ascii=False)


@tool(approval_mode="never_require")
def check_ticket_status(
    ticket_id: Annotated[str, Field(description="Talep numarasi (ornegin INC-123456)")],
) -> str:
    """Destek talebinin durumunu kontrol eder."""
    statuses = ["open", "in_progress", "waiting_user", "resolved"]
    status = random.choice(statuses)

    response = {
        "ticket_id": ticket_id,
        "status": status,
        "assigned_to": "IT Teknisyeni",
        "last_update": datetime.now().isoformat(),
    }
    return json.dumps(response, ensure_ascii=False)


@tool(approval_mode="never_require")
def request_equipment(
    equipment_type: Annotated[str, Field(description="Ekipman tipi: laptop, monitor, mouse, keyboard, headset")],
    quantity: Annotated[int, Field(description="Adet")] = 1,
    justification: Annotated[str, Field(description="Talep gerekçesi")] = "",
) -> str:
    """Donanim/ekipman talep eder."""
    request_id = f"EQ-{random.randint(10000, 99999)}"
    costs = {"laptop": 30000, "monitor": 8000, "mouse": 500, "keyboard": 1000, "headset": 1500}

    response = {
        "status": "pending_approval",
        "request_id": request_id,
        "equipment": equipment_type,
        "quantity": quantity,
        "estimated_cost": costs.get(equipment_type, 1000) * quantity,
        "approver": "Satin Alma Muduru",
        "message": f"{equipment_type} talebiniz olusturuldu. Onay bekliyor.",
    }
    return json.dumps(response, ensure_ascii=False)


# ============================================================
# FINANCE TOOLS
# ============================================================

@tool(approval_mode="never_require")
def request_advance_payment(
    amount: Annotated[float, Field(description="Talep edilen miktar (TL)")],
    reason: Annotated[str, Field(description="Avans nedeni")],
    repayment_months: Annotated[int, Field(description="Kac ay taksitle geri odeme (1-12)")] = 3,
) -> str:
    """Avans (on odeme) talebi olusturur."""
    request_id = f"ADV-{random.randint(10000, 99999)}"
    monthly_payment = amount / repayment_months

    response = {
        "status": "pending_approval",
        "request_id": request_id,
        "amount": amount,
        "monthly_payment": round(monthly_payment, 2),
        "repayment_months": repayment_months,
        "approver": "Finans Muduru",
        "message": f"{amount} TL avans talebiniz olusturuldu.",
    }
    return json.dumps(response, ensure_ascii=False)


@tool(approval_mode="never_require")
def check_expense_status(
    expense_id: Annotated[str, Field(description="Harcama numarasi")] = "last",
) -> str:
    """Harcama talebinin durumunu kontrol eder."""
    if expense_id == "last":
        expense_id = f"EXP-{random.randint(10000, 99999)}"

    response = {
        "expense_id": expense_id,
        "status": "approved",
        "amount": 2500,
        "category": "Yol masrafi",
        "payment_date": "2025-01-25",
        "message": "Harcaniz onaylandi.",
    }
    return json.dumps(response, ensure_ascii=False)


# ============================================================
# GENERAL TOOLS
# ============================================================

@tool(approval_mode="never_require")
def get_lunch_menu(
    date: Annotated[str, Field(description="Tarih ('today' veya DD.MM.YYYY)")] = "today",
) -> str:
    """Yemekhane menusunu IFS sisteminden getirir."""
    try:
        meals = get_meal_list()
        current_date = datetime.now().strftime("%d.%m.%Y")
        target_date = current_date if date == "today" else date

        today_meal = None
        all_meals = []
        for m in meals:
            meal_entry = {
                "tarih": m.get("tarih"),
                "yemek1": m.get("yemek1"),
                "yemek2": m.get("yemek2"),
                "yemek3": m.get("yemek3"),
                "yemek4": m.get("yemek4"),
                "toplam_kalori": m.get("toplamKalori"),
            }
            all_meals.append(meal_entry)
            if m.get("tarih") == target_date:
                today_meal = meal_entry

        result = {
            "istenen_tarih": target_date,
            "bugunun_menusu": today_meal,
            "toplam_gun": len(all_meals),
            "tum_menuler": all_meals,
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool(approval_mode="never_require")
def lookup_part_detail(
    parcano: Annotated[str, Field(description="Parca numarasi")],
) -> str:
    """IFS sisteminden parca detay bilgisi getirir."""
    try:
        parts = get_part_detail(parcano)
        if not parts:
            return json.dumps({"error": f"{parcano} numarali parca bulunamadi."}, ensure_ascii=False)

        result = []
        for p in parts:
            result.append({
                "parca_no": p.get("parcaNo"),
                "aciklama": p.get("aciklama"),
                "eo": p.get("eo"),
                "teknik_koordinator": p.get("teknikKoordinator"),
                "urun_kodu": p.get("urunKodu"),
                "tip_kodu": p.get("tipKodu"),
            })
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================
# TOOL GRUPLARI (Agent'lara atanmak icin)
# ============================================================

HR_TOOLS = [get_employee_info, check_leave_balance, request_leave, check_salary_slip]
IT_TOOLS = [create_support_ticket, check_ticket_status, request_equipment]
FINANCE_TOOLS = [request_advance_payment, check_expense_status]
GENERAL_TOOLS = [get_lunch_menu, lookup_part_detail]
