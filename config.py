import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WOLFRAM_ALPHA_APPID = os.getenv("WOLFRAM_ALPHA_APPID")
IFS_API_BASE_URL = os.getenv("IFS_API_BASE_URL", "https://commonapi.fnss.com.tr")
IFS_API_TIMEOUT = int(os.getenv("IFS_API_TIMEOUT", "15"))

# IFS Auth
IFS_AUTH_URL = os.getenv("IFS_AUTH_URL", "https://fnssaiservice.fnss.com.tr/api/Auth/Login")
IFS_CLIENT_ID = os.getenv("IFS_CLIENT_ID", "")
IFS_CLIENT_SECRET = os.getenv("IFS_CLIENT_SECRET", "")
