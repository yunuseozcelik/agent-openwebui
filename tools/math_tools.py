# tools/math_tools.py - WORKING VERSION
import requests
from langchain_core.tools import tool
from config import WOLFRAM_ALPHA_APPID

WOLFRAM_APP_ID = WOLFRAM_ALPHA_APPID
def query_wolfram_api(query: str) -> str:
    """
    Wolfram Alpha Simple API'ye direkt istek atar.
    """
    url = "http://api.wolframalpha.com/v1/result"
    params = {
        "appid": WOLFRAM_APP_ID,
        "i": query,
        "timeout": 10,
        "units": "metric"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            return response.text.strip()
        elif response.status_code == 501:
            return f"⚠️ Wolfram bu soruya cevap bulamadı. Soruyu farklı şekilde deneyin: '{query}'"
        elif response.status_code == 401:
            return "❌ API anahtarı geçersiz. https://developer.wolframalpha.com/"
        else:
            return f"⚠️ Wolfram API hatası (kod: {response.status_code})"
            
    except requests.exceptions.Timeout:
        return "⏱️ Wolfram Alpha zaman aşımına uğradı."
    except Exception as e:
        return f"❌ Bağlantı hatası: {str(e)}"


@tool
def calculate_wolfram(query: str) -> str:
    """
    Matematik, bilim, döviz, istatistik hesaplamaları için kullanılır.
    
    Örnekler:
    - "solve x^2 + 5x + 6 = 0"
    - "100 USD to TRY"
    - "population of Turkey"
    - "derivative of sin(x)"
    - "distance Earth to Mars"
    
    Args:
        query: İngilizce matematiksel/bilimsel soru
        
    Returns:
        Wolfram Alpha'nın cevabı
    """
    print(f"\n{'='*60}")
    print(f"[WOLFRAM] TOOL CAGRILDI")
    print(f"[WOLFRAM] Sorgu: {query}")
    print(f"{'='*60}")

    result = query_wolfram_api(query)

    print(f"[WOLFRAM] Cevap: {result[:150]}")
    print(f"{'='*60}\n")
    
    return result


# Test - baslangiçta calisir
try:
    test_result = query_wolfram_api("2+2")
    if test_result == "4":
        print("[WOLFRAM] Baglanti basarili")
    else:
        print(f"[WOLFRAM] Baglanti var ama beklenmeyen cevap: {test_result}")
except Exception as e:
    print(f"[WOLFRAM] Baslatma hatasi: {e}")