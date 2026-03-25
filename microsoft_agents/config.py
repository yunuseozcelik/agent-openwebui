import os
from dotenv import load_dotenv

load_dotenv()

# Azure AI Foundry Project endpoint
# Ornek: "https://<project-name>.services.ai.azure.com/api/projects/<project-id>"
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")

# Azure OpenAI deployment adi (ornegin "gpt-4o")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

# Opsiyonel: Azure OpenAI icin ayri endpoint ve key (agent-framework icin)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
