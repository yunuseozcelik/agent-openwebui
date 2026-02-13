from langchain_core.tools import tool
from tools.ifs_tools import get_real_lunch_menu

# Gerçek yemek menüsü tool'u ifs_tools'tan geliyor
get_lunch_menu = get_real_lunch_menu


@tool
def get_shuttle_times(route: str = "Merkez") -> str:
    """
    Servis kalkış saatlerini sorgular.
    Güzergahlar: 'Merkez', 'Batıkent', 'Çayyolu', 'Keçiören'.
    """
    return (f"🚌 **{route} Servis Saatleri:**\n"
            "- Sabah: 07:45 (Semt Durağı)\n"
            "- Akşam: 18:15 (Ofis Önü)")
