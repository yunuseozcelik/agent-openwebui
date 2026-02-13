# openwebui/ifs_pipeline.py
import os
import sys
import datetime
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
from langchain_core.messages import SystemMessage 

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

class Pipeline:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.name = "🏢 Kurumsal IFS Asistanı (v2)"
        self.graph = None
        self.valves = self.Valves()

    async def on_startup(self):
        print(f"Pipeline Baslatiliyor: {self.name}")
        try:
            from graph.builder import build_graph
            self.graph = build_graph()
            print("[OK] Supervisor Graph Basariyla Derlendi!")
        except ImportError as e:
            print(f"[HATA] {e}")

    async def on_shutdown(self):
        print(f"Pipeline Durduruldu: {self.name}")

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        
        if not self.graph:
            return "Sistem Hatası: AI Beyni yüklenemedi."

        user_data = body.get("user", {})
        user_name = user_data.get("name", "Değerli Çalışan")
        user_email = user_data.get("email", "bilinmiyor")
        
        # Tarih ve Saat
        now = datetime.datetime.now()
        current_time = now.strftime("%d %B %Y, %H:%M")
        day_name = now.strftime("%A") 

       
        context_prompt = (
            f"SİSTEM BİLGİSİ:\n"
            f"- Konuştuğun Kullanıcı: {user_name} ({user_email})\n"
            f"- Şu Anki Tarih ve Saat: {current_time} ({day_name})\n"
            f"- Sen kurumsal bir asistansın. Kullanıcıya ismiyle hitap et.\n"
        )

        graph_inputs = {
            "messages": [
                SystemMessage(content=context_prompt), # Gizli sistem bilgisi
                ("user", user_message)
            ],
            "user_context": {
                "user_name": user_name,
                "user_email": user_email,
                "current_date": now.strftime("%Y-%m-%d"),
            }
        }
        
        thread_id = user_email if user_email != "bilinmiyor" else "default_user"
        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = self.graph.invoke(graph_inputs, config=config)
            last_message = result["messages"][-1]
            return last_message.content

        except Exception as e:
            return f"İşlem Hatası: {str(e)}"