# openwebui/ifs_pipeline.py
import os
import sys
import datetime # Tarih için ekledik
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
from langchain_core.messages import SystemMessage # System mesajı eklemek için

# --- PATH AYARI ---
# Open WebUI bu dosyayı çalıştırdığında, ana proje klasörünü görmesi lazım.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) # Bir üst klasör (ifs_corporate_ai)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Şimdi kendi modüllerimizi import edebiliriz
try:
    from graph.builder import build_graph
    from config.settings import settings
    print("✅ IFS Corporate AI Modülleri Yüklendi.")
except ImportError as e:
    print(f"❌ Modül Yükleme Hatası: {e}")
    build_graph = None


class Pipeline:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.name = "🏢 Kurumsal IFS Asistanı (v2)"
        self.graph = None
        self.valves = self.Valves()

    async def on_startup(self):
        print(f"Pipeline Başlatılıyor: {self.name}")
        try:
            from graph.builder import build_graph
            self.graph = build_graph()
            print("🧠 Supervisor Graph Başarıyla Derlendi!")
        except ImportError as e:
            print(f"❌ Hata: {e}")

    async def on_shutdown(self):
        print(f"Pipeline Durduruldu: {self.name}")

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        
        if not self.graph:
            return "Sistem Hatası: AI Beyni yüklenemedi."

        # --- 1. KULLANICI BİLGİLERİNİ AL ---
        user_data = body.get("user", {})
        user_name = user_data.get("name", "Değerli Çalışan")
        user_email = user_data.get("email", "bilinmiyor")
        
        # Tarih ve Saat
        now = datetime.datetime.now()
        current_time = now.strftime("%d %B %Y, %H:%M") # Örn: 20 Ocak 2026, 15:30
        day_name = now.strftime("%A") # Gün ismi

        # --- 2. CONTEXT (BAĞLAM) OLUŞTUR ---
        # Bu mesaj kullanıcıya görünmez ama AI bunu "hafızasında" tutar.
        context_prompt = (
            f"SİSTEM BİLGİSİ:\n"
            f"- Konuştuğun Kullanıcı: {user_name} ({user_email})\n"
            f"- Şu Anki Tarih ve Saat: {current_time} ({day_name})\n"
            f"- Sen kurumsal bir asistansın. Kullanıcıya ismiyle hitap et.\n"
        )

        # Mesaj listesini hazırla
        # Eğer bu konuşmanın ilk mesajıysa context'i başa ekle, değilse sadece user message'ı yolla
        # LangGraph state'i genellikle kendi hafızasını tuttuğu için buraya her seferinde
        # SystemMessage eklemek yerine, graph içindeki promptlarda da kullanabilirsin.
        # Ancak en garantisi input'a eklemektir.
        
        graph_inputs = {
            "messages": [
                SystemMessage(content=context_prompt), # Gizli sistem bilgisi
                ("user", user_message)
            ]
        }
        
        # Thread ID (Hafıza sürekliliği)
        thread_id = user_email if user_email != "bilinmiyor" else "default_user"
        config = {"configurable": {"thread_id": thread_id}}

        try:
            # 3. Graph'ı Çalıştır
            result = self.graph.invoke(graph_inputs, config=config)
            last_message = result["messages"][-1]
            return last_message.content

        except Exception as e:
            return f"İşlem Hatası: {str(e)}"