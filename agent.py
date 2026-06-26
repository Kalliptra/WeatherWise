"""Public API — WeatherWise ajan çalıştırıcıları."""

from __future__ import annotations

from core.graph import compiled_graph
from tools.weather import get_weather


def run_skywise(city: str, preferences: str) -> dict:
    """Full StateGraph flow. UI ile uyumlu 7-anahtarlı dict döndürür."""
    final = compiled_graph.invoke(
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
        "itinerary": final.get("itinerary") or "",
    }


def run_skywise_traced(city: str, preferences: str) -> dict:
    """Eval için: tüm final state'i döndürür (iteration, evaluation, plan, ...)."""
    return compiled_graph.invoke(
        {
            "city": city,
            "preferences": preferences,
            "iteration": 0,
            "history": [],
            "venues": {},
        }
    )


if __name__ == "__main__":
    result = run_skywise("Istanbul", "doğa yürüyüşü, kafe, müze")
    print("=== ÖNERİ ===")
    print(result["recommendation"])
