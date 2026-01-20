# config/settings.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Key'i buraya varsayılan olarak koyabilirsin veya .env'den çeker
    OPENAI_API_KEY: str = "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" # Kendi keyini buraya yazabilirsin (test için)
    
    # Model İsimleri
    SUPERVISOR_MODEL: str = "gpt-4o"      # Yönetici zeki olmalı
    WORKER_MODEL: str = "gpt-4o-mini"     # İşçiler hızlı ve ucuz olabilir
    
    # Open WebUI Pipeline Ayarları
    PIPELINE_NAME: str = "IFS Kurumsal Asistan v2"

settings = Settings()