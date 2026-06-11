import os
from collections import Counter
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

_PROVIDER = None


def set_weather_provider(provider):
    """Eval framework için DI seam: callable(city) -> get_weather() şemasında dict."""
    global _PROVIDER
    _PROVIDER = provider


def get_weather(city: str) -> dict:
    """
    Given a city name, returns a dict with weather details.
    Raises ValueError if city is not found.
    """
    if _PROVIDER is not None:
        return _PROVIDER(city)

    params = {
        "q": city,
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "lang": "tr",
    }

    response = requests.get(BASE_URL, params=params)

    if response.status_code == 404:
        raise ValueError(f"Şehir bulunamadı: {city}")
    if response.status_code != 200:
        raise ConnectionError(f"Hava durumu verisi alınamadı. HTTP {response.status_code}")

    data = response.json()

    weather = {
        "city": data["name"],
        "country": data["sys"]["country"],
        "temperature": round(data["main"]["temp"], 1),
        "feels_like": round(data["main"]["feels_like"], 1),
        "humidity": data["main"]["humidity"],
        "wind_speed": round(data["wind"]["speed"] * 3.6, 1),  # m/s → km/h
        "condition": data["weather"][0]["description"],
        "condition_id": data["weather"][0]["id"],
        "visibility": data.get("visibility", 10000) // 1000,  # metre → km
    }

    weather["is_rainy"] = weather["condition_id"] in range(200, 622)
    weather["is_stormy"] = weather["condition_id"] in range(200, 300)
    weather["is_snowy"] = weather["condition_id"] in range(600, 622)
    weather["is_foggy"] = weather["condition_id"] in range(700, 800)
    weather["is_clear"] = weather["condition_id"] in range(800, 803)

    return weather


def get_forecast(city: str, days: int = 3) -> str:
    """
    Returns a plain-text daily forecast summary for the given city (up to `days` days).
    Raises ValueError if city is not found.
    """
    params = {
        "q": city,
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "lang": "tr",
        "cnt": days * 8,  # 8 slots per day (3-hour intervals)
    }

    response = requests.get(FORECAST_URL, params=params)

    if response.status_code == 404:
        raise ValueError(f"Şehir bulunamadı: {city}")
    if response.status_code != 200:
        raise ConnectionError(f"Tahmin verisi alınamadı. HTTP {response.status_code}")

    data = response.json()

    # Group slots by calendar date
    by_date: dict[str, list] = {}
    for slot in data["list"]:
        date = datetime.fromtimestamp(slot["dt"]).strftime("%Y-%m-%d")
        by_date.setdefault(date, []).append(slot)

    lines = []
    for date, slots in list(by_date.items())[:days]:
        temps = [s["main"]["temp"] for s in slots]
        conditions = [s["weather"][0]["description"] for s in slots]
        dominant = Counter(conditions).most_common(1)[0][0]
        label = datetime.strptime(date, "%Y-%m-%d").strftime("%d %b")
        lines.append(
            f"{label}: {round(min(temps), 1)}–{round(max(temps), 1)}°C, {dominant}"
        )

    return "\n".join(lines) if lines else "Tahmin verisi bulunamadı."


def calculate_comfort_index(temperature: float, humidity: int, wind_speed: float) -> str:
    """
    Returns a human-readable comfort verdict based on temperature, humidity, and wind speed.
    No API call — pure calculation.
    """
    if temperature >= 27 and humidity >= 60:
        # Simplified Heat Index feel
        hi = (
            -8.784695
            + 1.61139411 * temperature
            + 2.338549 * humidity
            - 0.14611605 * temperature * humidity
            - 0.01230809 * temperature**2
            - 0.01642482 * humidity**2
        )
        if hi >= 41:
            verdict = f"Tehlikeli sıcaklık (hissedilen ≈{round(hi)}°C) — yoğun fiziksel aktivite önerilmez"
        elif hi >= 32:
            verdict = f"Bunaltıcı (hissedilen ≈{round(hi)}°C) — güneşten korunun"
        else:
            verdict = f"Nemli ama katlanılabilir (hissedilen ≈{round(hi)}°C)"
    elif temperature <= 10 and wind_speed >= 20:
        # Simplified Wind Chill
        wc = 13.12 + 0.6215 * temperature - 11.37 * (wind_speed**0.16) + 0.3965 * temperature * (wind_speed**0.16)
        verdict = f"Soğuk ve rüzgarlı (hissedilen ≈{round(wc)}°C) — katmanlı giyinin"
    elif temperature < 0:
        verdict = f"Dondurucu soğuk ({temperature}°C) — açık hava sporları önerilmez"
    elif 15 <= temperature <= 26 and humidity < 70:
        verdict = f"Konforlu ({temperature}°C, nem %{humidity}) — ideal dış mekan koşulları"
    else:
        verdict = f"Kabul edilebilir ({temperature}°C, nem %{humidity})"

    return f"Konfor Analizi: {verdict}"


def format_weather_summary(weather: dict) -> str:
    """Returns a human-readable weather summary string for LLM prompt."""
    return (
        f"Şehir: {weather['city']}, {weather['country']}\n"
        f"Sıcaklık: {weather['temperature']}°C (hissedilen {weather['feels_like']}°C)\n"
        f"Nem: {weather['humidity']}%\n"
        f"Rüzgar: {weather['wind_speed']} km/h\n"
        f"Hava durumu: {weather['condition']}\n"
        f"Görüş mesafesi: {weather['visibility']} km\n"
        f"Yağışlı: {'Evet' if weather['is_rainy'] else 'Hayır'}\n"
        f"Fırtınalı: {'Evet' if weather['is_stormy'] else 'Hayır'}"
    )


if __name__ == "__main__":
    test_city = "Istanbul"
    weather = get_weather(test_city)
    print(format_weather_summary(weather))
    print()
    print(get_forecast(test_city, days=3))
    print()
    print(calculate_comfort_index(weather["temperature"], weather["humidity"], weather["wind_speed"]))
