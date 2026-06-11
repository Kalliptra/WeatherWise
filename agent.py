from __future__ import annotations

import os
import time
from collections.abc import Iterator
from operator import add
from typing import Annotated, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from venue_tool import find_venues, format_venues_for_llm
from weather_tool import (
    calculate_comfort_index,
    format_weather_summary,
    get_forecast,
    get_weather,
)

load_dotenv()


# ---- LLMs ----

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

planner_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
)


# ---- Prompts ----

PLANNER_SYSTEM_PROMPT = """Sen SkyWise ajanının araç planlayıcısısın.
Şehir, kullanıcı tercihleri ve şu ana kadar toplanmış veriler verildiğinde,
aktivite önerisi üretmek için hangi araçların hangi sırayla çağrılması
gerektiğini yapısal olarak döndürürsün.

Mevcut araçlar:
- current_weather(city) — anlık hava
- forecast(city) — 3 günlük tahmin
- comfort(temperature, humidity, wind_speed) — konfor analizi
- venue_search(city, category, radius_km) — gerçek mekân listesi
  (müze, park, kafe, restoran, spor salonu, manzara, kütüphane,
  sanat galerisi, alışveriş, plaj, sinema vb.)

Kurallar:
- İlk turda current_weather MUTLAKA çağırılır.
- Kullanıcı tercihlerinden çıkardığın her ana kategori için bir venue_search planla.
- Şu ana kadar toplanmış veri yeterli ise calls=[] ve done=true döndür.
- Geçen turun supervisor yorumu varsa onu hesaba kat ve eksik veriyi tamamla.
- forecast opsiyoneldir, sadece haftalık/gelecek günlük planlama gerekiyorsa çağır.

Yanıtın yapısal olmalı."""

RECOMMEND_SYSTEM_PROMPT = """Sen SkyWise — hava durumuna göre aktivite öneren Türkçe asistansın.

Sana toplanmış araç çıktıları (hava, tahmin, konfor, mekânlar) ve kullanıcı
tercihleri verilecek. Görevin: 3–5 somut aktivite önerisi üretmek.

Güvenlik kuralları (mutlak):
- Fırtına veya şiddetli yağışta açık hava aktivitesi YOK.
- Sıcaklık 0°C altında açık hava sporu YOK.
- Sıcaklık 38°C üzerinde yoğun fiziksel aktivite YOK.

Stil kuralları:
- Her öneri 1–2 cümle gerekçe içersin.
- venue_search çıktısında gerçek mekân isimleri varsa önerini bunlarla
  somutlaştır (mekân adı + neden uygun olduğu).
- Kullanıcı tercihleriyle her öneriyi açıkça ilişkilendir.
- Hava kötüyse iç mekân alternatifi sun.
- Türkçe, samimi, kısa."""

SUPERVISOR_SYSTEM_PROMPT = """Sen bir kalite denetçisisin. Aşağıdaki öneriyi değerlendir.

Kriterler:
1. Güvenlik: Hava koşullarına aykırı (fırtınada dışarı, 0°C altında açık hava sporu,
   38°C üzerinde yoğun aktivite) öneri var mı?
2. Tutarlılık: Öneriler toplanmış hava verileri ve konfor analiziyle uyumlu mu?
3. Kişiselleştirme: Kullanıcının tercihleri gerçekten yansıtılmış mı, yoksa genel mi?
4. Somutluk: Venue verisi varsa gerçek mekân isimleri kullanılmış mı?

Yanıt formatın AYNEN şu şekilde olsun:
ONAY: [EVET/HAYIR]
SKOR: [1-10]
YORUM: [max 2 cümle değerlendirme]
DÜZELTİLMİŞ_ÖNERİ: [HAYIR ise düzeltilmiş versiyon, EVET ise "Öneri uygundur."]
"""

