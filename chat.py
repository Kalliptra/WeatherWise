"""Sohbet tabanlı SkyWise katmanı — ReAct agent + supervisor gate."""

from __future__ import annotations

import time
from collections.abc import Iterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from core.llms import evaluator_llm, react_llm
from core.prompts import CHAT_SYSTEM_PROMPT, SUPERVISOR_SYSTEM_PROMPT
from core.graph import _parse_supervisor
from tools.venue import find_venues, format_venues_for_llm
from tools.weather import (
    calculate_comfort_index,
    format_weather_summary,
    get_forecast,
    get_weather,
)


# ---- LangChain tool tanımları ----

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


# ---- ReAct worker ----

_RECOMMENDATION_TOOLS = {"current_weather_tool", "venue_search_tool"}

_chat_worker = create_react_agent(
    react_llm,
    tools=[current_weather_tool, forecast_tool, comfort_tool, venue_search_tool],
)


# ---- Yardımcılar ----

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
