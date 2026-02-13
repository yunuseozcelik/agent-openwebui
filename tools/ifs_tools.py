from langchain_core.tools import tool
from datetime import datetime
import json
from tools.ifs_client import get_part_detail, get_meal_list, get_user_by_email, get_user_detail, get_empno_from_email


@tool
def lookup_user_info(email: str) -> str:
    """
    IFS sisteminden e-posta adresi ile kullanıcı bilgisi getirir.
    Sicil no, ad soyad, birim ve pozisyon bilgilerini döner.

    Args:
        email: Kullanıcının e-posta adresi
    """
    try:
        users = get_user_by_email(email)
        if not users:
            return json.dumps({"error": f"{email} icin kullanici bulunamadi."}, ensure_ascii=False)

        result = []
        for u in users:
            result.append({
                "sicil_no": u.get("empNo"),
                "ad_soyad": u.get("name"),
                "birim": u.get("unit"),
                "pozisyon": u.get("position"),
            })
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Sistem hatasi: {str(e)}"}, ensure_ascii=False)


@tool
def lookup_user_detail(badgeno: str = "", email: str = "") -> str:
    """
    IFS sisteminden personel detay bilgisi getirir.
    Sicil no veya e-posta ile sorgulama yapılabilir.
    İzin bilgileri, hizmet süresi, ECB saat, son durum gibi detayları döner.

    Args:
        badgeno: Sicil numarası (4 veya 5 haneli). Boş bırakılırsa email kullanılır.
        email: Kullanıcının e-posta adresi. badgeno verilmezse email'den sicil no bulunur.
    """
    try:
        if not badgeno and not email:
            return json.dumps({"error": "Sicil numarasi veya e-posta adresi gereklidir."}, ensure_ascii=False)

        if not badgeno:
            badgeno = get_empno_from_email(email)

        users = get_user_detail(badgeno)
        if not users:
            return json.dumps({"error": f"{badgeno} icin detay bulunamadi."}, ensure_ascii=False)

        result = []
        for u in users:
            result.append({
                "sicil_no": u.get("sicilNo"),
                "ad_soyad": u.get("adSoyad"),
                "birim": u.get("birim"),
                "pozisyon": u.get("pozisyon"),
                "mail": u.get("mail"),
                "hizmet_suresi": u.get("hizmetSuresi"),
                "toplam_izin": u.get("toplamIzin"),
                "kullandigi_izin": u.get("kullandigiIzin"),
                "kalan_izin": u.get("kalanIzin"),
                "ecb_saat": u.get("ecbSaat"),
                "mazeret_izin": u.get("mazeretIzin"),
                "son_durum": u.get("sonDurum"),
            })
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Sistem hatasi: {str(e)}"}, ensure_ascii=False)


@tool
def lookup_part_detail(parcano: str) -> str:
    """
    IFS sisteminden parça detay bilgisi getirir.
    Parça no, açıklama, EO, teknik koordinatör, ürün kodu ve tip kodu bilgilerini döner.

    Args:
        parcano: Parça numarası
    """
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
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Sistem hatasi: {str(e)}"}, ensure_ascii=False)


@tool
def get_real_lunch_menu(date: str = "today") -> str:
    """
    FNSS yemekhane menüsünü IFS sisteminden getirir.
    2 haftalık menü listesi döner ve bugünün menüsünü işaretler.

    Args:
        date: Tarih ('today' = bugün, veya DD.MM.YYYY formatında)
    """
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
                "is_today": m.get("tarih") == current_date,
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
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Sistem hatasi: {str(e)}"}, ensure_ascii=False)
