from __future__ import annotations


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
