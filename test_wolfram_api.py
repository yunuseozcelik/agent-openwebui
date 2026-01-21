import requests
import json

# API Endpoint
BASE_URL = "http://localhost:9099/v1/chat/completions"

def test_math_agent(question):
    """Math Agent'ı test et"""
    print(f"\n{'='*60}")
    print(f"❓ SORU: {question}")
    print(f"{'='*60}")
    
    payload = {
        "model": "ifs-agent",
        "messages": [
            {"role": "user", "content": question}
        ],
        "stream": False
    }
    
    try:
        response = requests.post(BASE_URL, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        
        print(f"✅ CEVAP:\n{answer}\n")
        return answer
        
    except requests.exceptions.Timeout:
        print("⏱️ İstek zaman aşımına uğradı (30 saniye)")
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP Hatası: {e}")
    except Exception as e:
        print(f"❌ Genel Hata: {e}")

if __name__ == "__main__":
    print("\n🧮 MATH AGENT BAŞARILI TEST SÜİTİ\n")
    
    # Test 1: Denklem Çözme
    test_math_agent("x^2 + 5x + 6 = 0 denklemini çöz")
    
    # Test 2: Döviz Çevirme
    test_math_agent("150 dolar kaç Türk Lirası eder?")
    
    # Test 3: Türev
    test_math_agent("cos(x) fonksiyonunun türevi nedir?")
    
    # Test 4: İntegral
    test_math_agent("x^2 fonksiyonunun integrali nedir?")
    
    # Test 5: İstatistik
    test_math_agent("Japonya'nın nüfusu kaç?")
    
    # Test 6: Fizik/Bilim
    test_math_agent("Işık hızı ne kadar?")
    
    # Test 7: Karmaşık Hesaplama
    test_math_agent("5 faktöriyel kaç eder?")
    
    # Test 8: Birim Çevirme
    test_math_agent("100 kilometre kaç mil?")
    
    # Test 9: Genel Sohbet (Math Agent'a GİTMEMELİ)
    print("\n" + "="*60)
    print("⚠️ NEGATÄ°F TEST (Math Agent seçilmemeli)")
    print("="*60)
    test_math_agent("Merhaba, nasılsın?")
    
    # Test 10: İK İşlemi (HR Agent'a gitmeli)
    print("\n" + "="*60)
    print("⚠️ NEGATÄ°F TEST (HR Agent seçilmeli)")
    print("="*60)
    test_math_agent("2 gün izin almak istiyorum")
    
    print("\n✅ Tüm testler tamamlandı!")
    print("\n📊 SONUÇ DEĞERLENDİRMESİ:")
    print("- Matematik soruları Math_Agent'a gitmeli")
    print("- Genel sorular chat moduna gitmeli")
    print("- İK soruları HR_Agent'a gitmeli")