CHAT_SYSTEM_PROMPT = """Sen SkyWise — hava durumuna göre aktivite öneren, Türkçe
konuşan modern bir AI asistansın. Kullanıcıyla doğal bir sohbet kurarsın.

Konuşma akışı:
- Şehir bilgisi yoksa kibarca sor (örn: "Hangi şehirde olduğunu söyler misin?").
- Tercih belirsizse 2-3 örnekle yönlendir
  ("Doğa yürüyüşü mü, kafe takılması mı, yoksa müze gezmek mi ilgini çeker?").
- Yeterli bilgi olduğunda doğrudan öneriye geç; tekrar tekrar onay isteme.
- Kullanıcı follow-up soru sorarsa (örn: "ilk önerdiğin kafe hakkında daha fazla
  bilgi"), önceki turda topladığın bilgiyi kullan — aynı şehir için tool'ları
  tekrar tekrar çağırma.

Araç kullanımı:
- current_weather: bir şehirde ilk kez öneri üretmeden önce ÇAĞIR.
- venue_search: kullanıcının ilgilendiği her ana aktivite kategorisi için
  ayrı ayrı çağır (kategoriler: müze, park, kafe, restoran, spor salonu,
  manzara, kütüphane, sanat galerisi, alışveriş, plaj, sinema, doğa yürüyüşü).
- forecast: sadece kullanıcı "yarın", "hafta sonu", "önümüzdeki günler" gibi
  ileri tarihten bahsederse çağır.
- comfort: hava sınırda (sıcak+nemli veya soğuk+rüzgarlı) ve kullanıcı dış
  mekan istiyorsa çağır.
- Aynı bilgi için aynı tool'u aynı argümanlarla iki kez ÇAĞIRMA.

Güvenlik kuralları (mutlak):
- Fırtına veya şiddetli yağışta açık hava aktivitesi ÖNERME, iç mekan alternatifi sun.
- Sıcaklık 0°C altında açık hava sporu ÖNERME.
- Sıcaklık 38°C üzerinde yoğun fiziksel aktivite ÖNERME.

Cevap stili:
- Türkçe, samimi, kısa. Öneriler 1-2 cümle gerekçe içersin.
- venue_search çıktısındaki gerçek mekân isimlerini kullan — uydurma isim verme.
- Öneri turunda 3-5 somut aktivite ver; follow-up'larda kullanıcının sorduğu
  spesifik konuya odaklan, listeyi tekrarlama.
- Kısa hava özetiyle başla (sıcaklık + kondisyon), sonra önerilere geç."""


# ---- LangChain tools (inspectability için tutulur; StateGraph dispatch ile çalışır) ----

@tool
def current_weather_tool(city: str) -> str:
    """Verilen şehrin anlık hava durumunu döndürür."""
    try:
        return format_weather_summary(get_weather(city))
    except (ValueError, ConnectionError) as e:
        return f"Hata: {e}"


@tool
def forecast_tool(city: str) -> str:
    """Verilen şehrin 3 günlük hava tahminini döndürür."""
    try:
        return get_forecast(city, days=3)
    except (ValueError, ConnectionError) as e:
        return f"Hata: {e}"


@tool
def comfort_tool(temperature: float, humidity: int, wind_speed: float) -> str:
    """Sıcaklık, nem ve rüzgar hızına göre dışarı aktivite için konfor analizi yapar."""
    return calculate_comfort_index(temperature, humidity, wind_speed)


@tool
def venue_search_tool(city: str, category: str, radius_km: int = 5) -> str:
    """Şehir etrafındaki gerçek mekânları bulur (OpenStreetMap).
    category: müze, park, kafe, restoran, spor salonu, manzara, kütüphane,
    sanat galerisi, alışveriş, plaj, sinema."""
    try:
        venues = find_venues(city, category, radius_km=radius_km)
        return format_venues_for_llm(venues, category, city)
    except (ValueError, ConnectionError) as e:
        return f"Hata: {e}"


# ---- State schema ----

class PlannedCall(TypedDict):
    tool: Literal["current_weather", "forecast", "comfort", "venue_search"]
    args: dict


class Evaluation(TypedDict):
    approved: bool
    score: Optional[int]
    comment: str
    corrected: str


class SkyWiseState(TypedDict, total=False):
    city: str
    preferences: str
    weather: dict
    weather_summary: str
    forecast: str
    comfort: str
    venues: dict[str, str]
    plan: list[PlannedCall]
    plan_done: bool
    recommendation: str
    evaluation: Evaluation
    iteration: int
    history: Annotated[list[str], add]


