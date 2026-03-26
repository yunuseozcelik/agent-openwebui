from langchain_core.tools import tool

from tools.ifs_tools import get_real_lunch_menu


@tool
def get_lunch_menu(date: str = "today") -> str:
    """
    Yemekhane menusunu getirir.
    """
    return get_real_lunch_menu.invoke({"date": date})


@tool
def get_shuttle_times(route: str = "Merkez") -> str:
    """
    Servis kalkis saatlerini sorgular.
    Guzergahlar: 'Merkez', 'Batikent', 'Cayyolu', 'Kecioren'.
    """
    return (
        f"Servis Saatleri ({route})\n"
        "- Sabah: 07:45 (Semt Duragi)\n"
        "- Aksam: 18:15 (Ofis Onu)"
    )
