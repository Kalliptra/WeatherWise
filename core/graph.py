"""LangGraph node'ları, graph kurulumu ve kontrol sabitleri."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from core.llms import evaluator_llm, itinerary_llm, planner_llm, react_llm
from core.prompts import get_prompt
from core.state import Evaluation, PlannedCall, PlannerOutput, WeatherWiseState
from tools.forecast import get_hourly_forecast, summarize_days, summarize_timing
from tools.uv import get_uv_index
from tools.venue import _USE_GOOGLE, find_venues, format_venues_for_llm, geocode_city
from tools.weather import (
    calculate_comfort_index,
    format_weather_summary,
    get_weather,
)

# ---- Kontrol sabitleri ----

MAX_ITERATIONS = 3
APPROVAL_SCORE_THRESHOLD = 7

# ---- Yapısal planner ----

_structured_planner = planner_llm.with_structured_output(
    PlannerOutput, method="function_calling"
)


# ---- Yardımcı ----

def _lang(state: WeatherWiseState) -> str:
    return state.get("language", "tr")


def _state_summary(state: WeatherWiseState) -> str:
    parts = []
    if state.get("weather_summary"):
        parts.append("HAVA TOPLANDI:\n" + state["weather_summary"])
    else:
        parts.append("HAVA HENÜZ YOK")
    if state.get("forecast"):
        parts.append("TAHMİN TOPLANDI:\n" + state["forecast"])
    if state.get("comfort"):
        parts.append("KONFOR: " + state["comfort"])
    if state.get("uv"):
        uv = state["uv"]
        parts.append(f"UV: {uv['uv_index']} ({uv['uv_level_tr']}) — {uv['uv_advice_tr']}")
    venues = state.get("venues") or {}
    if venues:
        parts.append("MEKÂNLAR TOPLANDI: " + ", ".join(venues.keys()))
    return "\n\n".join(parts)


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


# ---- Node'lar ----

def plan_node(state: WeatherWiseState) -> dict:
    iteration = state.get("iteration", 0) + 1
    history = state.get("history") or []
    last_feedback = history[-1] if history else ""
    lang = _lang(state)

    human = (
        f"Şehir: {state['city']}\n"
        f"Kullanıcı tercihleri: {state.get('preferences') or 'belirtilmemiş'}\n\n"
        f"Mevcut durum:\n{_state_summary(state)}\n\n"
        f"Son supervisor notu: {last_feedback or 'yok'}\n\n"
        f"Bir sonraki adım için araç planını üret."
    )

    result: PlannerOutput = _structured_planner.invoke(
        [
            SystemMessage(content=get_prompt("planner", lang)),
            HumanMessage(content=human),
        ]
    )

    calls: list[PlannedCall] = [
        {"tool": c.tool, "args": c.args} for c in result.calls
    ]

    if iteration == 1 and not any(c["tool"] == "current_weather" for c in calls):
        calls.insert(0, {"tool": "current_weather", "args": {"city": state["city"]}})

    return {"plan": calls, "plan_done": result.done, "iteration": iteration}


def execute_node(state: WeatherWiseState) -> dict:
    plan = state.get("plan") or []
    lang = _lang(state)
    out: dict = {}
    venues: dict[str, str] = dict(state.get("venues") or {})
    errors: list[str] = []

    weather_obj = state.get("weather")
    uv_obj = state.get("uv")
    forecast_str = state.get("forecast")
    forecast_hourly_obj = state.get("forecast_hourly")
    comfort_str = state.get("comfort")
    weather_summary = state.get("weather_summary")

    # Venue ve diğer çağrıları ayır
    venue_calls = [c for c in plan if c["tool"] == "venue_search"]
    non_venue_calls = [c for c in plan if c["tool"] != "venue_search"]

    # 1. Sıralı: hava/UV/tahmin/konfor çağrıları (değişmez)
    for call in non_venue_calls:
        name = call["tool"]
        args = call.get("args") or {}
        try:
            if name == "current_weather":
                city = args.get("city") or state["city"]
                w = get_weather(city, lang=lang)
                weather_obj = w
                if uv_obj is None:
                    try:
                        uv_obj = get_uv_index(city, lang=lang)
                    except Exception:
                        pass
                weather_summary = format_weather_summary(w, uv=uv_obj, lang=lang)
                if not comfort_str:
                    comfort_str = calculate_comfort_index(
                        w["temperature"], w["humidity"], w["wind_speed"]
                    )
            elif name == "uv_index":
                city = args.get("city") or state["city"]
                uv_obj = get_uv_index(city, lang=lang)
                if weather_obj is not None:
                    weather_summary = format_weather_summary(weather_obj, uv=uv_obj, lang=lang)
            elif name in ("forecast", "hourly_forecast"):
                city = args.get("city") or state["city"]
                days = int(args.get("days", 3))
                forecast_hourly_obj = get_hourly_forecast(city, days=days, lang=lang)
                forecast_str = summarize_days(forecast_hourly_obj, lang=lang)
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
        except (ValueError, ConnectionError, KeyError) as e:
            errors.append(f"[tool {name} hata]: {e}")

    # 2. Paralel: venue aramaları
    if venue_calls:
        # Geocode cache'i ısıt → tüm thread'ler aynı şehir için cache hit alır
        try:
            geocode_city(state["city"])
        except Exception:
            pass

        # Overpass rate-limit riski varsa worker sayısını düşür
        max_workers = 4 if _USE_GOOGLE else 2

        def _run_venue(call: PlannedCall) -> tuple[str, str]:
            args = call.get("args") or {}
            category = args.get("category", "attraction")
            radius_km = int(args.get("radius_km", 5))
            city = args.get("city") or state["city"]
            vlist = find_venues(city, category, radius_km=radius_km)
            return category, format_venues_for_llm(vlist, category, city, lang=lang)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_run_venue, c): c for c in venue_calls}
            for fut in as_completed(futures):
                call = futures[fut]
                try:
                    cat, formatted = fut.result()
                    venues[cat] = formatted
                except (ValueError, ConnectionError, KeyError) as e:
                    cat = (call.get("args") or {}).get("category", "?")
                    errors.append(f"[venue_search {cat} hata]: {e}")

    if weather_obj is not None:
        out["weather"] = weather_obj
    if uv_obj is not None:
        out["uv"] = uv_obj
    if weather_summary:
        out["weather_summary"] = weather_summary
    if forecast_str:
        out["forecast"] = forecast_str
    if forecast_hourly_obj:
        out["forecast_hourly"] = forecast_hourly_obj
    if comfort_str:
        out["comfort"] = comfort_str
    if venues:
        out["venues"] = venues
    if errors:
        out["history"] = errors

    return out


def recommend_node(state: WeatherWiseState) -> dict:
    iteration = state.get("iteration", 1)
    history = state.get("history") or []
    lang = _lang(state)

    sections = []
    if state.get("weather_summary"):
        sections.append("HAVA:\n" + state["weather_summary"])
    if state.get("forecast"):
        sections.append("TAHMİN:\n" + state["forecast"])
    if state.get("comfort"):
        sections.append(state["comfort"])

    # Sunset context
    weather = state.get("weather") or {}
    mins_to_sunset = weather.get("minutes_to_sunset")
    if mins_to_sunset is not None and 0 < mins_to_sunset < 60:
        if lang == "en":
            sections.append(f"SUNSET WARNING: Only {mins_to_sunset} minutes until sunset — great time for viewpoints!")
        else:
            sections.append(f"GÜN BATIMI UYARISI: Gün batımına {mins_to_sunset} dakika kaldı — manzara noktaları için ideal zaman!")

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
            SystemMessage(content=get_prompt("recommend", lang)),
            HumanMessage(content=human),
        ]
    ).content

    return {"recommendation": raw}


def evaluate_node(state: WeatherWiseState) -> dict:
    weather_summary = state.get("weather_summary", "")
    venues_text = "\n\n".join((state.get("venues") or {}).values())
    lang = _lang(state)

    user = (
        f"Hava durumu:\n{weather_summary}\n\n"
        f"Konfor analizi: {state.get('comfort', 'yok')}\n\n"
        f"Mekân verisi:\n{venues_text or 'yok'}\n\n"
        f"Kullanıcı tercihleri: {state.get('preferences') or 'belirtilmemiş'}\n\n"
        f"Değerlendirilecek öneri:\n{state.get('recommendation', '')}"
    )

    raw = evaluator_llm.invoke(
        [
            SystemMessage(content=get_prompt("supervisor", lang)),
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


def refine_router(state: WeatherWiseState) -> Literal["plan", "itinerary"]:
    e = state.get("evaluation") or {}
    i = state.get("iteration", 1)
    score = e.get("score")
    approved = e.get("approved", False)

    if approved and (score is None or score >= APPROVAL_SCORE_THRESHOLD):
        return "itinerary"
    if i >= MAX_ITERATIONS:
        return "itinerary"
    return "plan"


def itinerary_node(state: WeatherWiseState) -> dict:
    """Öneri metnini alıp günlük zaman planı üretir."""
    lang = _lang(state)

    sections: list[str] = []
    if state.get("weather_summary"):
        sections.append("HAVA:\n" + state["weather_summary"])
    if state.get("comfort"):
        sections.append(state["comfort"])
    if state.get("forecast"):
        sections.append("TAHMİN:\n" + state["forecast"])
    if state.get("forecast_hourly"):
        timing = summarize_timing(state["forecast_hourly"], lang=lang)
        if timing:
            label = "SAATLİK ZAMANLAMA" if lang == "tr" else "HOURLY TIMING"
            sections.append(f"{label}:\n{timing}")

    weather = state.get("weather") or {}
    mins_to_sunset = weather.get("minutes_to_sunset")
    if mins_to_sunset is not None and 0 < mins_to_sunset <= 60:
        label = f"GÜN BATIMI: {mins_to_sunset} dakika kaldı" if lang == "tr" else f"SUNSET: {mins_to_sunset} minutes away"
        sections.append(label)

    uv = state.get("uv") or {}
    if uv.get("uv_index") is not None:
        uv_info = f"UV İndeksi: {uv['uv_index']} — {uv.get('uv_advice_tr', '')}" if lang == "tr" \
            else f"UV Index: {uv['uv_index']} — {uv.get('uv_advice_en', '')}"
        sections.append(uv_info)

    for cat, block in (state.get("venues") or {}).items():
        sections.append(block)

    sections.append(
        f"KULLANICI TERCİHLERİ: {state.get('preferences') or 'belirtilmemiş'}"
        if lang == "tr" else
        f"USER PREFERENCES: {state.get('preferences') or 'not specified'}"
    )
    sections.append(
        f"AKTİVİTE ÖNERİLERİ:\n{state.get('recommendation', '')}"
        if lang == "tr" else
        f"ACTIVITY SUGGESTIONS:\n{state.get('recommendation', '')}"
    )

    human = "\n\n".join(sections) + (
        "\n\nLütfen günlük zaman planı oluştur." if lang == "tr"
        else "\n\nPlease create a day itinerary."
    )

    raw = itinerary_llm.invoke([
        SystemMessage(content=get_prompt("itinerary", lang)),
        HumanMessage(content=human),
    ]).content

    return {"itinerary": raw.strip() or None}


# ---- Graph kurulumu ----

_graph_builder = StateGraph(WeatherWiseState)
_graph_builder.add_node("plan", plan_node)
_graph_builder.add_node("execute", execute_node)
_graph_builder.add_node("recommend", recommend_node)
_graph_builder.add_node("evaluate", evaluate_node)
_graph_builder.add_node("itinerary", itinerary_node)

_graph_builder.add_edge(START, "plan")
_graph_builder.add_edge("plan", "execute")
_graph_builder.add_edge("execute", "recommend")
_graph_builder.add_edge("recommend", "evaluate")
_graph_builder.add_conditional_edges(
    "evaluate", refine_router, {"plan": "plan", "itinerary": "itinerary"}
)
_graph_builder.add_edge("itinerary", END)

compiled_graph = _graph_builder.compile()
