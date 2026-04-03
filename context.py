"""OpenWebUI context extraction utility."""

import re
from typing import Optional, Dict


def extract_ow_context(messages: list) -> Dict[str, Optional[str]]:
    """
    Mesaj listesinden [OW_CONTEXT]...[/OW_CONTEXT] blogunu parse eder.
    Ayrica ifs_pipeline.py'nin 'SISTEM BILGISI' formatini da destekler.
    """
    context = {
        "user_name": None,
        "user_email": None,
        "current_date": None,
    }

    for msg in messages:
        content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
        if not content:
            continue

        # Format 1: [OW_CONTEXT] bloku (main.py uzerinden OpenWebUI)
        if "[OW_CONTEXT]" in content:
            match = re.search(r"\[OW_CONTEXT\](.*?)\[/OW_CONTEXT\]", content, re.DOTALL)
            if match:
                block = match.group(1)
                for line in block.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("User name:"):
                        context["user_name"] = line.split(":", 1)[1].strip()
                    elif line.startswith("User email:"):
                        context["user_email"] = line.split(":", 1)[1].strip()
                    elif "Current date" in line:
                        context["current_date"] = line.split(":", 1)[1].strip().split("(")[0].strip()
            break

        # Format 2: SISTEM BILGISI
        if "Konuştuğun Kullanıcı:" in content:
            name_match = re.search(r"Konuştuğun Kullanıcı:\s*(.+?)\s*\((.+?)\)", content)
            if name_match:
                context["user_name"] = name_match.group(1).strip()
                context["user_email"] = name_match.group(2).strip()
            date_match = re.search(r"Tarih ve Saat:\s*(.+?)(?:\n|$)", content)
            if date_match:
                context["current_date"] = date_match.group(1).strip()
            break

    return context
