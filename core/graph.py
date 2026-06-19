"""LangGraph node'ları, graph kurulumu ve kontrol sabitleri."""

from __future__ import annotations

from typing import Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from core.llms import evaluator_llm, planner_llm, react_llm
from core.prompts import RECOMMEND_SYSTEM_PROMPT, SUPERVISOR_SYSTEM_PROMPT, PLANNER_SYSTEM_PROMPT
from core.state import Evaluation, PlannedCall, PlannerOutput, SkyWiseState
from tools.venue import find_venues, format_venues_for_llm
from tools.weather import (
    calculate_comfort_index,
    format_weather_summary,
    get_forecast,
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


# ---- Graph kurulumu ----

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

compiled_graph = _graph_builder.compile()
