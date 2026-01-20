from langchain_core.tools import tool
import json
from datetime import datetime


@tool
def check_pending_approvals(user_role: str = "employee"):
    """
    Bekleyen onayları listeler.
    
    Args:
        user_role: Kullanıcı rolü (employee: kendi talepleri, manager: ekip talepleri)
    """
    if user_role == "manager":
        approvals = [
            {"id": "LEAVE-001", "type": "İzin", "requester": "Ali Yılmaz", "days": 5},
            {"id": "EQ-002", "type": "Ekipman", "requester": "Ayşe Demir", "item": "Laptop"},
            {"id": "ADV-003", "type": "Avans", "requester": "Mehmet Öz", "amount": 5000}
        ]
    else:
        approvals = [
            {"id": "LEAVE-123", "type": "İzin", "status": "Onay bekliyor", "days": 3},
            {"id": "EXP-456", "type": "Harcama", "status": "Onaylandı", "amount": 1200}
        ]
    
    return json.dumps({"pending_count": len(approvals), "items": approvals}, ensure_ascii=False)

@tool
def approve_request(request_id: str, comment: str = ""):
    """
    Talebi onaylar (sadece yöneticiler).
    
    Args:
        request_id: Talep numarası
        comment: Onay notu
    """
    response = {
        "status": "approved",
        "request_id": request_id,
        "approved_by": "current_manager",
        "approved_at": datetime.now().isoformat(),
        "comment": comment,
        "message": f"{request_id} numaralı talep onaylandı."
    }
    return json.dumps(response, ensure_ascii=False)

@tool
def reject_request(request_id: str, reason: str):
    """
    Talebi reddeder (sadece yöneticiler).
    
    Args:
        request_id: Talep numarası
        reason: Red nedeni
    """
    response = {
        "status": "rejected",
        "request_id": request_id,
        "rejected_by": "current_manager",
        "rejected_at": datetime.now().isoformat(),
        "reason": reason,
        "message": f"{request_id} numaralı talep reddedildi."
    }
    return json.dumps(response, ensure_ascii=False)