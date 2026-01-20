from langchain_core.tools import tool
from datetime import datetime, timedelta
import json

@tool
def check_leave_balance(user_id: str = "current_user"):
    """
    Kullanıcının izin bakiyesini gösterir.
    Yıllık izin, hastalık izni, kullanılan izin bilgilerini içerir.
    """
    # Mock data (Gerçekte veritabanından gelecek)
    balance = {
        "user_id": user_id,
        "annual_leave": 14,
        "sick_leave": 5,
        "used_leave": 8,
        "pending_requests": 2,
        "last_leave": "2025-01-10"
    }
    return json.dumps(balance, ensure_ascii=False)

@tool
def request_leave(
    start_date: str,
    end_date: str,
    leave_type: str = "annual",
    reason: str = ""
):
    """
    İzin talebi oluşturur.
    
    Args:
        start_date: Başlangıç tarihi (YYYY-MM-DD)
        end_date: Bitiş tarihi (YYYY-MM-DD)
        leave_type: İzin tipi (annual, sick, unpaid)
        reason: İzin nedeni
    """
    # Tarih kontrolü
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
        "approver": "Mehmet Yılmaz (Müdür)",
        "message": f"{days} günlük izin talebiniz oluşturuldu. Onay bekliyor."
    }
    return json.dumps(response, ensure_ascii=False)

@tool
def check_salary_slip(month: str = "current"):
    """
    Maaş bordrosunu gösterir.
    
    Args:
        month: Ay (YYYY-MM formatında, örn: 2025-01)
    """
    if month == "current":
        month = datetime.now().strftime("%Y-%m")
    
    slip = {
        "month": month,
        "gross_salary": 50000,
        "deductions": {
            "tax": 7500,
            "sgk": 5000,
            "other": 500
        },
        "net_salary": 37000,
        "payment_date": f"{month}-28",
        "status": "paid"
    }
    return json.dumps(slip, ensure_ascii=False)