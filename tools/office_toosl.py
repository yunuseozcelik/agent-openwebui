from langchain_core.tools import tool
from datetime import datetime

@tool
def get_lunch_menu(date: str = "today") -> str:
    """
    Şirket yemekhanesindeki günün menüsünü getirir.
    Kullanıcı 'Bugün yemekte ne var?' veya 'Yarın yemek ne?' diye sorabilir.
    """
    # Bugünün tarihi
    today = datetime.now().strftime("%Y-%m-%d")
    
    if "today" in date or date == today:
        return ("🍽️ **Günün Menüsü:**\n"
                "- Mercimek Çorbası\n"
                "- Hünkar Beğendi\n"
                "- Pirinç Pilavı\n"
                "- Mevsim Salata\n"
                "- Kemalpaşa Tatlısı")
    else:
        return ("🍽️ **Yarının Menüsü:**\n"
                "- Ezogelin Çorba\n"
                "- Izgara Tavuk\n"
                "- Bulgur Pilavı\n"
                "- Yoğurt\n"
                "- Meyve")

@tool
def get_shuttle_times(route: str = "Merkez") -> str:
    """
    Servis kalkış saatlerini sorgular.
    Güzergahlar: 'Merkez', 'Batıkent', 'Çayyolu', 'Keçiören'.
    """
    return (f"🚌 **{route} Servis Saatleri:**\n"
            "- Sabah: 07:45 (Semt Durağı)\n"
            "- Akşam: 18:15 (Ofis Önü)")