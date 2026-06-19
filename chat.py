"""Sohbet tabanlı SkyWise katmanı — ReAct agent + supervisor gate."""

from __future__ import annotations

import time
from collections.abc import Iterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from core.llms import evaluator_llm, react_llm
from core.prompts import get_prompt
from core.graph import _parse_supervisor
from tools.uv import get_uv_index
from tools.venue import find_venues, format_venues_for_llm
from tools.weather import (
    calculate_comfort_index,
    format_weather_summary,
    get_forecast,
    get_weather,
)

# ---- Dil tespiti ----

_TURKISH_CHARS = set("ğışçöüĞİŞÇÖÜ")
_TURKISH_WORDS = {
    "merhaba", "nasıl", "bugün", "hava", "istanbul", "ankara",
    "ne", "için", "ben", "bir", "ve", "de", "da", "mi", "mu",
    "var", "yok", "evet", "hayır", "lütfen", "teşekkür",
}

_current_language: str = "tr"


def _detect_language(text: str) -> str:
    if any(c in _TURKISH_CHARS for c in text):
        return "tr"
    words = set(text.lower().split())
    if words & _TURKISH_WORDS:
        return "tr"
    return "en"


def get_current_language() -> str:
    return _current_language


# ---- LangChain tool tanımları ----

@tool
def current_weather_tool(city: str) -> str:
    """Returns the current weather for the given city, including UV index and sunset time."""
    try:
        w = get_weather(city, lang=_current_language)
        try:
            uv = get_uv_index(city, lang=_current_language)
        except Exception:
            uv = None
        return format_weather_summary(w, uv=uv, lang=_current_language)
    except (ValueError, ConnectionError) as e:
        return f"Hata: {e}"


@tool
def forecast_tool(city: str) -> str:
    """Returns the 3-day weather forecast for the given city."""
    try:
        return get_forecast(city, days=3, lang=_current_language)
    except (ValueError, ConnectionError) as e:
        return f"Hata: {e}"


@tool
def comfort_tool(temperature: float, humidity: int, wind_speed: float) -> str:
    """Analyzes outdoor activity comfort based on temperature, humidity, and wind speed."""
    return calculate_comfort_index(temperature, humidity, wind_speed)


@tool
def venue_search_tool(city: str, category: str, radius_km: int = 5) -> str:
    """Finds real venues near a city (Google Places or OpenStreetMap).
    category: müze/museum, park, kafe/cafe, restoran/restaurant, spor salonu/gym,
    manzara/viewpoint, kütüphane/library, sanat galerisi/art gallery,
    alışveriş/shopping mall, plaj/beach, sinema/cinema."""
    try:
        venues = find_venues(city, category, radius_km=radius_km)
        return format_venues_for_llm(venues, category, city, lang=_current_language)
    except (ValueError, ConnectionError) as e:
        return f"Hata: {e}"


@tool
def uv_tool(city: str) -> str:
    """Returns the current UV index and sun protection advice for the given city."""
    try:
        uv = get_uv_index(city, lang=_current_language)
        if _current_language == "en":
            return f"UV Index: {uv['uv_index']} ({uv['uv_level_en']}) — {uv['uv_advice_en']}"
        return f"UV İndeksi: {uv['uv_index']} ({uv['uv_level_tr']}) — {uv['uv_advice_tr']}"
    except Exception as e:
        return f"UV verisi alınamadı: {e}"


# ---- ReAct worker ----

_RECOMMENDATION_TOOLS = {"current_weather_tool", "venue_search_tool"}

_chat_worker = create_react_agent(
    react_llm,
    tools=[current_weather_tool, forecast_tool, comfort_tool, venue_search_tool, uv_tool],
)


# ---- Yardımcılar ----

def _gradio_to_lc_messages(messages: list[dict]) -> list:
    global _current_language

    # Dil tespiti: ilk kullanıcı mesajından
    for m in messages:
        if m.get("role") == "user" and (m.get("content") or "").strip():
            _current_language = _detect_language(m["content"])
            break

    lc: list = [SystemMessage(content=get_prompt("chat", _current_language))]
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
            SystemMessage(content=get_prompt("supervisor", _current_language)),
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
        buf += text[i: i + chunk_size]
        yield buf
        time.sleep(delay_s)
    if buf != text:
        yield text


# ---- Public API ----

def chat_skywise(messages: list[dict]) -> Iterator[str]:
    """Sohbet tabanlı SkyWise asistanı.

    Girdi: Gradio Chatbot(type="messages") formatı —
        [{"role": "user"|"assistant", "content": str}, ...]
    Çıktı: kümülatif metin parçaları (streaming) — son chunk tam yanıttır.
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
