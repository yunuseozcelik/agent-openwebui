from langchain_core.tools import tool
from datetime import datetime
import json
import random

@tool
def request_advance_payment(
    amount: float,
    reason: str,
    repayment_months: int = 3
):
    """
    Avans (ön ödeme) talebi oluşturur.
    
    Args:
        amount: Talep edilen miktar (TL)
        reason: Avans nedeni
        repayment_months: Kaç ay taksitle geri ödeme (1-12)
    """
    request_id = f"ADV-{random.randint(10000, 99999)}"
    monthly_payment = amount / repayment_months
    
    response = {
        "status": "pending_approval",
        "request_id": request_id,
        "amount": amount,
        "monthly_payment": round(monthly_payment, 2),
        "repayment_months": repayment_months,
        "approver": "Finans Müdürü",
        "message": f"{amount} TL avans talebiniz oluşturuldu."
    }
    return json.dumps(response, ensure_ascii=False)

@tool
def check_expense_status(expense_id: str = "last"):
    """
    Harcama talebinin durumunu kontrol eder.
    
    Args:
        expense_id: Harcama numarası (boş ise son harcama)
    """
    if expense_id == "last":
        expense_id = f"EXP-{random.randint(10000, 99999)}"
    
    response = {
        "expense_id": expense_id,
        "status": "approved",
        "amount": 2500,
        "category": "Yol masrafı",
        "payment_date": "2025-01-25",
        "message": "Harcamanız onaylandı, ödeme tarihi: 25 Ocak"
    }
    return json.dumps(response, ensure_ascii=False)

@tool
def submit_expense_report(
    expenses: list,
    total_amount: float,
    category: str = "travel"
):
    """
    Harcama raporu gönderir.
    
    Args:
        expenses: Harcama listesi [{"item": "Uçak", "amount": 1500}, ...]
        total_amount: Toplam tutar
        category: Kategori (travel, meal, accommodation, other)
    """
    report_id = f"EXP-{random.randint(10000, 99999)}"
    
    response = {
        "status": "submitted",
        "report_id": report_id,
        "total_amount": total_amount,
        "items_count": len(expenses),
        "approver": "Bölüm Müdürü",
        "message": f"Harcama raporu gönderildi. Numara: {report_id}"
    }
    return json.dumps(response, ensure_ascii=False)