import os
import time
from collections import Counter
from datetime import datetime
from typing import Optional

import requests
from dotenv import load_dotenv

from tools.cache import get_or_fetch

load_dotenv()

WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

_PROVIDER = None
_LAST_WEATHER: Optional[dict] = None


def set_weather_provider(provider):
    """Eval framework için DI seam: callable(city) -> get_weather() şemasında dict."""
    global _PROVIDER
    _PROVIDER = provider


def get_last_weather() -> Optional[dict]:
    """UI katmanı için: bu turda en son çekilen hava durumu (yoksa None)."""
    return _LAST_WEATHER


def clear_last_weather() -> None:
    global _LAST_WEATHER
    _LAST_WEATHER = None


def _remember(weather: dict) -> dict:
    global _LAST_WEATHER
    _LAST_WEATHER = weather
    return weather


def _parse_current(data: dict) -> dict:
    icon = data["weather"][0].get("icon", "01d")
    sys = data.get("sys", {})
    sunset_unix = sys.get("sunset")
    now_ts = int(time.time())

    weather = {
        "city": data["name"],
        "country": sys.get("country", ""),
        "temperature": round(data["main"]["temp"], 1),
        "feels_like": round(data["main"]["feels_like"], 1),
        "humidity": data["main"]["humidity"],
        "wind_speed": round(data["wind"]["speed"] * 3.6, 1),  # m/s → km/h
        "condition": data["weather"][0]["description"],
        "condition_id": data["weather"][0]["id"],
        "visibility": data.get("visibility", 10000) // 1000,  # metre → km
        "icon": icon,
        "is_night": icon.endswith("n"),
        "sunset_unix": sunset_unix,
        "sunset_str": datetime.fromtimestamp(sunset_unix).strftime("%H:%M") if sunset_unix else None,
        "minutes_to_sunset": max(0, (sunset_unix - now_ts) // 60) if sunset_unix else None,
    }

    weather["is_rainy"] = weather["condition_id"] in range(200, 622)
    weather["is_stormy"] = weather["condition_id"] in range(200, 300)
    weather["is_snowy"] = weather["condition_id"] in range(600, 622)
    weather["is_foggy"] = weather["condition_id"] in range(700, 800)
    weather["is_clear"] = weather["condition_id"] in range(800, 803)

    return weather


def _fetch_owm(params: dict) -> dict:
    """OWM anlık hava endpoint'ine GET atıp ham JSON döndürür.
    `params` üzerine appid/units eklenir. 404 → ValueError, diğer hata → ConnectionError.
    """
    response = requests.get(
        BASE_URL,
        params={**params, "appid": WEATHER_API_KEY, "units": "metric"},
    )
    if response.status_code == 404:
        raise ValueError("Konum bulunamadı")
    if response.status_code != 200:
        raise ConnectionError(f"Hava durumu verisi alınamadı. HTTP {response.status_code}")
    return response.json()


def get_weather(city: str, lang: str = "tr") -> dict:
    """
    Given a city name, returns a dict with weather details.
    Raises ValueError if city is not found.
    """
    if _PROVIDER is not None:
        return _remember(_PROVIDER(city))

    today = datetime.now().strftime("%Y-%m-%d")

    def _fetch():
        # Önce Nominatim ile geocode et: OWM'in q=city isim araması, "Beşiktaş" gibi
        # ilçe adlarını yanlış (ör. Doğu Anadolu'daki başka bir Beşiktaş) yere
        # çözüyor. Geocode başarılıysa koordinatla çek; başarısızsa eski isim
        # aramasına düş (geriye dönük güvenli fallback).
        display_name = None
        try:
            from tools.venue import geocode_city

            lat, lon = geocode_city(city)
            data = _fetch_owm({"lat": lat, "lon": lon, "lang": lang})
            # Koordinatla çekince OWM en yakın büyük şehir adını döndürür
            # (Beşiktaş→"İstanbul"); kullanıcının sorduğu yeri koru.
            display_name = city.strip().title()
        except (ValueError, ConnectionError):
            data = _fetch_owm({"q": city, "lang": lang})

        weather = _parse_current(data)
        if display_name:
            weather["city"] = display_name
        return weather

    return _remember(get_or_fetch(("weather", city.lower(), today), _fetch))


def get_weather_by_coords(lat: float, lon: float) -> dict:
    """
    Returns the same schema as get_weather() for the given coordinates.
    Used only by the UI startup path (geolocation); bypasses the eval provider seam.
    """
    return _remember(_parse_current(_fetch_owm({"lat": lat, "lon": lon, "lang": "tr"})))


def get_forecast(city: str, days: int = 3, lang: str = "tr") -> str:
    """
    Returns a plain-text daily forecast summary for the given city (up to `days` days).
    Raises ValueError if city is not found.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    def _fetch():
        params = {
            "q": city,
            "appid": WEATHER_API_KEY,
            "units": "metric",
            "lang": lang,
            "cnt": days * 8,
        }
        response = requests.get(FORECAST_URL, params=params)
        if response.status_code == 404:
            raise ValueError(f"Şehir bulunamadı: {city}")
        if response.status_code != 200:
            raise ConnectionError(f"Tahmin verisi alınamadı. HTTP {response.status_code}")

        data = response.json()
        by_date: dict[str, list] = {}
        for slot in data["list"]:
            d = datetime.fromtimestamp(slot["dt"]).strftime("%Y-%m-%d")
            by_date.setdefault(d, []).append(slot)

        lines = []
        for d, slots in list(by_date.items())[:days]:
            temps = [s["main"]["temp"] for s in slots]
            conditions = [s["weather"][0]["description"] for s in slots]
            dominant = Counter(conditions).most_common(1)[0][0]
            label = datetime.strptime(d, "%Y-%m-%d").strftime("%d %b")
            lines.append(f"{label}: {round(min(temps), 1)}–{round(max(temps), 1)}°C, {dominant}")

        return "\n".join(lines) if lines else "Tahmin verisi bulunamadı."

    return get_or_fetch(("forecast", city.lower(), today), _fetch)


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


def format_weather_summary(weather: dict, uv: Optional[dict] = None, lang: str = "tr") -> str:
    """Returns a human-readable weather summary string for LLM prompt."""
    if lang == "en":
        lines = [
            f"City: {weather['city']}, {weather['country']}",
            f"Temperature: {weather['temperature']}°C (feels like {weather['feels_like']}°C)",
            f"Humidity: {weather['humidity']}%",
            f"Wind: {weather['wind_speed']} km/h",
            f"Condition: {weather['condition']}",
            f"Visibility: {weather['visibility']} km",
            f"Rainy: {'Yes' if weather['is_rainy'] else 'No'}",
            f"Stormy: {'Yes' if weather['is_stormy'] else 'No'}",
        ]
        if weather.get("sunset_str"):
            lines.append(f"Sunset: {weather['sunset_str']}")
            if weather.get("minutes_to_sunset") is not None:
                mins = weather["minutes_to_sunset"]
                if 0 < mins < 120:
                    lines.append(f"Time to sunset: {mins} minutes")
        if uv:
            lines.append(f"UV Index: {uv['uv_index']} ({uv['uv_level_en']}) — {uv['uv_advice_en']}")
    else:
        lines = [
            f"Şehir: {weather['city']}, {weather['country']}",
            f"Sıcaklık: {weather['temperature']}°C (hissedilen {weather['feels_like']}°C)",
            f"Nem: {weather['humidity']}%",
            f"Rüzgar: {weather['wind_speed']} km/h",
            f"Hava durumu: {weather['condition']}",
            f"Görüş mesafesi: {weather['visibility']} km",
            f"Yağışlı: {'Evet' if weather['is_rainy'] else 'Hayır'}",
            f"Fırtınalı: {'Evet' if weather['is_stormy'] else 'Hayır'}",
        ]
        if weather.get("sunset_str"):
            lines.append(f"Gün batımı: {weather['sunset_str']}")
            if weather.get("minutes_to_sunset") is not None:
                mins = weather["minutes_to_sunset"]
                if 0 < mins < 120:
                    lines.append(f"Gün batımına kalan süre: {mins} dakika")
        if uv:
            lines.append(f"UV İndeksi: {uv['uv_index']} ({uv['uv_level_tr']}) — {uv['uv_advice_tr']}")

    return "\n".join(lines)


if __name__ == "__main__":
    test_city = "Istanbul"
    weather = get_weather(test_city)
    print(format_weather_summary(weather))
    print()
    print(get_forecast(test_city, days=3))
    print()
    print(calculate_comfort_index(weather["temperature"], weather["humidity"], weather["wind_speed"]))
