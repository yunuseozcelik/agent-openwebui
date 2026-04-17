import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_COPILOT_MODEL = os.getenv("OPENAI_COPILOT_MODEL", "gpt-4o")
OPENAI_WORKER_MODEL = os.getenv("OPENAI_WORKER_MODEL", "gpt-4o-mini")

# Azure AI Foundry (opsiyonel - deploy icin)
FOUNDRY_PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
