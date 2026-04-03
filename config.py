import os
from dotenv import load_dotenv

load_dotenv()


def _split_csv_env(name: str, default: str = "") -> list[str]:
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_PLANNER_MODEL = os.getenv("OPENAI_PLANNER_MODEL", "gpt-5.2")
OPENAI_WORKER_MODEL = os.getenv("OPENAI_WORKER_MODEL", "gpt-4o-mini")

# API / Runtime
CORS_ALLOW_ORIGINS = _split_csv_env(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080,http://localhost:8106,http://127.0.0.1:8106",
)
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "40"))
WORKFLOW_SESSION_TTL_SECONDS = int(os.getenv("WORKFLOW_SESSION_TTL_SECONDS", "14400"))
MAX_WORKFLOW_SESSIONS = int(os.getenv("MAX_WORKFLOW_SESSIONS", "500"))
AGENT_ALLOWED_EMAILS = _split_csv_env("AGENT_ALLOWED_EMAILS", "")

# IFS ERP API
IFS_API_BASE_URL = os.getenv("IFS_API_BASE_URL", "https://commonapi.fnss.com.tr")
IFS_API_TIMEOUT = int(os.getenv("IFS_API_TIMEOUT", "15"))
IFS_AUTH_URL = os.getenv("IFS_AUTH_URL", "https://fnssaiservice.fnss.com.tr/api/Auth/Login")
IFS_CLIENT_ID = os.getenv("IFS_CLIENT_ID", "")
IFS_CLIENT_SECRET = os.getenv("IFS_CLIENT_SECRET", "")
IFS_FORCE_MOCK_MODE = os.getenv("IFS_FORCE_MOCK_MODE", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
