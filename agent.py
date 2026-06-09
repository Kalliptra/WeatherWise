import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from weather_tool import get_weather, format_weather_summary

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
)

evaluator_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
)


MAIN_SYSTEM_PROMPT = """Sen SkyWise adında bir hava durumu bazlı aktivite öneri asistanısın.
Kullanıcının bulunduğu şehrin güncel hava durumu verilerine göre uygun aktiviteler önerirsin.

Kuralların:
- Fırtına veya şiddetli yağış varsa kesinlikle dışarı aktivite önerme.
- Sıcaklık 0°C altında ise açık hava sporlarını önerme.
- Sıcaklık 38°C üzerinde ise yoğun fiziksel aktivite önerme.
- Kullanıcının tercihlerini dikkate al (spor, kültür, yemek, doğa, vb).
- Her öneri için kısa bir gerekçe yaz.
- Türkçe cevap ver.
- 3-5 farklı aktivite öner, her biri 1-2 cümle açıklama içersin.
- Eğer hava kötü ise iç mekan alternatifleri sun.
"""

SUPERVISOR_SYSTEM_PROMPT = """Sen bir kalite denetçisisin.
Bir AI asistanın hava durumuna göre verdiği aktivite önerilerini değerlendiriyorsun.

Şu kriterlere göre değerlendir:
1. Mantıksal Tutarlılık: Öneriler hava koşullarıyla uyuşuyor mu? (örn. yağmurda piknik öneriliyor mu?)
2. Güvenlik: Aşırı sıcak/soğuk/fırtınalı havada tehlikeli aktivite var mı?
3. Kişiselleştirme: Kullanıcının tercihleri dikkate alınmış mı?

Yanıt formatın şu şekilde olsun:
ONAY: [EVET/HAYIR]
SKOR: [1-10]
YORUM: [Kısa değerlendirme, max 2 cümle]
DÜZELTİLMİŞ_ÖNERİ: [Sadece ONAY=HAYIR ise, düzeltilmiş versiyon yaz. ONAY=EVET ise "Öneri uygundur." yaz.]
"""


def run_main_agent(city: str, preferences: str) -> tuple[str, dict]:
    """
    Main agent: fetches weather and generates activity recommendations.
    Returns (recommendation_text, weather_dict)
    """
    weather = get_weather(city)
    weather_summary = format_weather_summary(weather)

    user_message = (
        f"Hava durumu bilgileri:\n{weather_summary}\n\n"
        f"Kullanıcı tercihleri: {preferences}\n\n"
        "Bu koşullara göre uygun aktiviteler öner."
    )

    messages = [
        SystemMessage(content=MAIN_SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]

    response = llm.invoke(messages)
    return response.content, weather


def run_supervisor_agent(recommendation: str, weather_summary: str, preferences: str) -> dict:
    """
    Supervisor agent: evaluates the main agent's recommendation.
    Returns a dict with approval, score, comment, and corrected recommendation.
    """
    user_message = (
        f"Hava durumu:\n{weather_summary}\n\n"
        f"Kullanıcı tercihleri: {preferences}\n\n"
        f"Değerlendirilecek öneri:\n{recommendation}"
    )

    messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]

    response = evaluator_llm.invoke(messages)
    raw = response.content

    result = {
        "raw": raw,
        "approved": "ONAY: EVET" in raw,
        "score": None,
        "comment": "",
        "corrected": "",
    }

    for line in raw.splitlines():
        if line.startswith("SKOR:"):
            try:
                result["score"] = int(line.replace("SKOR:", "").strip().split("/")[0])
            except ValueError:
                pass
        elif line.startswith("YORUM:"):
            result["comment"] = line.replace("YORUM:", "").strip()
        elif line.startswith("DÜZELTİLMİŞ_ÖNERİ:"):
            result["corrected"] = line.replace("DÜZELTİLMİŞ_ÖNERİ:", "").strip()

    return result


def run_skywise(city: str, preferences: str) -> dict:
    """
    Full pipeline: weather → main agent → supervisor → final output.
    Returns a dict with all results.
    """
    recommendation, weather = run_main_agent(city, preferences)
    weather_summary = format_weather_summary(weather)
    evaluation = run_supervisor_agent(recommendation, weather_summary, preferences)

    final_recommendation = (
        recommendation
        if evaluation["approved"]
        else evaluation.get("corrected", recommendation)
    )

    return {
        "city": weather["city"],
        "country": weather["country"],
        "temperature": weather["temperature"],
        "condition": weather["condition"],
        "humidity": weather["humidity"],
        "wind_speed": weather["wind_speed"],
        "recommendation": final_recommendation,
        "supervisor_approved": evaluation["approved"],
        "supervisor_score": evaluation["score"],
        "supervisor_comment": evaluation["comment"],
        "weather": weather,
    }


if __name__ == "__main__":
    result = run_skywise("Istanbul", "doğa yürüyüşü, kafe, müze")
    print("=== ÖNERİ ===")
    print(result["recommendation"])
    print("\n=== SUPERVISOR ===")
    print(f"Onay: {result['supervisor_approved']}")
    print(f"Skor: {result['supervisor_score']}/10")
    print(f"Yorum: {result['supervisor_comment']}")
