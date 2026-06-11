from __future__ import annotations

import math
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

_NOMINATIM_MIN_INTERVAL_S = 1.05
_last_nominatim_call_ts = 0.0

_geocode_cache: dict[str, tuple[float, float]] = {}
_venues_cache: dict[tuple[str, str, int], list[dict]] = {}

OSM_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "müze": [("tourism", "museum")],
    "muze": [("tourism", "museum")],
    "museum": [("tourism", "museum")],
    "park": [("leisure", "park"), ("leisure", "garden")],
    "bahçe": [("leisure", "garden"), ("leisure", "park")],
    "bahce": [("leisure", "garden"), ("leisure", "park")],
    "kafe": [("amenity", "cafe")],
    "cafe": [("amenity", "cafe")],
    "restoran": [("amenity", "restaurant")],
    "restaurant": [("amenity", "restaurant")],
    "yemek": [("amenity", "restaurant")],
    "spor salonu": [("leisure", "fitness_centre"), ("leisure", "sports_centre")],
    "spor": [("leisure", "fitness_centre"), ("leisure", "sports_centre")],
    "gym": [("leisure", "fitness_centre"), ("leisure", "sports_centre")],
    "fitness": [("leisure", "fitness_centre")],
    "manzara": [("tourism", "viewpoint")],
    "viewpoint": [("tourism", "viewpoint")],
    "seyir": [("tourism", "viewpoint")],
    "kütüphane": [("amenity", "library")],
    "kutuphane": [("amenity", "library")],
    "library": [("amenity", "library")],
    "sanat galerisi": [("tourism", "gallery")],
    "galeri": [("tourism", "gallery")],
    "gallery": [("tourism", "gallery")],
    "alışveriş": [("shop", "mall")],
    "alisveris": [("shop", "mall")],
    "mall": [("shop", "mall")],
    "avm": [("shop", "mall")],
    "yürüyüş": [("route", "hiking"), ("leisure", "nature_reserve")],
    "yuruyus": [("route", "hiking"), ("leisure", "nature_reserve")],
    "doğa": [("leisure", "nature_reserve"), ("route", "hiking")],
    "doga": [("leisure", "nature_reserve"), ("route", "hiking")],
    "trail": [("route", "hiking")],
    "plaj": [("natural", "beach")],
    "beach": [("natural", "beach")],
    "sinema": [("amenity", "cinema")],
    "cinema": [("amenity", "cinema")],
}


def _user_agent() -> str:
    return os.getenv("NOMINATIM_USER_AGENT", "SkyWise-SEN4018/1.0")


def _normalize_category(category: str) -> list[tuple[str, str]]:
    key = category.strip().casefold()
    if key in OSM_CATEGORIES:
        return OSM_CATEGORIES[key]
    for k, tags in OSM_CATEGORIES.items():
        if k in key or key in k:
            return tags
    return [("tourism", "attraction")]


def _wait_for_nominatim_window() -> None:
    global _last_nominatim_call_ts
    elapsed = time.time() - _last_nominatim_call_ts
    if elapsed < _NOMINATIM_MIN_INTERVAL_S:
        time.sleep(_NOMINATIM_MIN_INTERVAL_S - elapsed)
    _last_nominatim_call_ts = time.time()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _build_overpass_query(
    lat: float, lon: float, tags: list[tuple[str, str]], radius_m: int
) -> str:
    clauses = "".join(
        f'nwr["{k}"="{v}"](around:{radius_m},{lat},{lon});' for k, v in tags
    )
    return f"[out:json][timeout:25];({clauses});out center 50;"


def _extract_name_and_coords(
    element: dict,
) -> tuple[Optional[str], Optional[float], Optional[float]]:
    tags = element.get("tags") or {}
    name = tags.get("name") or tags.get("name:tr") or tags.get("name:en")
    if element.get("type") == "node":
        return name, element.get("lat"), element.get("lon")
    center = element.get("center") or {}
    return name, center.get("lat"), center.get("lon")


def geocode_city(city: str, timeout: float = 10.0) -> tuple[float, float]:
    """Return (lat, lon) for `city` via Nominatim. Caches by lowercased city."""
    key = city.strip().lower()
    if key in _geocode_cache:
        return _geocode_cache[key]

    _wait_for_nominatim_window()
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": _user_agent(), "Accept-Language": "tr,en"},
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise ConnectionError(f"Nominatim erişim hatası: {e}") from e

    if resp.status_code != 200:
        raise ConnectionError(f"Nominatim HTTP {resp.status_code}")

    results = resp.json()
    if not results:
        raise ValueError(f"Şehir bulunamadı: {city}")

    lat = float(results[0]["lat"])
    lon = float(results[0]["lon"])
    _geocode_cache[key] = (lat, lon)
    return lat, lon


def find_venues(
    city: str,
    category: str,
    radius_km: int = 5,
    limit: int = 8,
    timeout: float = 25.0,
) -> list[dict]:
    """Return mesafe-sıralı venue dict listesi: {name, type, lat, lon, distance_km}."""
    cache_key = (city.strip().lower(), category.strip().lower(), int(radius_km))
    if cache_key in _venues_cache:
        return _venues_cache[cache_key][:limit]

    lat, lon = geocode_city(city)
    tags = _normalize_category(category)
    query = _build_overpass_query(lat, lon, tags, radius_km * 1000)

    try:
        resp = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": _user_agent()},
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise ConnectionError(f"Overpass erişim hatası: {e}") from e

    if resp.status_code in (429, 504):
        raise ConnectionError("Overpass meşgul, daha sonra dener misiniz?")
    if resp.status_code != 200:
        raise ConnectionError(f"Overpass HTTP {resp.status_code}")

    elements = resp.json().get("elements", [])
    venues: list[dict] = []
    seen_names: set[str] = set()

    for el in elements:
        name, vlat, vlon = _extract_name_and_coords(el)
        if not name or vlat is None or vlon is None:
            continue
        if name in seen_names:
            continue
        seen_names.add(name)
        el_tags = el.get("tags") or {}
        vtype = next(
            (f"{k}={el_tags[k]}" for k, _ in tags if k in el_tags),
            "venue",
        )
        venues.append(
            {
                "name": name,
                "type": vtype,
                "lat": vlat,
                "lon": vlon,
                "distance_km": round(_haversine_km(lat, lon, vlat, vlon), 2),
            }
        )

    venues.sort(key=lambda v: v["distance_km"])
    _venues_cache[cache_key] = venues
    return venues[:limit]


def format_venues_for_llm(venues: list[dict], category: str, city: str) -> str:
    """Compact Türkçe blok. Boşsa kullanıcı dostu mesaj döner."""
    if not venues:
        return f"{city} çevresinde '{category}' kategorisinde uygun mekân bulunamadı."

    header = f"Yakındaki '{category}' önerileri ({city}):"
    lines = [
        f"- {v['name']} ({v['type']}, ~{v['distance_km']}km)" for v in venues
    ]
    return header + "\n" + "\n".join(lines)


if __name__ == "__main__":
    venues = find_venues("Eskişehir", "müze", radius_km=5)
    print(format_venues_for_llm(venues, "müze", "Eskişehir"))
