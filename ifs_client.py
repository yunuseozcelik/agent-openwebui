"""IFS ERP API client - explicit real mode or explicit mock mode."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any

import requests

from config import (
    IFS_API_BASE_URL,
    IFS_API_TIMEOUT,
    IFS_AUTH_URL,
    IFS_CLIENT_ID,
    IFS_CLIENT_SECRET,
    IFS_FORCE_MOCK_MODE,
)


HAS_IFS_CREDENTIALS = bool(IFS_CLIENT_ID and IFS_CLIENT_SECRET)
MOCK_MODE = IFS_FORCE_MOCK_MODE
MOCK_USER_EMAIL = "demo.user@sirket.com"
MOCK_USER_NAME = "Demo Kullanici"

if MOCK_MODE:
    print("[IFS] Mock mod explicit olarak aktif - ornek veri kullanilacak.")
elif not HAS_IFS_CREDENTIALS:
    print("[IFS] Gercek IFS credential'lari bulunamadi. IFS sorgulari hata dondurecek.")


_token_cache = {
    "token": None,
    "expires_at": 0,
}


def _require_real_ifs_config() -> None:
    if MOCK_MODE:
        return
    if not HAS_IFS_CREDENTIALS:
        raise ValueError(
            "Gercek IFS kullanimi icin IFS_CLIENT_ID ve IFS_CLIENT_SECRET gerekli. "
            "Mock test istiyorsan IFS_FORCE_MOCK_MODE=true kullan."
        )


def _get_token() -> str:
    """Fetches and caches the Bearer token from the FNSS auth service."""
    now = time.time()

    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    _require_real_ifs_config()

    payload = {
        "clientId": IFS_CLIENT_ID,
        "Secret": IFS_CLIENT_SECRET,
    }
    response = requests.post(IFS_AUTH_URL, json=payload, timeout=IFS_API_TIMEOUT)
    if not response.ok:
        raise ValueError(f"IFS Auth hatasi: HTTP {response.status_code} - {response.text}")

    data = response.json()
    inner = data.get("data") or {}
    token = inner.get("token") or data.get("token") or data.get("accessToken") or data.get("access_token")
    if not token:
        raise ValueError(f"Token response'da bulunamadi. Response: {data}")

    _token_cache["token"] = token
    _token_cache["expires_at"] = now + 55 * 60
    print("[IFS AUTH] Token basariyla alindi.")
    return token


def _headers() -> dict[str, str]:
    token = _get_token()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def get_user_by_email(email: str) -> list[dict[str, Any]]:
    if MOCK_MODE:
        return [
            {
                "empNo": "12345",
                "name": MOCK_USER_NAME,
                "unit": "Muhendislik",
                "position": "Kidemli Muhendis",
            }
        ]

    _require_real_ifs_config()
    url = f"{IFS_API_BASE_URL}/api/user/{email}"
    response = requests.get(url, headers=_headers(), timeout=IFS_API_TIMEOUT)
    if not response.ok:
        raise ValueError(f"IFS API hatasi: HTTP {response.status_code}")
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Beklenmeyen veri formati: /api/user/")
    return data


def get_user_detail(badgeno: str) -> list[dict[str, Any]]:
    if MOCK_MODE:
        return [
            {
                "sicilNo": badgeno or "12345",
                "adSoyad": MOCK_USER_NAME,
                "birim": "Muhendislik",
                "pozisyon": "Kidemli Muhendis",
                "mail": MOCK_USER_EMAIL,
                "hizmetSuresi": "8 Yil 3 Ay",
                "toplamIzin": 24,
                "kullandigiIzin": 9,
                "kalanIzin": 15,
                "ecbSaat": 12.5,
                "mazeretIzin": 2,
                "sonDurum": "Aktif",
            }
        ]

    _require_real_ifs_config()
    if len(badgeno) == 4:
        badgeno = f"0{badgeno}"
    elif len(badgeno) != 5:
        raise ValueError("Sicil numarasi 4 veya 5 haneli olmalidir.")

    url = f"{IFS_API_BASE_URL}/api/User/Detail/{badgeno}"
    response = requests.get(url, headers=_headers(), timeout=IFS_API_TIMEOUT)
    if not response.ok:
        raise ValueError(f"IFS API hatasi: HTTP {response.status_code}")
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Beklenmeyen veri formati: /api/User/Detail/")
    return data


def get_empno_from_email(email: str) -> str:
    if MOCK_MODE:
        return "12345"

    _require_real_ifs_config()
    users = get_user_by_email(email)
    if not users:
        raise ValueError(f"Bu e-posta icin personel bulunamadi: {email}")
    empno = users[0].get("empNo")
    if not empno:
        raise ValueError("Kullanici kaydinda empNo alani bulunamadi.")
    return empno


def get_part_detail(parcano: str) -> list[dict[str, Any]]:
    if MOCK_MODE:
        return [
            {
                "parcaNo": parcano,
                "aciklama": "Hidrolik Pompa Modulu",
                "eo": "EO-2024-0158",
                "teknikKoordinator": "Mehmet Demir",
                "urunKodu": "HPM-300",
                "tipKodu": "TIP-A",
            }
        ]

    _require_real_ifs_config()
    url = f"{IFS_API_BASE_URL}/api/User/PartDetail/{parcano}"
    response = requests.get(url, headers=_headers(), timeout=IFS_API_TIMEOUT)
    if not response.ok:
        raise ValueError(f"IFS API hatasi: HTTP {response.status_code}")
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Beklenmeyen veri formati: /api/User/PartDetail/")
    return data


def get_meal_list() -> list[dict[str, Any]]:
    if MOCK_MODE:
        today = datetime.now()
        meals = []
        menu_data = [
            ("Mercimek Corbasi", "Tavuk Sote", "Pilav", "Ayran", 650),
            ("Domates Corbasi", "Kofte", "Makarna", "Komposto", 720),
            ("Ezogelin Corbasi", "Izgara Tavuk", "Bulgur Pilavi", "Cacik", 680),
            ("Yayla Corbasi", "Etli Nohut", "Pirinc Pilavi", "Salata", 710),
            ("Sehriye Corbasi", "Tas Kebabi", "Patates Pure", "Ayran", 750),
        ]
        for i in range(5):
            d = today + timedelta(days=i)
            m = menu_data[i]
            meals.append(
                {
                    "tarih": d.strftime("%d.%m.%Y"),
                    "yemek1": m[0],
                    "yemek2": m[1],
                    "yemek3": m[2],
                    "yemek4": m[3],
                    "toplamKalori": m[4],
                }
            )
        return meals

    _require_real_ifs_config()
    url = f"{IFS_API_BASE_URL}/api/User/YemekListesi"
    response = requests.get(url, headers=_headers(), timeout=IFS_API_TIMEOUT)
    if not response.ok:
        raise ValueError(f"IFS API hatasi: HTTP {response.status_code}")
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Beklenmeyen veri formati: /api/User/YemekListesi")
    return data
