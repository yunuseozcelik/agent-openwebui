"""
IFS API Baglanti Testi
Kullanim: python test_ifs.py
VPN'e baglanip calistirin.
"""
import json
import sys
from tools.ifs_client import (
    get_meal_list,
    get_user_by_email,
    get_user_detail,
    get_empno_from_email,
    get_part_detail,
)

TEST_EMAIL = sys.argv[1] if len(sys.argv) > 1 else "yunus@fnss.com.tr"

results = {}

# 1) Yemek Listesi
print("\n[1/4] Yemek Listesi testi...")
try:
    meals = get_meal_list()
    print(f"  BASARILI - {len(meals)} gunluk menu geldi")
    if meals:
        m = meals[0]
        print(f"  Ornek: {m.get('tarih')} - {m.get('yemek1')}")
    results["yemek_listesi"] = "OK"
except Exception as e:
    print(f"  HATA: {e}")
    results["yemek_listesi"] = f"HATA: {e}"

# 2) Kullanici Bilgisi (email ile)
print(f"\n[2/4] Kullanici bilgisi testi ({TEST_EMAIL})...")
try:
    users = get_user_by_email(TEST_EMAIL)
    print(f"  BASARILI - {len(users)} kayit bulundu")
    if users:
        u = users[0]
        print(f"  Sicil: {u.get('empNo')} | Ad: {u.get('name')} | Birim: {u.get('unit')}")
    results["kullanici_bilgisi"] = "OK"
except Exception as e:
    print(f"  HATA: {e}")
    results["kullanici_bilgisi"] = f"HATA: {e}"

# 3) Kullanici Detay (sicil no ile)
print(f"\n[3/4] Kullanici detay testi (email -> sicil -> detay)...")
try:
    empno = get_empno_from_email(TEST_EMAIL)
    details = get_user_detail(empno)
    if details:
        d = details[0]
        print(f"  BASARILI - {d.get('adSoyad')}")
        print(f"  Birim: {d.get('birim')} | Pozisyon: {d.get('pozisyon')}")
        print(f"  Izin: {d.get('kalanIzin')} kalan / {d.get('toplamIzin')} toplam")
    results["kullanici_detay"] = "OK"
except Exception as e:
    print(f"  HATA: {e}")
    results["kullanici_detay"] = f"HATA: {e}"

# 4) Parca Detay (ornek parca no gerekli)
print("\n[4/4] Parca detay testi (ornek no: 12345678)...")
try:
    parts = get_part_detail("12345678")
    if parts:
        p = parts[0]
        print(f"  BASARILI - {p.get('parcaNo')} | {p.get('aciklama')}")
    else:
        print("  Sonuc bos ama API yanit verdi")
    results["parca_detay"] = "OK"
except Exception as e:
    print(f"  HATA: {e}")
    results["parca_detay"] = f"HATA: {e}"

# Ozet
print("\n" + "=" * 50)
print("SONUC OZETI:")
print("=" * 50)
for k, v in results.items():
    status = "BASARILI" if v == "OK" else "BASARISIZ"
    print(f"  {k:25s} -> {status}")

ok_count = sum(1 for v in results.values() if v == "OK")
print(f"\n{ok_count}/{len(results)} endpoint basarili")
