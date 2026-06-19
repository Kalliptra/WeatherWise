"""UV indeksi — Open-Meteo (ücretsiz, key gerektirmez)."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import requests

from tools.cache import get_or_fetch

_UV_PROVIDER: Optional[Callable] = None

_UV_SCALE = [
    (2, "düşük", "low", "Güneş kremi gerekmez.", "No sunscreen needed."),
    (5, "orta", "moderate", "Güneş gözlüğü takmanız önerilir.", "Sunglasses recommended."),
    (7, "yüksek", "high", "Güneş kremi (SPF 30+) sürün.", "Apply sunscreen (SPF 30+)."),
    (10, "çok yüksek", "very high", "Öğlen saatlerinde gölgede kalın.", "Stay in shade at midday."),
    (99, "aşırı", "extreme", "Açık havadan kaçının.", "Avoid outdoor exposure."),
]


def set_uv_provider(provider: Optional[Callable]) -> None:
    """Eval framework için DI seam."""
    global _UV_PROVIDER
    _UV_PROVIDER = provider


def _classify(uv: float) -> tuple[str, str, str, str]:
    for threshold, level_tr, level_en, advice_tr, advice_en in _UV_SCALE:
        if uv <= threshold:
            return level_tr, level_en, advice_tr, advice_en
    return _UV_SCALE[-1][1], _UV_SCALE[-1][2], _UV_SCALE[-1][3], _UV_SCALE[-1][4]


def _fetch_uv(city: str) -> dict:
    from tools.venue import geocode_city
    lat, lon = geocode_city(city)

    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "uv_index",
            "timezone": "auto",
            "forecast_days": 1,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    times = data["hourly"]["time"]
    uv_values = data["hourly"]["uv_index"]

    now_str = datetime.now().strftime("%Y-%m-%dT%H:00")
    idx = 0
    for i, t in enumerate(times):
        if t == now_str:
            idx = i
            break

    uv_val = round(uv_values[idx] or 0, 1)
    level_tr, level_en, advice_tr, advice_en = _classify(uv_val)

    return {
        "uv_index": uv_val,
        "uv_level_tr": level_tr,
        "uv_level_en": level_en,
        "uv_advice_tr": advice_tr,
        "uv_advice_en": advice_en,
    }


def get_uv_index(city: str, lang: str = "tr") -> dict:
    """Verilen şehir için anlık UV indeksi döndürür."""
    if _UV_PROVIDER is not None:
        return _UV_PROVIDER(city)

    today = __import__("datetime").date.today().isoformat()
    return get_or_fetch(("uv", city.lower(), today), lambda: _fetch_uv(city))
