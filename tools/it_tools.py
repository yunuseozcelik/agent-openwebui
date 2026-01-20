from langchain_core.tools import tool
from datetime import datetime
import json
import random

@tool
def create_support_ticket(
    title: str,
    description: str,
    category: str = "hardware",
    priority: str = "medium"
):
    """
    IT destek talebi oluşturur.
    
    Args:
        title: Talep başlığı
        description: Detaylı açıklama
        category: Kategori (hardware, software, network, access)
        priority: Öncelik (low, medium, high, critical)
    """
    ticket_id = f"INC-{random.randint(100000, 999999)}"
    
    # Önceliğe göre SLA (çözüm süresi)
    sla_hours = {"low": 72, "medium": 24, "high": 8, "critical": 2}
    
    response = {
        "status": "created",
        "ticket_id": ticket_id,
        "category": category,
        "priority": priority,
        "sla": f"{sla_hours[priority]} saat içinde çözülecek",
        "assigned_to": "IT Destek Ekibi",
        "created_at": datetime.now().isoformat(),
        "message": f"Talebiniz oluşturuldu. Numara: {ticket_id}"
    }
    return json.dumps(response, ensure_ascii=False)

@tool
def check_ticket_status(ticket_id: str):
    """
    Destek talebinin durumunu kontrol eder.
    
    Args:
        ticket_id: Talep numarası (örn: INC-123456)
    """
    # Mock data
    statuses = ["open", "in_progress", "waiting_user", "resolved"]
    status = random.choice(statuses)
    
    response = {
        "ticket_id": ticket_id,
        "status": status,
        "assigned_to": "Ahmet Kaya (IT Teknisyeni)",
        "last_update": datetime.now().isoformat(),
        "comments": [
            {"time": "10:30", "user": "Teknisyen", "text": "Sorun inceleniyor"},
            {"time": "14:15", "user": "Teknisyen", "text": "Parça sipariş edildi"}
        ]
    }
    return json.dumps(response, ensure_ascii=False)

@tool
def request_equipment(
    equipment_type: str,
    quantity: int = 1,
    justification: str = ""
):
    """
    Donanım/ekipman talep eder.
    
    Args:
        equipment_type: Ekipman tipi (laptop, monitor, mouse, keyboard, headset)
        quantity: Adet
        justification: Gerekçe
    """
    request_id = f"EQ-{random.randint(10000, 99999)}"
    
    # Ekipman maliyetleri (tahmini)
    costs = {
        "laptop": 30000,
        "monitor": 8000,
        "mouse": 500,
        "keyboard": 1000,
        "headset": 1500
    }
    
    response = {
        "status": "pending_approval",
        "request_id": request_id,
        "equipment": equipment_type,
        "quantity": quantity,
        "estimated_cost": costs.get(equipment_type, 1000) * quantity,
        "approver": "Satın Alma Müdürü",
        "message": f"{equipment_type} talebiniz oluşturuldu. Onay bekliyor."
    }
    return json.dumps(response, ensure_ascii=False)