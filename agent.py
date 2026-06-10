import os

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from weather_tool import (
    calculate_comfort_index,
    format_weather_summary,
    get_forecast,
    get_weather,
)

load_dotenv()

react_llm = ChatOpenAI(
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

Elindeki araçları şu şekilde kullan:
- Anlık hava için `current_weather_tool`
- Hafta sonu veya gelecek gün planlaması için `forecast_tool`
- Sıcaklık/nem/rüzgar kombinasyonunun insan konforu üzerindeki etkisini anlamak için `comfort_tool`

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
1. Mantıksal Tutarlılık: Öneriler hava koşullarıyla uyuşuyor mu?
2. Güvenlik: Aşırı sıcak/soğuk/fırtınalı havada tehlikeli aktivite var mı?
3. Kişiselleştirme: Kullanıcının tercihleri dikkate alınmış mı?

Yanıt formatın şu şekilde olsun:
ONAY: [EVET/HAYIR]
SKOR: [1-10]
YORUM: [Kısa değerlendirme, max 2 cümle]
DÜZELTİLMİŞ_ÖNERİ: [Sadece ONAY=HAYIR ise, düzeltilmiş versiyon yaz. ONAY=EVET ise "Öneri uygundur." yaz.]
"""


# ---- LangChain tools ----

@tool
def current_weather_tool(city: str) -> str:
    """Verilen şehrin anlık hava durumunu döndürür: sıcaklık, nem, rüzgar, durum."""
    try:
        weather = get_weather(city)
        return format_weather_summary(weather)
    except (ValueError, ConnectionError) as e:
        return f"Hata: {e}"


@tool
def forecast_tool(city: str) -> str:
    """Verilen şehrin önümüzdeki 3 günlük hava tahminini döndürür. Hafta sonu planları için kullan."""
    try:
        return get_forecast(city, days=3)
    except (ValueError, ConnectionError) as e:
        return f"Hata: {e}"


@tool
def comfort_tool(temperature: float, humidity: int, wind_speed: float) -> str:
    """Sıcaklık, nem ve rüzgar hızına göre dışarı aktivite için konfor analizi yapar."""
    return calculate_comfort_index(temperature, humidity, wind_speed)


_tools = [current_weather_tool, forecast_tool, comfort_tool]
_agent_graph = create_react_agent(react_llm, _tools)


# ---- Internal helpers ----

def _run_react_agent(city: str, preferences: str, extra_context: str = "") -> tuple[str, dict]:
    """Runs the ReAct agent and returns (recommendation_text, weather_dict)."""
    user_content = (
        f"Şehir: {city}\n"
        f"Kullanıcı tercihleri: {preferences}\n"
    )
    if extra_context:
        user_content += f"\nÖnceki değerlendirmeden not: {extra_context}"

    result = _agent_graph.invoke({
        "messages": [
            SystemMessage(content=MAIN_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]
    })

    # Last AIMessage that is not a tool call is the final answer
    final_text = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            final_text = msg.content
            break

    # Fetch structured weather data for the UI cards (cheap second call)
    weather = get_weather(city)
    return final_text, weather


def _run_supervisor(recommendation: str, weather_summary: str, preferences: str) -> dict:
    """Evaluates the recommendation. Returns approval, score, comment, corrected text."""
    user_message = (
        f"Hava durumu:\n{weather_summary}\n\n"
        f"Kullanıcı tercihleri: {preferences}\n\n"
        f"Değerlendirilecek öneri:\n{recommendation}"
    )

    messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]

    raw = evaluator_llm.invoke(messages).content

    result = {"approved": "ONAY: EVET" in raw, "score": None, "comment": "", "corrected": ""}
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


# ---- Public API ----

def run_skywise(city: str, preferences: str) -> dict:
    """
    Full flow: ReAct agent gathers weather data → generates recommendations →
    internal supervisor quality check (with one retry if rejected).
    Returns a dict with weather + final recommendation.
    """
    recommendation, weather = _run_react_agent(city, preferences)

    weather_summary = format_weather_summary(weather)
    evaluation = _run_supervisor(recommendation, weather_summary, preferences)

    if not evaluation["approved"]:
        recommendation, weather = _run_react_agent(
            city, preferences, extra_context=evaluation["comment"]
        )

    return {
        "city": weather["city"],
        "country": weather["country"],
        "temperature": weather["temperature"],
        "condition": weather["condition"],
        "humidity": weather["humidity"],
        "wind_speed": weather["wind_speed"],
        "recommendation": recommendation,
    }


if __name__ == "__main__":
    result = run_skywise("Istanbul", "doğa yürüyüşü, kafe, müze")
    print("=== ÖNERİ ===")
    print(result["recommendation"])