class PlannerCall(BaseModel):
    tool: Literal["current_weather", "forecast", "comfort", "venue_search"]
    args: dict = Field(default_factory=dict)


class PlannerOutput(BaseModel):
    calls: list[PlannerCall] = Field(default_factory=list)
    done: bool = False
    rationale: str = ""


_structured_planner = planner_llm.with_structured_output(
    PlannerOutput, method="function_calling"
)


# ---- Control constants ----

MAX_ITERATIONS = 3
APPROVAL_SCORE_THRESHOLD = 7


# ---- Nodes ----

def _state_summary(state: SkyWiseState) -> str:
    parts = []
    if state.get("weather_summary"):
        parts.append("HAVA TOPLANDI:\n" + state["weather_summary"])
    else:
        parts.append("HAVA HENÜZ YOK")
    if state.get("forecast"):
        parts.append("TAHMİN TOPLANDI:\n" + state["forecast"])
    if state.get("comfort"):
        parts.append("KONFOR: " + state["comfort"])
    venues = state.get("venues") or {}
    if venues:
        parts.append("MEKÂNLAR TOPLANDI: " + ", ".join(venues.keys()))
    return "\n\n".join(parts)


def plan_node(state: SkyWiseState) -> dict:
    iteration = state.get("iteration", 0) + 1
    history = state.get("history") or []
    last_feedback = history[-1] if history else ""

    human = (
        f"Şehir: {state['city']}\n"
        f"Kullanıcı tercihleri: {state.get('preferences') or 'belirtilmemiş'}\n\n"
        f"Mevcut durum:\n{_state_summary(state)}\n\n"
        f"Son supervisor notu: {last_feedback or 'yok'}\n\n"
        f"Bir sonraki adım için araç planını üret."
    )

    result: PlannerOutput = _structured_planner.invoke(
        [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=human),
        ]
    )

    calls: list[PlannedCall] = [
        {"tool": c.tool, "args": c.args} for c in result.calls
    ]

    if iteration == 1 and not any(c["tool"] == "current_weather" for c in calls):
        calls.insert(0, {"tool": "current_weather", "args": {"city": state["city"]}})

    return {"plan": calls, "plan_done": result.done, "iteration": iteration}


def execute_node(state: SkyWiseState) -> dict:
    plan = state.get("plan") or []
    out: dict = {}
    venues: dict[str, str] = dict(state.get("venues") or {})
    errors: list[str] = []

    weather_obj = state.get("weather")
    forecast_str = state.get("forecast")
    comfort_str = state.get("comfort")
    weather_summary = state.get("weather_summary")

    for call in plan:
        name = call["tool"]
        args = call.get("args") or {}
        try:
            if name == "current_weather":
                city = args.get("city") or state["city"]
                w = get_weather(city)
                weather_obj = w
                weather_summary = format_weather_summary(w)
                if not comfort_str:
                    comfort_str = calculate_comfort_index(
                        w["temperature"], w["humidity"], w["wind_speed"]
                    )
            elif name == "forecast":
                city = args.get("city") or state["city"]
                forecast_str = get_forecast(city, days=3)
            elif name == "comfort":
                if weather_obj is not None:
                    temperature = args.get("temperature", weather_obj["temperature"])
                    humidity = args.get("humidity", weather_obj["humidity"])
                    wind_speed = args.get("wind_speed", weather_obj["wind_speed"])
                else:
                    temperature = args["temperature"]
                    humidity = args["humidity"]
                    wind_speed = args["wind_speed"]
                comfort_str = calculate_comfort_index(temperature, humidity, wind_speed)
            elif name == "venue_search":
                city = args.get("city") or state["city"]
                category = args.get("category", "attraction")
                radius_km = int(args.get("radius_km", 5))
                vlist = find_venues(city, category, radius_km=radius_km)
                venues[category] = format_venues_for_llm(vlist, category, city)
        except (ValueError, ConnectionError, KeyError) as e:
            errors.append(f"[tool {name} hata]: {e}")

    if weather_obj is not None:
        out["weather"] = weather_obj
    if weather_summary:
        out["weather_summary"] = weather_summary
    if forecast_str:
        out["forecast"] = forecast_str
    if comfort_str:
        out["comfort"] = comfort_str
    if venues:
        out["venues"] = venues
    if errors:
        out["history"] = errors

    return out


