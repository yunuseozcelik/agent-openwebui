"""Kurumsal yapi katalogu: Departman + Kademe -> Unvan + Rol.

Kurumsal kariyer kademesi Turkiye'deki standart sirket hiyerarsisine uygun
sekilde tanimlanmistir (Stajyer -> Direktor). Unvan ve yetki, secilen
departman ve kademeden otomatik turetilir.
"""

from __future__ import annotations

import re


DEPARTMENTS: list[dict] = [
    {"id": "HR",          "label": "Insan Kaynaklari",    "base_role": "hr"},
    {"id": "Finance",     "label": "Finans",              "base_role": "finance"},
    {"id": "IT",          "label": "Bilgi Teknolojileri", "base_role": "engineering"},
    {"id": "Engineering", "label": "Muhendislik",         "base_role": "engineering"},
    {"id": "General",     "label": "Idari Isler",         "base_role": "employee"},
]

# Kademe -> unvan sonek + yonetici mi
LEVELS: list[dict] = [
    {"id": "intern",     "label": "Stajyer",          "suffix": "Stajyeri",         "is_manager": False},
    {"id": "junior",     "label": "Uzman Yardimcisi", "suffix": "Uzman Yardimcisi", "is_manager": False},
    {"id": "specialist", "label": "Uzman",            "suffix": "Uzmani",           "is_manager": False},
    {"id": "senior",     "label": "Kidemli Uzman",    "suffix": "Kidemli Uzmani",   "is_manager": False},
    {"id": "manager",    "label": "Mudur",            "suffix": "Muduru",           "is_manager": True},
    {"id": "director",   "label": "Direktor",         "suffix": "Direktoru",        "is_manager": True},
]


def catalog() -> dict:
    return {"departments": DEPARTMENTS, "levels": LEVELS}


def department_by_id(dept_id: str) -> dict | None:
    return next((d for d in DEPARTMENTS if d["id"] == dept_id), None)


def level_by_id(level_id: str) -> dict | None:
    return next((l for l in LEVELS if l["id"] == level_id), None)


def resolve_title_and_role(department_id: str, level_id: str) -> tuple[str, str]:
    d = department_by_id(department_id)
    l = level_by_id(level_id)
    if not d:
        raise ValueError(f"Gecersiz departman: {department_id}")
    if not l:
        raise ValueError(f"Gecersiz kademe: {level_id}")
    title = f"{d['label']} {l['suffix']}"
    role = "manager" if l["is_manager"] else d["base_role"]
    return title, role


_TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def slugify_email(name: str, existing: set[str]) -> str:
    n = name.strip().translate(_TR_MAP).lower()
    n = re.sub(r"[^a-z0-9\s]", "", n)
    parts = [p for p in n.split() if p]
    if not parts:
        parts = ["user"]
    base = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
    email = f"{base}@fnss.com.tr"
    i = 2
    while email.lower() in existing:
        email = f"{base}{i}@fnss.com.tr"
        i += 1
    return email
