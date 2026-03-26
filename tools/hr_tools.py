from langchain_core.tools import tool
from datetime import datetime
import json
from tools.ifs_client import (
    MOCK_MODE,
    MOCK_USER_EMAIL,
    get_user_by_email,
    get_user_detail,
    get_empno_from_email,
)


@tool
def get_employee_info(user_email: str = "") -> str:
    """
    Kullanıcının detaylı personel bilgilerini IFS sisteminden getirir.
    Sicil no, ad soyad, birim, pozisyon, hizmet süresi, izin özeti ve durum bilgilerini döner.

    Args:
        user_email: Kullanıcının e-posta adresi (sistem mesajındaki context'ten alınmalı)
    """
    if not user_email and MOCK_MODE:
        user_email = MOCK_USER_EMAIL

    if not user_email:
        return json.dumps({"error": "E-posta adresi gerekli. Sistem mesajindaki kullanici bilgisinden alinmali."}, ensure_ascii=False)

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
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Sistem hatasi: {str(e)}"}, ensure_ascii=False)


@tool
def check_leave_balance(user_email: str = "") -> str:
    """
    Kullanıcının GERÇEK izin bakiyesini IFS sisteminden getirir.
    Toplam izin, kullanılan izin, kalan izin, mazeret izni ve ECB saat bilgilerini döner.

    Args:
        user_email: Kullanıcının e-posta adresi (sistem mesajındaki context'ten alınmalı)
    """
    if not user_email and MOCK_MODE:
        user_email = MOCK_USER_EMAIL

    if not user_email:
        return json.dumps({"error": "E-posta adresi gerekli. Sistem mesajindaki kullanici bilgisinden alinmali."}, ensure_ascii=False)

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
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Sistem hatasi: {str(e)}"}, ensure_ascii=False)


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