def recommend_node(state: SkyWiseState) -> dict:
    iteration = state.get("iteration", 1)
    history = state.get("history") or []

    sections = []
    if state.get("weather_summary"):
        sections.append("HAVA:\n" + state["weather_summary"])
    if state.get("forecast"):
        sections.append("TAHMİN:\n" + state["forecast"])
    if state.get("comfort"):
        sections.append(state["comfort"])
    venues = state.get("venues") or {}
    for cat, block in venues.items():
        sections.append(block)

    sections.append(
        f"KULLANICI TERCİHLERİ: {state.get('preferences') or 'belirtilmemiş'}"
    )

    if iteration > 1 and history:
        sections.append("SUPERVISOR NOTU (önceki tur): " + history[-1])

    human = "\n\n".join(sections) + "\n\nLütfen 3-5 somut aktivite önerisi üret."

    raw = react_llm.invoke(
        [
            SystemMessage(content=RECOMMEND_SYSTEM_PROMPT),
            HumanMessage(content=human),
        ]
    ).content

    return {"recommendation": raw}


def _parse_supervisor(raw: str) -> Evaluation:
    result: Evaluation = {
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


def evaluate_node(state: SkyWiseState) -> dict:
    weather_summary = state.get("weather_summary", "")
    venues_text = "\n\n".join((state.get("venues") or {}).values())

    user = (
        f"Hava durumu:\n{weather_summary}\n\n"
        f"Konfor analizi: {state.get('comfort', 'yok')}\n\n"
        f"Mekân verisi:\n{venues_text or 'yok'}\n\n"
        f"Kullanıcı tercihleri: {state.get('preferences') or 'belirtilmemiş'}\n\n"
        f"Değerlendirilecek öneri:\n{state.get('recommendation', '')}"
    )

    raw = evaluator_llm.invoke(
        [
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            HumanMessage(content=user),
        ]
    ).content

    evaluation = _parse_supervisor(raw)
    iteration = state.get("iteration", 1)
    summary_line = (
        f"Tur {iteration}: SKOR={evaluation['score']} "
        f"YORUM={evaluation['comment']}"
    )
    return {"evaluation": evaluation, "history": [summary_line]}


def refine_router(state: SkyWiseState) -> Literal["plan", "END"]:
    e = state.get("evaluation") or {}
    i = state.get("iteration", 1)
    score = e.get("score")
    approved = e.get("approved", False)

    if approved and (score is None or score >= APPROVAL_SCORE_THRESHOLD):
        return "END"
    if i >= MAX_ITERATIONS:
        return "END"
    return "plan"


# ---- Build graph ----

_graph_builder = StateGraph(SkyWiseState)
_graph_builder.add_node("plan", plan_node)
_graph_builder.add_node("execute", execute_node)
_graph_builder.add_node("recommend", recommend_node)
_graph_builder.add_node("evaluate", evaluate_node)

_graph_builder.add_edge(START, "plan")
_graph_builder.add_edge("plan", "execute")
_graph_builder.add_edge("execute", "recommend")
_graph_builder.add_edge("recommend", "evaluate")
_graph_builder.add_conditional_edges(
    "evaluate", refine_router, {"plan": "plan", "END": END}
)

_compiled_graph = _graph_builder.compile()


# ---- Public API ----

def run_skywise(city: str, preferences: str) -> dict:
    """Full StateGraph flow. UI ile uyumlu 7-anahtarlı dict döndürür."""
    final = _compiled_graph.invoke(
        {
            "city": city,
            "preferences": preferences,
            "iteration": 0,
            "history": [],
            "venues": {},
        }
    )

    weather = final.get("weather") or get_weather(city)
    return {
        "city": weather["city"],
        "country": weather["country"],
        "temperature": weather["temperature"],
        "condition": weather["condition"],
        "humidity": weather["humidity"],
        "wind_speed": weather["wind_speed"],
        "recommendation": final.get("recommendation", ""),
    }


def run_skywise_traced(city: str, preferences: str) -> dict:
    """Eval için: tüm final state'i döndürür (iteration, evaluation, plan, ...)."""
    return _compiled_graph.invoke(
        {
            "city": city,
            "preferences": preferences,
            "iteration": 0,
            "history": [],
            "venues": {},
        }
    )


# ---- Chat layer (worker ReAct agent + supervisor gate) ----

_RECOMMENDATION_TOOLS = {"current_weather_tool", "venue_search_tool"}

_chat_worker = create_react_agent(
    react_llm,
    tools=[current_weather_tool, forecast_tool, comfort_tool, venue_search_tool],
)


def _gradio_to_lc_messages(messages: list[dict]) -> list:
    lc: list = [SystemMessage(content=CHAT_SYSTEM_PROMPT)]
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            lc.append(HumanMessage(content=content))
        elif role == "assistant":
            lc.append(AIMessage(content=content))
    return lc


def _turn_produced_recommendation(new_messages: list) -> bool:
    for m in new_messages:
        if isinstance(m, AIMessage):
            for call in getattr(m, "tool_calls", None) or []:
                name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
                if name in _RECOMMENDATION_TOOLS:
                    return True
        elif isinstance(m, ToolMessage):
            if getattr(m, "name", "") in _RECOMMENDATION_TOOLS:
                return True
    return False


def _last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return (m.get("content") or "").strip()
    return ""


def _supervise_chat_turn(
    worker_text: str, new_messages: list, original_messages: list[dict]
) -> str:
    tool_outputs: list[str] = []
    for m in new_messages:
        if isinstance(m, ToolMessage):
            tool_outputs.append(f"[{m.name}]\n{m.content}")

    user_block = _last_user_text(original_messages) or "(kullanıcı mesajı yok)"
    context_block = "\n\n".join(tool_outputs) or "yok"

    raw = evaluator_llm.invoke(
        [
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Kullanıcı son mesajı:\n{user_block}\n\n"
                    f"Worker'ın bu turda topladığı veriler:\n{context_block}\n\n"
                    f"Değerlendirilecek öneri:\n{worker_text}"
                )
            ),
        ]
    ).content

    evaluation = _parse_supervisor(raw)
    if evaluation.get("approved"):
        return worker_text

    corrected = (evaluation.get("corrected") or "").strip()
    if corrected and corrected.lower() != "öneri uygundur.":
        return corrected
    return worker_text


