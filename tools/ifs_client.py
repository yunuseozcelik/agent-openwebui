import requests
import time
from typing import List, Dict, Any
from config import IFS_API_BASE_URL, IFS_API_TIMEOUT, IFS_AUTH_URL, IFS_CLIENT_ID, IFS_CLIENT_SECRET

# Token cache
_token_cache = {
    "token": None,
    "expires_at": 0,
}


def _get_token() -> str:
    """Login endpoint'inden Bearer token alır ve cache'ler."""
    now = time.time()

    # Cache'de geçerli token varsa onu döndür
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        print("[IFS AUTH] Cache'den token kullaniliyor")
        return _token_cache["token"]

    if not IFS_CLIENT_ID or not IFS_CLIENT_SECRET:
        print("[IFS AUTH] HATA: IFS_CLIENT_ID veya IFS_CLIENT_SECRET bos!")
        raise ValueError("IFS_CLIENT_ID ve IFS_CLIENT_SECRET .env dosyasında tanımlanmalıdır.")

    payload = {
        "clientId": IFS_CLIENT_ID,
        "Secret": IFS_CLIENT_SECRET,
    }
    response = requests.post(IFS_AUTH_URL, json=payload, timeout=IFS_API_TIMEOUT)
    if not response.ok:
        print(f"[IFS AUTH] HATA: HTTP {response.status_code} - {response.text}")
        raise ValueError(f"IFS Auth hatasi: HTTP {response.status_code} - {response.text}")

    data = response.json()
    # API yanıtı: {"isSuccess": true, "data": {"token": "..."}} formatında
    inner = data.get("data") or {}
    token = inner.get("token") or data.get("token") or data.get("accessToken") or data.get("access_token")
    if not token:
        print(f"[IFS AUTH] HATA: Token response'da bulunamadi. Response: {data}")
        raise ValueError(f"Token response'da bulunamadi. Response: {data}")

    # Token'ı 55 dakika cache'le (genelde 60 dk geçerlidir)
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + 55 * 60

    print(f"[IFS AUTH] Token basariyla alindi (ilk 20 karakter: {token[:20]}...)")
    return token


def _headers() -> Dict[str, str]:
    """Her API isteği için Authorization header'lı headers döner."""
    token = _get_token()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def get_user_by_email(email: str) -> List[Dict[str, Any]]:
    """
    GET /api/user/{email}
    Returns: [{empNo, name, unit, position}]
    """
    url = f"{IFS_API_BASE_URL}/api/user/{email}"
    response = requests.get(url, headers=_headers(), timeout=IFS_API_TIMEOUT)
    if not response.ok:
        raise ValueError(f"IFS API hatasi: HTTP {response.status_code}")
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Beklenmeyen veri formati: /api/user/")
    return data


def get_user_detail(badgeno: str) -> List[Dict[str, Any]]:
    """
    GET /api/User/Detail/{badgeno}
    Returns: [{sicilNo, adSoyad, birim, pozisyon, mail,
               hizmetSuresi, toplamIzin, kullandigiIzin, kalanIzin,
               ecbSaat, mazeretIzin, sonDurum}]
    """
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
    """Email -> empNo cevirici."""
    users = get_user_by_email(email)
    if not users:
        raise ValueError(f"Bu e-posta icin personel bulunamadi: {email}")
    empno = users[0].get("empNo")
    if not empno:
        raise ValueError("Kullanici kaydinda empNo alani bulunamadi.")
    return empno


def get_part_detail(parcano: str) -> List[Dict[str, Any]]:
    """
    GET /api/User/PartDetail/{parcano}
    Returns: [{parcaNo, aciklama, eo, teknikKoordinator, urunKodu, tipKodu}]
    """
    url = f"{IFS_API_BASE_URL}/api/User/PartDetail/{parcano}"
    response = requests.get(url, headers=_headers(), timeout=IFS_API_TIMEOUT)
    if not response.ok:
        raise ValueError(f"IFS API hatasi: HTTP {response.status_code}")
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Beklenmeyen veri formati: /api/User/PartDetail/")
    return data


def get_meal_list() -> List[Dict[str, Any]]:
    """
    GET /api/User/YemekListesi
    Returns: [{tarih, yemek1-4, toplamKalori, salata1-13}]
    """
    url = f"{IFS_API_BASE_URL}/api/User/YemekListesi"
    response = requests.get(url, headers=_headers(), timeout=IFS_API_TIMEOUT)
    if not response.ok:
        raise ValueError(f"IFS API hatasi: HTTP {response.status_code}")
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Beklenmeyen veri formati: /api/User/YemekListesi")
    return data
