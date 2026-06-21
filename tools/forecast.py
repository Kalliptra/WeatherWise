"""Saatlik + çok günlü tahmin — Open-Meteo (ücretsiz, key gerektirmez).

Tek çağrıda saatlik sıcaklık/yağış/UV ve günlük min-max verir. Sonuç hem
sohbet araçlarına (yağmur/UV zamanlama metni, gün-gün özet) hem de UI
grafiğine (`get_last_forecast`) beslenir.

Eval framework `set_forecast_provider()` ile gerçek API'yi mock'layabilir.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Optional

import requests

from tools.cache import get_or_fetch

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

_FORECAST_PROVIDER: Optional[Callable] = None
_LAST_FORECAST: Optional[dict] = None

# WMO weather_code → (TR açıklama, EN açıklama, yağışlı mı)
_WMO_CODES: dict[int, tuple[str, str, bool]] = {
    0: ("açık", "clear sky", False),
    1: ("az bulutlu", "mainly clear", False),
    2: ("parçalı bulutlu", "partly cloudy", False),
    3: ("kapalı", "overcast", False),
    45: ("sisli", "fog", False),
    48: ("kırağılı sis", "rime fog", False),
    51: ("hafif çiseleme", "light drizzle", True),
    53: ("çiseleme", "drizzle", True),
    55: ("yoğun çiseleme", "dense drizzle", True),
    56: ("dondurucu çiseleme", "freezing drizzle", True),
    57: ("yoğun dondurucu çiseleme", "dense freezing drizzle", True),
    61: ("hafif yağmur", "light rain", True),
    63: ("yağmur", "rain", True),
    65: ("şiddetli yağmur", "heavy rain", True),
    66: ("dondurucu yağmur", "freezing rain", True),
    67: ("şiddetli dondurucu yağmur", "heavy freezing rain", True),
    71: ("hafif kar", "light snow", True),
    73: ("kar", "snow", True),
    75: ("yoğun kar", "heavy snow", True),
    77: ("kar taneleri", "snow grains", True),
    80: ("hafif sağanak", "light showers", True),
    81: ("sağanak", "showers", True),
    82: ("şiddetli sağanak", "violent showers", True),
    85: ("hafif kar sağanağı", "light snow showers", True),
    86: ("yoğun kar sağanağı", "heavy snow showers", True),
    95: ("gök gürültülü fırtına", "thunderstorm", True),
    96: ("dolulu fırtına", "thunderstorm with hail", True),
    99: ("şiddetli dolulu fırtına", "thunderstorm with heavy hail", True),
}

_WEEKDAYS_TR = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
_WEEKDAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def set_forecast_provider(provider: Optional[Callable]) -> None:
    """Eval framework için DI seam: callable(city, days) -> get_hourly_forecast() şeması."""
    global _FORECAST_PROVIDER
    _FORECAST_PROVIDER = provider


def get_last_forecast() -> Optional[dict]:
    """UI katmanı için: bu turda en son çekilen saatlik tahmin (yoksa None)."""
    return _LAST_FORECAST


def clear_last_forecast() -> None:
    global _LAST_FORECAST
    _LAST_FORECAST = None


def _remember(forecast: dict) -> dict:
    global _LAST_FORECAST
    _LAST_FORECAST = forecast
    return forecast


def _code_desc(code: int, lang: str) -> str:
    entry = _WMO_CODES.get(int(code))
    if not entry:
        return ""
    return entry[1] if lang == "en" else entry[0]


def _code_is_rainy(code: int) -> bool:
    entry = _WMO_CODES.get(int(code))
    return bool(entry and entry[2])


def _weekday_label(date_iso: str, lang: str) -> str:
    dt = datetime.strptime(date_iso, "%Y-%m-%d")
    return (_WEEKDAYS_EN if lang == "en" else _WEEKDAYS_TR)[dt.weekday()]


def _fetch(city: str, days: int) -> dict:
    from tools.venue import geocode_city
    lat, lon = geocode_city(city)

    resp = requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": (
                "temperature_2m,apparent_temperature,precipitation_probability,"
                "precipitation,weather_code,uv_index,wind_speed_10m"
            ),
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max,uv_index_max"
            ),
            "timezone": "auto",
            "forecast_days": days,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    h = data.get("hourly") or {}
    times = h.get("time") or []
    temps = h.get("temperature_2m") or []
    feels = h.get("apparent_temperature") or []
    pprob = h.get("precipitation_probability") or []
    pmm = h.get("precipitation") or []
    codes = h.get("weather_code") or []
    uvs = h.get("uv_index") or []
    winds = h.get("wind_speed_10m") or []

    def _at(seq, i, default=0):
        return seq[i] if i < len(seq) and seq[i] is not None else default

    hours: list[dict] = []
    for i, iso in enumerate(times):
        code = int(_at(codes, i, 0))
        prob = int(_at(pprob, i, 0))
        mm = float(_at(pmm, i, 0.0))
        rainy = _code_is_rainy(code) or prob >= 50 or mm >= 0.2
        hours.append({
            "iso": iso,
            "hour": int(iso[11:13]) if len(iso) >= 13 else 0,
            "date": iso[:10],
            "temp": round(float(_at(temps, i, 0.0)), 1),
            "feels": round(float(_at(feels, i, 0.0)), 1),
            "precip_prob": prob,
            "precip_mm": round(mm, 2),
            "code": code,
            "uv": round(float(_at(uvs, i, 0.0)), 1),
            "wind": round(float(_at(winds, i, 0.0)), 1),
            "is_rainy": rainy,
        })

    d = data.get("daily") or {}
    d_dates = d.get("time") or []
    d_codes = d.get("weather_code") or []
    d_tmax = d.get("temperature_2m_max") or []
    d_tmin = d.get("temperature_2m_min") or []
    d_pprob = d.get("precipitation_probability_max") or []
    d_uvmax = d.get("uv_index_max") or []

    days_out: list[dict] = []
    for i, d_iso in enumerate(d_dates):
        days_out.append({
            "date": d_iso,
            "t_min": round(float(_at(d_tmin, i, 0.0)), 1),
            "t_max": round(float(_at(d_tmax, i, 0.0)), 1),
            "code": int(_at(d_codes, i, 0)),
            "precip_prob_max": int(_at(d_pprob, i, 0)),
            "uv_max": round(float(_at(d_uvmax, i, 0.0)), 1),
        })

    return {
        "city": city,
        "timezone": data.get("timezone", ""),
        "hours": hours,
        "days": days_out,
    }


def get_hourly_forecast(city: str, days: int = 3, lang: str = "tr") -> dict:
    """Verilen şehir için saatlik + günlük tahmin yapısı döndürür."""
    if _FORECAST_PROVIDER is not None:
        return _remember(_FORECAST_PROVIDER(city, days))

    today = date.today().isoformat()
    return _remember(
        get_or_fetch(("hourly", city.lower(), days, today), lambda: _fetch(city, days))
    )


# ---- Deterministik özetler (LLM'siz) ----

def _today_upcoming(hours: list[dict]) -> list[dict]:
    """İlk gelecek saatten itibaren AYNI güne ait kalan saatler (bugünün gidişatı).

    Aynı güne sınırlamak gün sarması kaynaklı hatalı pencereleri (örn. 16:00–16:00)
    önler; saatlik zamanlama her zaman tek bir günü tarif eder.
    """
    now_iso = datetime.now().strftime("%Y-%m-%dT%H:00")
    upcoming = [h for h in hours if h["iso"] >= now_iso] or hours
    if not upcoming:
        return []
    target_date = upcoming[0]["date"]
    return [h for h in upcoming if h["date"] == target_date]


def _rain_windows(hours: list[dict]) -> list[tuple[str, str]]:
    """Bugünün kalan saatlerindeki ardışık yağışlı pencereleri (HH:MM, HH:MM) döndürür."""
    upcoming = _today_upcoming(hours)
    windows: list[tuple[str, str]] = []
    start: Optional[dict] = None
    prev: Optional[dict] = None

    def _end_label(h: dict) -> str:
        # Yağışlı saat h, [h:00, h+1:00) aralığını kapsar; gün sonunu 24:00 yerine 23:59 göster.
        return "23:59" if h["hour"] >= 23 else f"{h['hour'] + 1:02d}:00"

    for h in upcoming:
        if h["is_rainy"]:
            if start is None:
                start = h
            prev = h
        elif start is not None:
            windows.append((f"{start['hour']:02d}:00", _end_label(prev)))
            start = None
    if start is not None and prev is not None:
        windows.append((f"{start['hour']:02d}:00", _end_label(prev)))
    return windows


def _uv_peak(hours: list[dict]) -> Optional[dict]:
    upcoming = _today_upcoming(hours)
    if not upcoming:
        return None
    peak = max(upcoming, key=lambda h: h["uv"])
    return peak if peak["uv"] >= 3 else None


def summarize_timing(forecast: dict, lang: str = "tr") -> str:
    """Yağmur pencereleri + UV zirvesini deterministik metne çevirir (itinerary için)."""
    hours = forecast.get("hours") or []
    windows = _rain_windows(hours)
    peak = _uv_peak(hours)

    parts: list[str] = []
    if lang == "en":
        if windows:
            spans = ", ".join(f"{a}–{b}" for a, b in windows)
            parts.append(f"Rain expected: {spans} (stay indoors then).")
        else:
            parts.append("No precipitation expected in the next 24h.")
        if peak:
            parts.append(f"UV peak: {peak['hour']:02d}:00 (UV {peak['uv']}).")
    else:
        if windows:
            spans = ", ".join(f"{a}–{b}" for a, b in windows)
            parts.append(f"Yağış beklenen saatler: {spans} (bu aralıkta iç mekân).")
        else:
            parts.append("Önümüzdeki 24 saatte yağış beklenmiyor.")
        if peak:
            parts.append(f"UV zirvesi: {peak['hour']:02d}:00 (UV {peak['uv']}).")
    return " ".join(parts)


def summarize_days(forecast: dict, lang: str = "tr") -> str:
    """Gün-gün özet metni (çok günlü plan için)."""
    days = forecast.get("days") or []
    lines: list[str] = []
    for day in days:
        label = _weekday_label(day["date"], lang)
        desc = _code_desc(day["code"], lang)
        if lang == "en":
            extra = f", rain {day['precip_prob_max']}%" if day["precip_prob_max"] >= 30 else ""
            lines.append(f"{label}: {day['t_min']}–{day['t_max']}°C, {desc}{extra}")
        else:
            extra = f", yağış %{day['precip_prob_max']}" if day["precip_prob_max"] >= 30 else ""
            lines.append(f"{label}: {day['t_min']}–{day['t_max']}°C, {desc}{extra}")
    return "\n".join(lines)


if __name__ == "__main__":
    f = get_hourly_forecast("Istanbul")
    print(summarize_timing(f, "tr"))
    print(summarize_days(f, "tr"))