def _stream_chunks(text: str, chunk_size: int = 6, delay_s: float = 0.012) -> Iterator[str]:
    if not text:
        yield ""
        return
    buf = ""
    for i in range(0, len(text), chunk_size):
        buf += text[i : i + chunk_size]
        yield buf
        time.sleep(delay_s)
    if buf != text:
        yield text


def chat_skywise(messages: list[dict]) -> Iterator[str]:
    """Sohbet tabanlı SkyWise asistanı.

    Girdi: Gradio Chatbot(type="messages") formatı —
        [{"role": "user"|"assistant", "content": str}, ...]
    Çıktı: kümülatif metin parçaları (streaming) — son chunk tam yanıttır.

    Worker (ReAct) araçları kullanarak yanıtı üretir; bir aktivite önerisi
    turu yapıldıysa supervisor evaluator devreye girip yanıtı denetler ve
    gerekirse düzeltilmiş versiyonu döner.
    """
    lc_messages = _gradio_to_lc_messages(messages)
    n_original = len(lc_messages)

    result = _chat_worker.invoke({"messages": lc_messages})
    all_messages = result.get("messages", [])
    new_messages = all_messages[n_original:]

    final_ai = all_messages[-1] if all_messages else None
    worker_text = (
        final_ai.content if isinstance(final_ai, AIMessage) and final_ai.content else ""
    )

    if not worker_text:
        worker_text = "Üzgünüm, şu an cevap üretemedim. Tekrar dener misin?"

    if _turn_produced_recommendation(new_messages):
        try:
            final_text = _supervise_chat_turn(worker_text, new_messages, messages)
        except Exception:
            final_text = worker_text
    else:
        final_text = worker_text

    yield from _stream_chunks(final_text)


if __name__ == "__main__":
    result = run_skywise("Istanbul", "doğa yürüyüşü, kafe, müze")
    print("=== ÖNERİ ===")
    print(result["recommendation"])
