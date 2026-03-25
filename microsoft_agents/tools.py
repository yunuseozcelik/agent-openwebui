"""
Azure AI Agent Service icin tool tanimlari.
Mevcut LangGraph projesindeki tool'larin sadeleştirilmiş versiyonlari.
"""

import json
import random
from datetime import datetime
from typing import Any


# ============================================================
# TOOL FONKSIYONLARI (Agent cagirdiginda calisacak kodlar)
# ============================================================

def check_leave_balance(employee_email: str) -> str:
    """
    Calisanin kalan izin bakiyesini sorgular.

    Args:
        employee_email: Calisan e-posta adresi
    """
    response = {
        "employee": employee_email,
        "annual_leave": 14,
        "used": 5,
        "remaining": 9,
        "sick_leave_remaining": 10,
        "message": f"{employee_email} icin izin bakiyesi getirildi."
    }
    return json.dumps(response, ensure_ascii=False)


def create_leave_request(
    employee_email: str,
    leave_type: str,
    start_date: str,
    days: int
) -> str:
    """
    Izin talebi olusturur.

    Args:
        employee_email: Calisan e-posta adresi
        leave_type: Izin turu (annual, sick, unpaid)
        start_date: Baslangic tarihi (YYYY-MM-DD)
        days: Gun sayisi
    """
    request_id = f"LEAVE-{random.randint(10000, 99999)}"
    response = {
        "status": "pending_approval",
        "request_id": request_id,
        "employee": employee_email,
        "leave_type": leave_type,
        "start_date": start_date,
        "days": days,
        "approver": "Departman Muduru",
        "message": f"{days} gunluk {leave_type} izin talebi olusturuldu. Talep No: {request_id}"
    }
    return json.dumps(response, ensure_ascii=False)


def create_support_ticket(
    title: str,
    description: str,
    category: str = "hardware",
    priority: str = "medium"
) -> str:
    """
    IT destek talebi olusturur.

    Args:
        title: Talep basligi
        description: Detayli aciklama
        category: Kategori (hardware, software, network, access)
        priority: Oncelik (low, medium, high, critical)
    """
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
        "message": f"Talebiniz olusturuldu. Numara: {ticket_id}"
    }
    return json.dumps(response, ensure_ascii=False)


def request_equipment(
    equipment_type: str,
    quantity: int = 1,
    justification: str = ""
) -> str:
    """
    Donanim/ekipman talep eder.

    Args:
        equipment_type: Ekipman tipi (laptop, monitor, mouse, keyboard, headset)
        quantity: Adet
        justification: Gerekce
    """
    request_id = f"EQ-{random.randint(10000, 99999)}"
    costs = {
        "laptop": 30000, "monitor": 8000, "mouse": 500,
        "keyboard": 1000, "headset": 1500
    }

    response = {
        "status": "pending_approval",
        "request_id": request_id,
        "equipment": equipment_type,
        "quantity": quantity,
        "estimated_cost": costs.get(equipment_type, 1000) * quantity,
        "approver": "Satin Alma Muduru",
        "message": f"{equipment_type} talebiniz olusturuldu. Onay bekliyor."
    }
    return json.dumps(response, ensure_ascii=False)


# ============================================================
# TOOL TANIMLARI (Azure AI Agent Service JSON Schema formati)
# ============================================================

HR_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_leave_balance",
            "description": "Calisanin kalan yillik izin, hastalik izni bakiyesini sorgular",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_email": {
                        "type": "string",
                        "description": "Calisan e-posta adresi"
                    }
                },
                "required": ["employee_email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_leave_request",
            "description": "Izin talebi olusturur (yillik izin, hastalik izni, ucretsiz izin)",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_email": {
                        "type": "string",
                        "description": "Calisan e-posta adresi"
                    },
                    "leave_type": {
                        "type": "string",
                        "enum": ["annual", "sick", "unpaid"],
                        "description": "Izin turu"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Baslangic tarihi (YYYY-MM-DD)"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Gun sayisi"
                    }
                },
                "required": ["employee_email", "leave_type", "start_date", "days"]
            }
        }
    }
]

IT_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "IT destek talebi olusturur (donanim, yazilim, ag, erisim)",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Talep basligi"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detayli aciklama"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["hardware", "software", "network", "access"],
                        "description": "Kategori"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Oncelik"
                    }
                },
                "required": ["title", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_equipment",
            "description": "Donanim/ekipman talep eder (laptop, monitor, mouse, klavye, kulaklik)",
            "parameters": {
                "type": "object",
                "properties": {
                    "equipment_type": {
                        "type": "string",
                        "enum": ["laptop", "monitor", "mouse", "keyboard", "headset"],
                        "description": "Ekipman tipi"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Adet",
                        "default": 1
                    },
                    "justification": {
                        "type": "string",
                        "description": "Talep gerekçesi"
                    }
                },
                "required": ["equipment_type"]
            }
        }
    }
]

# Fonksiyon adi -> fonksiyon eslestirmesi (tool call'lari calistirmak icin)
TOOL_FUNCTIONS = {
    "check_leave_balance": check_leave_balance,
    "create_leave_request": create_leave_request,
    "create_support_ticket": create_support_ticket,
    "request_equipment": request_equipment,
}
