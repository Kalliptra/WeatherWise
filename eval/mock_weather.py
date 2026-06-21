from __future__ import annotations

from datetime import date, timedelta


def _materialize(override: dict) -> dict:
    """Verilen partial weather dict'i get_weather() çıktısıyla aynı şemaya genişletir."""
    cid = override.get("condition_id", 800)
    base = {
        "city": override["city"],
        "country": override.get("country", "TR"),
        "temperature": float(override["temperature"]),
        "feels_like": float(override.get("feels_like", override["temperature"])),
        "humidity": int(override["humidity"]),
        "wind_speed": float(override["wind_speed"]),
        "condition": override.get("condition", ""),
        "condition_id": int(cid),
        "visibility": int(override.get("visibility", 10)),
        "icon": override.get("icon", "01d"),
    }
    base["is_night"] = base["icon"].endswith("n")
    base["is_rainy"] = 200 <= cid < 622
    base["is_stormy"] = 200 <= cid < 300
    base["is_snowy"] = 600 <= cid < 622
    base["is_foggy"] = 700 <= cid < 800
    base["is_clear"] = 800 <= cid < 803
    return base


class MockWeatherProvider:
    """Eval için deterministik hava sağlayıcı. weather_tool.set_weather_provider'a verilir."""

    def __init__(self, overrides_by_city: dict[str, dict]):
        self._by_city = {k.lower(): v for k, v in overrides_by_city.items()}

    def __call__(self, city: str) -> dict:
        key = city.strip().lower()
        override = self._by_city.get(key)
        if override is None:
            raise ValueError(f"Şehir bulunamadı: {city}")
        return _materialize(override)


class MockForecastProvider:
    """Eval için deterministik saatlik+günlük tahmin sağlayıcı.

    forecast.set_forecast_provider'a verilir; ağ çağrısı yapmadan
    scenario weather_override'larından tutarlı bir tahmin türetir.
    """

    def __init__(self, overrides_by_city: dict[str, dict]):
        self._by_city = {k.lower(): v for k, v in overrides_by_city.items()}

    def __call__(self, city: str, days: int = 3) -> dict:
        key = city.strip().lower()
        override = self._by_city.get(key)
        if override is None:
            raise ValueError(f"Şehir bulunamadı: {city}")

        w = _materialize(override)
        rainy = w["is_rainy"]
        t_base = w["temperature"]
        code = 61 if rainy else (3 if override.get("condition_id", 800) >= 803 else 0)

        hours: list[dict] = []
        days_out: list[dict] = []
        today = date.today()
        for d in range(max(1, days)):
            day_iso = (today + timedelta(days=d)).isoformat()
            uv_vals = []
            for h in range(24):
                # Öğlene doğru zirve yapan basit UV eğrisi (gece 0)
                uv = max(0.0, 7.0 - abs(13 - h)) if 6 <= h <= 20 else 0.0
                uv_vals.append(round(uv, 1))
                hours.append({
                    "iso": f"{day_iso}T{h:02d}:00",
                    "hour": h,
                    "date": day_iso,
                    "temp": round(t_base, 1),
                    "feels": round(w["feels_like"], 1),
                    "precip_prob": 80 if rainy else 0,
                    "precip_mm": 1.0 if rainy else 0.0,
                    "code": code,
                    "uv": round(uv, 1),
                    "wind": round(w["wind_speed"], 1),
                    "is_rainy": rainy,
                })
            days_out.append({
                "date": day_iso,
                "t_min": round(t_base - 4, 1),
                "t_max": round(t_base + 2, 1),
                "code": code,
                "precip_prob_max": 80 if rainy else 0,
                "uv_max": max(uv_vals) if uv_vals else 0.0,
            })

        return {
            "city": override["city"],
            "timezone": "mock",
            "hours": hours,
            "days": days_out,
        }
