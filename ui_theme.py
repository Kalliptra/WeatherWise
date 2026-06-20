"""SkyWise UI teması: koyu (dark) glassmorphism tasarım + SVG ikonlar + panel HTML'i.

Zemin her zaman koyu kalır; hava durumu yalnızca vurgu rengini (--accent),
parlamayı (--glow) ve ikon tonlarını değiştirir. Tema, `document.body.dataset.theme`
üzerinden seçilir ve her tema yalnızca accent ile ilgili CSS değişkenlerini
override eder. Bileşen stilleri tek bir yerde (CUSTOM_CSS) tanımlıdır.
"""

import html as _html
import json as _json
import os as _os

_GMAPS_KEY = _os.getenv("GOOGLE_PLACES_API_KEY", "")

# Koyu zemine uygun Google Maps stil dizisi (API anahtarı olan kullanıcılar için)
_GMAPS_DARK_STYLE = [
    {"elementType": "geometry", "stylers": [{"color": "#1c2233"}]},
    {"elementType": "labels.text.stroke", "stylers": [{"color": "#11151f"}]},
    {"elementType": "labels.text.fill", "stylers": [{"color": "#9aa4c2"}]},
    {"featureType": "administrative", "elementType": "geometry",
     "stylers": [{"color": "#39415a"}]},
    {"featureType": "poi", "elementType": "geometry", "stylers": [{"color": "#242b3d"}]},
    {"featureType": "poi.park", "elementType": "geometry", "stylers": [{"color": "#1c3326"}]},
    {"featureType": "poi.park", "elementType": "labels.text.fill",
     "stylers": [{"color": "#6fae8a"}]},
    {"featureType": "road", "elementType": "geometry", "stylers": [{"color": "#2a3146"}]},
    {"featureType": "road", "elementType": "labels.text.fill",
     "stylers": [{"color": "#aab4d0"}]},
    {"featureType": "road.highway", "elementType": "geometry",
     "stylers": [{"color": "#39415a"}]},
    {"featureType": "transit", "stylers": [{"visibility": "off"}]},
    {"featureType": "water", "elementType": "geometry", "stylers": [{"color": "#0e1422"}]},
    {"featureType": "water", "elementType": "labels.text.fill",
     "stylers": [{"color": "#4a5878"}]},
]


def weather_to_theme(weather: dict) -> str:
    """get_weather() şemasındaki dict'i 7 temadan birine eşler.

    Öncelik: storm > snow > rain > fog > night > clouds > clear-day.
    """
    cid = weather.get("condition_id", 800)
    night = weather.get("is_night", False)

    if 200 <= cid < 300:
        return "storm"
    if 600 <= cid < 622:
        return "snow"
    if 300 <= cid < 600:
        return "rain"
    if 700 <= cid < 800:
        return "fog"
    if night:
        return "night"
    if cid > 800:
        return "clouds"
    return "clear-day"


# ---- İkonlar (inline SVG, renkler tema değişkenlerinden) -------------------

def _cloud(fill: str, dx: int = 0, dy: int = 0) -> str:
    """Daire birleşiminden bulut silüeti (y: 29–85 aralığı, dx/dy ile kaydırılır)."""
    return (
        f'<g fill="{fill}" transform="translate({dx},{dy})">'
        '<circle cx="42" cy="66" r="19"/>'
        '<circle cx="64" cy="54" r="25"/>'
        '<circle cx="86" cy="66" r="17"/>'
        '<rect x="30" y="66" width="70" height="19" rx="9"/>'
        "</g>"
    )


_SVG_OPEN = '<svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" role="img" aria-hidden="true">'

ICONS = {
    "clear-day": (
        _SVG_OPEN
        + '<circle cx="60" cy="60" r="26" fill="var(--icon-main)"/>'
        + '<g stroke="var(--icon-main)" stroke-width="7" stroke-linecap="round">'
        + '<line x1="60" y1="8" x2="60" y2="22"/>'
        + '<line x1="60" y1="98" x2="60" y2="112"/>'
        + '<line x1="8" y1="60" x2="22" y2="60"/>'
        + '<line x1="98" y1="60" x2="112" y2="60"/>'
        + '<line x1="23" y1="23" x2="33" y2="33"/>'
        + '<line x1="87" y1="87" x2="97" y2="97"/>'
        + '<line x1="23" y1="97" x2="33" y2="87"/>'
        + '<line x1="87" y1="33" x2="97" y2="23"/>'
        + "</g></svg>"
    ),
    "night": (
        _SVG_OPEN
        + '<path d="M82 14a46 46 0 1 0 26 60 38 38 0 0 1-26-60z" fill="var(--icon-main)"/>'
        + '<circle cx="88" cy="28" r="4.5" fill="var(--icon-soft)"/>'
        + '<circle cx="104" cy="46" r="3" fill="var(--icon-soft)"/>'
        + '<circle cx="94" cy="62" r="2.5" fill="var(--icon-soft)"/>'
        + "</svg>"
    ),
    "clouds": (
        _SVG_OPEN
        + '<g transform="translate(22,-16) scale(0.62)">' + _cloud("var(--icon-soft)") + "</g>"
        + _cloud("var(--icon-main)", dy=14)
        + "</svg>"
    ),
    "rain": (
        _SVG_OPEN
        + _cloud("var(--icon-main)", dy=-6)
        + '<g stroke="var(--icon-soft)" stroke-width="7" stroke-linecap="round">'
        + '<line x1="46" y1="92" x2="41" y2="108"/>'
        + '<line x1="66" y1="92" x2="61" y2="108"/>'
        + '<line x1="86" y1="92" x2="81" y2="108"/>'
        + "</g></svg>"
    ),
    "storm": (
        _SVG_OPEN
        + _cloud("var(--icon-soft)", dy=-10)
        + '<polygon points="68,76 46,104 60,104 52,120 80,90 64,90" fill="var(--icon-main)"/>'
        + "</svg>"
    ),
    "snow": (
        _SVG_OPEN
        + '<g stroke="var(--icon-main)" stroke-width="6.5" stroke-linecap="round">'
        + '<line x1="60" y1="14" x2="60" y2="106"/>'
        + '<line x1="20" y1="37" x2="100" y2="83"/>'
        + '<line x1="20" y1="83" x2="100" y2="37"/>'
        + "</g>"
        + '<circle cx="60" cy="60" r="9" fill="var(--icon-soft)"/>'
        + "</svg>"
    ),
    "fog": (
        _SVG_OPEN
        + _cloud("var(--icon-soft)", dy=-14)
        + '<g stroke="var(--icon-main)" stroke-width="7" stroke-linecap="round">'
        + '<line x1="26" y1="88" x2="94" y2="88"/>'
        + '<line x1="36" y1="102" x2="104" y2="102"/>'
        + '<line x1="22" y1="116" x2="78" y2="116"/>'
        + "</g></svg>"
    ),
}


# ---- Panel HTML ------------------------------------------------------------

def render_weather_panel(weather: dict, uv=None) -> str:
    theme = weather_to_theme(weather)
    icon = ICONS.get(theme, ICONS["clear-day"])
    temp = round(weather.get("temperature", 0))
    feels = round(weather.get("feels_like", temp))
    condition = str(weather.get("condition", "")).strip()
    condition = condition[:1].upper() + condition[1:] if condition else ""
    city = weather.get("city", "")
    country = weather.get("country", "")
    place = f"{city}, {country}" if country else city

    sunset_str = weather.get("sunset_str")
    uv_level = (uv or {}).get("uv_level_tr") or (uv or {}).get("uv_level_en")
    uv_index = (uv or {}).get("uv_index")

    chips = []
    if sunset_str:
        chips.append(f'<span class="wx-chip">🌅 {sunset_str}</span>')
    if uv_index is not None and uv_level:
        chips.append(f'<span class="wx-chip">☀ UV {uv_index} · {uv_level}</span>')
    chips_html = f'<div class="wx-chips">{"".join(chips)}</div>' if chips else ""

    return (
        '<div class="wx-panel">'
        f'<div class="wx-icon">{icon}</div>'
        f'<div class="wx-temp">{temp}°</div>'
        f'<div class="wx-feels">Hissedilen {feels}°</div>'
        f'<div class="wx-cond">{condition}</div>'
        f'<div class="wx-city">{place}</div>'
        f"{chips_html}"
        "</div>"
    )


def _fmt_review_count(n) -> str:
    if n is None:
        return ""
    if n >= 1000:
        return f"{n / 1000:.1f}k yorum".replace(".0k", "k")
    return f"{n} yorum"


def _map_iframe(center_lat: float, center_lon: float, venues_data: list[dict], zoom: int = 14) -> str:
    """Haritayı iframe srcdoc olarak render eder (koyu temalı).

    GOOGLE_PLACES_API_KEY varsa koyu stilli Google Maps JavaScript API kullanır,
    yoksa CartoDB dark_all tile'ları ile Leaflet kullanır.
    """
    venues_json = _json.dumps(venues_data)

    if _GMAPS_KEY:
        styles_json = _json.dumps(_GMAPS_DARK_STYLE)
        map_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; background: #0e1422; }}
  #map {{ width: 100%; height: 100vh; }}
  .gm-popup {{ font-family: 'Inter', Arial, sans-serif; font-size: 13px; }}
  .gm-popup a {{ color: #1a73e8; font-weight: 600; text-decoration: none; }}
</style>
</head>
<body>
<div id="map"></div>
<script>
var venues = {venues_json};
function initMap() {{
  var map = new google.maps.Map(document.getElementById('map'), {{
    center: {{ lat: {center_lat}, lng: {center_lon} }},
    zoom: {zoom},
    mapTypeControl: false,
    streetViewControl: false,
    fullscreenControl: false,
    styles: {styles_json}
  }});
  var infoWindow = new google.maps.InfoWindow();
  venues.forEach(function(v) {{
    var marker = new google.maps.Marker({{
      position: {{ lat: v.lat, lng: v.lon }},
      map: map,
      title: v.name
    }});
    var c = '<div class="gm-popup"><b>' + v.name + '</b>';
    if (v.open_label) c += ' <span style="font-size:11px;">' + v.open_label + '</span>';
    if (v.rating) c += '<br>⭐ ' + v.rating;
    if (v.review_count_str) c += ' &middot; ' + v.review_count_str;
    if (v.maps_url) c += '<br><a href="' + v.maps_url + '" target="_blank">🗺 ' + (v.btn_label || 'Rota Al') + '</a>';
    c += '</div>';
    marker.addListener('click', function() {{
      infoWindow.setContent(c);
      infoWindow.open(map, marker);
    }});
    if (v.open_popup) {{
      infoWindow.setContent(c);
      infoWindow.open(map, marker);
    }}
  }});
}}
</script>
<script src="https://maps.googleapis.com/maps/api/js?key={_GMAPS_KEY}&callback=initMap" async defer></script>
</body>
</html>"""
    else:
        map_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; background: #0e1422; }}
  #map {{ width: 100%; height: 100vh; }}
  a {{ color: #1a73e8; font-weight: 600; }}
</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
var map = L.map('map').setView([{center_lat}, {center_lon}], {zoom});
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution: '&copy; OpenStreetMap &copy; CARTO',
  subdomains: 'abcd',
  maxZoom: 19
}}).addTo(map);
var venues = {venues_json};
venues.forEach(function(v) {{
  var c = '<b>' + v.name + '</b>';
  if (v.open_label) c += ' <span style="font-size:11px;">' + v.open_label + '</span>';
  if (v.rating) c += '<br>⭐ ' + v.rating;
  if (v.review_count_str) c += ' &middot; ' + v.review_count_str;
  if (v.maps_url) c += '<br><a href="' + v.maps_url + '" target="_blank">🗺 ' + (v.btn_label || 'Rota Al') + '</a>';
  var marker = L.marker([v.lat, v.lon]).addTo(map).bindPopup(c);
  if (v.open_popup) marker.openPopup();
}});
</script>
</body>
</html>"""

    srcdoc = _html.escape(map_doc, quote=True)
    return (
        f'<iframe srcdoc="{srcdoc}" '
        'style="width:100%;height:280px;border:1px solid rgba(255,255,255,0.08);'
        'border-radius:18px;" loading="lazy"></iframe>'
    )


def render_map_panel(venues: list[dict]) -> str:
    """Venue kartları + koyu harita (iframe ile)."""
    if not venues:
        return ""

    valid = [v for v in venues if v.get("lat") and v.get("lon")]
    if not valid:
        return ""

    center_lat = sum(v["lat"] for v in valid) / len(valid)
    center_lon = sum(v["lon"] for v in valid) / len(valid)

    # Venue kartları (yatay kaydırılabilir, haritanın üstünde)
    cards_html = ""
    for v in valid:
        rating_str = f"⭐ {v['rating']}" if v.get("rating") else ""
        reviews_str = _fmt_review_count(v.get("review_count"))
        meta_line = " · ".join([p for p in [rating_str, reviews_str] if p])
        dist_str = f"{v['distance_km']} km" if v.get("distance_km") is not None else ""
        maps_url = v.get("maps_url", "#")
        safe_name = _html.escape(v["name"])

        # Açık/Kapalı rozeti
        open_now = v.get("open_now")
        if open_now is True:
            badge = '<span class="venue-badge venue-badge--open">Açık</span>'
        elif open_now is False:
            badge = '<span class="venue-badge venue-badge--closed">Kapalı</span>'
        else:
            badge = ""

        # Fotoğraf
        photo_url = v.get("photo_url")
        photo_html = (
            f'<img class="venue-card__photo" src="{photo_url}" alt="{safe_name}" '
            f'loading="lazy" onerror="this.style.display=\'none\'">'
        ) if photo_url else ""

        meta_html = f'<div class="venue-card__meta">{meta_line}</div>' if meta_line else ""
        dist_html = f'<div class="venue-card__dist">{dist_str}</div>' if dist_str else ""

        cards_html += (
            '<div class="venue-card">'
            f"{photo_html}"
            f'<div class="venue-card__head"><div class="venue-card__name">{safe_name}</div>{badge}</div>'
            f"{meta_html}{dist_html}"
            f'<a class="venue-card__route" href="{maps_url}" target="_blank">🗺 Rota Al</a>'
            "</div>"
        )

    # iframe için veri listesi (JSON güvenli)
    def _open_label(v):
        if v.get("open_now") is True:
            return "✅ Açık"
        if v.get("open_now") is False:
            return "❌ Kapalı"
        return ""

    venues_data = [{
        "lat": v["lat"],
        "lon": v["lon"],
        "name": v["name"],
        "rating": v.get("rating"),
        "review_count": v.get("review_count"),
        "review_count_str": _fmt_review_count(v.get("review_count")),
        "open_label": _open_label(v),
        "maps_url": v.get("maps_url", ""),
        "btn_label": "Rota Al",
        "open_popup": False,
    } for v in valid]

    iframe_html = _map_iframe(center_lat, center_lon, venues_data, zoom=14)

    return (
        '<div class="map-panel">'
        f'<div class="venue-strip">{cards_html}</div>'
        f"{iframe_html}"
        "</div>"
    )


def render_location_map(name: str, lat: float, lon: float) -> str:
    """Tek pinli harita — spesifik lokasyon için (iframe ile)."""
    maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
    venues_data = [{
        "lat": lat, "lon": lon, "name": name,
        "rating": None, "review_count": None, "review_count_str": "",
        "open_label": "", "maps_url": maps_url, "btn_label": "Yol Tarifi Al", "open_popup": True,
    }]
    iframe_html = _map_iframe(lat, lon, venues_data, zoom=15)
    return f'<div class="map-panel">{iframe_html}</div>'


def render_locations_map(coords: list[tuple[str, float, float]]) -> str:
    """Çok pinli harita — LLM'in önerdiği birden fazla yer için (iframe ile)."""
    if not coords:
        return ""
    venues_data = []
    for name, lat, lon in coords:
        maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
        venues_data.append({
            "lat": lat, "lon": lon, "name": name,
            "rating": None, "review_count": None, "review_count_str": "",
            "open_label": "", "maps_url": maps_url, "btn_label": "Yol Tarifi Al", "open_popup": False,
        })
    center_lat = sum(v["lat"] for v in venues_data) / len(venues_data)
    center_lon = sum(v["lon"] for v in venues_data) / len(venues_data)
    zoom = 13 if len(venues_data) > 1 else 15
    iframe_html = _map_iframe(center_lat, center_lon, venues_data, zoom=zoom)
    return f'<div class="map-panel">{iframe_html}</div>'


def render_panel_placeholder(message: str) -> str:
    return (
        '<div class="wx-panel wx-panel-empty">'
        f'<div class="wx-icon">{ICONS["clouds"]}</div>'
        f'<div class="wx-cond">{message}</div>'
        "</div>"
    )


# ---- CSS -------------------------------------------------------------------

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* Accent renklerini kayıtlı property yap → tema değişiminde yumuşak crossfade */
@property --accent { syntax: '<color>'; inherits: true; initial-value: #7c5cff; }
@property --accent-strong { syntax: '<color>'; inherits: true; initial-value: #4f8cff; }

/* ---- Ortak koyu palet + varsayılan accent (mor→mavi) ---- */
body, body[data-theme="clear-day"], body[data-theme="night"], body[data-theme="clouds"],
body[data-theme="rain"], body[data-theme="storm"], body[data-theme="snow"], body[data-theme="fog"] {
    --bg-1: #0c1020;
    --bg-2: #070912;
    --ink: #e9ecf8;
    --ink-soft: #aab3d0;
    --ink-faint: #7a85ab;
    --hero-ink: #f4f6ff;
    --hero-soft: #b9c2e0;
    --line: rgba(255, 255, 255, 0.10);
    --line-strong: rgba(255, 255, 255, 0.18);
    --surface: rgba(255, 255, 255, 0.045);
    --surface-strong: rgba(255, 255, 255, 0.085);
    --surface-hover: rgba(255, 255, 255, 0.13);
    --on-accent: #0a0d1a;
    color-scheme: dark;
}

/* ---- Havaya göre yalnızca accent / parlama / ikon değişir ---- */
body, body[data-theme="clear-day"] {
    --accent: #ffc24d;
    --accent-strong: #f59e0b;
    --glow: rgba(255, 174, 45, 0.30);
    --icon-main: #ffce5a;
    --icon-soft: #fff3d6;
}
body[data-theme="night"] {
    --accent: #8b7cff;
    --accent-strong: #5f8bff;
    --glow: rgba(124, 108, 255, 0.34);
    --icon-main: #ffe9a8;
    --icon-soft: #cfe0ff;
}
body[data-theme="clouds"] {
    --accent: #8aa0ff;
    --accent-strong: #5f7fe8;
    --glow: rgba(122, 144, 255, 0.30);
    --icon-main: #aebbe0;
    --icon-soft: #ffffff;
}
body[data-theme="rain"] {
    --accent: #4fc3f7;
    --accent-strong: #4f8cff;
    --glow: rgba(79, 170, 247, 0.32);
    --icon-main: #8fb6d8;
    --icon-soft: #4fc3f7;
}
body[data-theme="storm"] {
    --accent: #ffd23f;
    --accent-strong: #f0a90b;
    --glow: rgba(255, 210, 63, 0.30);
    --icon-main: #ffd23f;
    --icon-soft: #9a93c8;
}
body[data-theme="snow"] {
    --accent: #9fd8ff;
    --accent-strong: #6fa8ff;
    --glow: rgba(159, 216, 255, 0.30);
    --icon-main: #bfe2ff;
    --icon-soft: #e8f4ff;
}
body[data-theme="fog"] {
    --accent: #aab4e0;
    --accent-strong: #8090c8;
    --glow: rgba(170, 180, 224, 0.26);
    --icon-main: #b6c0dc;
    --icon-soft: #dfe5f2;
}

/* ---- Zemin (her zaman koyu; accent-tintli ambient parlama) ---- */
html, body { min-height: 100vh; }
body {
    background:
        radial-gradient(1100px 560px at 50% -10%,
            color-mix(in srgb, var(--accent) 16%, transparent) 0%, transparent 60%),
        radial-gradient(900px 520px at 88% 4%,
            color-mix(in srgb, var(--accent-strong) 10%, transparent) 0%, transparent 55%),
        linear-gradient(180deg, var(--bg-1) 0%, var(--bg-2) 100%) fixed !important;
    transition: --accent 0.8s ease, --accent-strong 0.8s ease;
    color: var(--ink) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
gradio-app, .gradio-container,
.gradio-container .main,
.gradio-container .wrap,
.gradio-container .app,
.gradio-container .block,
.gradio-container .form {
    background: transparent !important;
    border-color: transparent !important;
}
.gradio-container {
    max-width: 1140px !important;
    margin: 0 auto !important;
    padding-top: 18px !important;
    color: var(--ink) !important;
}
.gradio-container .prose,
.gradio-container .prose * { color: var(--ink) !important; }
footer { display: none !important; }
.main-row { gap: 18px !important; align-items: flex-start !important; }

/* Tema geçişinde bileşen renkleri de yumuşasın */
.wx-panel, .chat-surface, .chat-area .flex-wrap.user, .chat-area .flex-wrap.bot,
.suggestion-btn, button.primary, textarea, input[type="text"], .wx-chip,
.venue-card, .brand-logo {
    transition: background-color 0.6s ease, color 0.6s ease,
                border-color 0.6s ease, box-shadow 0.6s ease !important;
}

/* ---- Üst bar (marka) ---- */
.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
    padding: 4px 4px 16px 4px !important;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--line);
    background: transparent !important;
}
.brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 900;
    font-size: 1.42rem;
    letter-spacing: -0.5px;
    color: var(--hero-ink) !important;
}
.brand-logo {
    font-size: 1.55rem;
    line-height: 1;
    background: linear-gradient(150deg, var(--accent), var(--accent-strong));
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 2px 10px var(--glow));
}
.brand-tag {
    font-size: 12.5px;
    font-weight: 500;
    color: var(--hero-soft) !important;
    letter-spacing: 0.01em;
}

/* ---- Hava paneli ---- */
.panel-col { position: sticky; top: 14px; align-self: flex-start; }
.wx-panel {
    position: relative;
    overflow: hidden;
    background: var(--surface) !important;
    backdrop-filter: blur(22px) saturate(125%);
    -webkit-backdrop-filter: blur(22px) saturate(125%);
    border: 1px solid var(--line);
    border-radius: 22px;
    padding: 30px 22px 24px;
    text-align: center;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
}
.wx-panel::before {
    content: "";
    position: absolute;
    left: 0; right: 0; top: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0.8;
}
.wx-icon svg {
    width: 104px;
    height: 104px;
    display: block;
    margin: 0 auto 6px auto;
    filter: drop-shadow(0 8px 22px var(--glow));
}
.wx-temp {
    font-size: 60px;
    font-weight: 800;
    letter-spacing: -2px;
    line-height: 1;
    color: var(--ink);
}
.wx-feels {
    font-size: 13.5px;
    font-weight: 600;
    color: var(--ink-faint);
    margin-top: 6px;
}
.wx-cond {
    font-size: 18px;
    font-weight: 700;
    color: var(--ink-soft);
    margin-top: 12px;
}
.wx-city {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin-top: 5px;
}
.wx-panel-empty .wx-cond { font-weight: 600; color: var(--ink-faint); }
.wx-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    justify-content: center;
    margin-top: 16px;
}
.wx-chip {
    font-size: 11.5px;
    font-weight: 600;
    color: var(--ink-soft);
    background: var(--surface-strong);
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 4px 11px;
    letter-spacing: 0.02em;
}

/* ---- Chat yüzeyi ---- */
.chat-surface {
    background: var(--surface) !important;
    backdrop-filter: blur(22px) saturate(125%);
    -webkit-backdrop-filter: blur(22px) saturate(125%);
    border: 1px solid var(--line) !important;
    border-radius: 22px !important;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45) !important;
    padding: 18px !important;
}
.chat-surface label, .chat-surface span, .chat-surface p { color: var(--ink) !important; }

/* Kaydırma kabı, satırlar ve Gradio'nun varsayılan opak zeminleri şeffaf */
.chat-area, .chat-area .wrapper, .chat-area .bubble-wrap,
.chat-area .message-wrap, .chat-area .message-row {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Asıl balon = .flex-wrap (TEK görünür katman) */
.chat-area .flex-wrap { padding: 11px 15px !important; }
.chat-area .flex-wrap.user {
    background: linear-gradient(150deg, var(--accent), var(--accent-strong)) !important;
    border: none !important;
    border-radius: 16px 16px 4px 16px !important;
    box-shadow: 0 10px 26px var(--glow) !important;
    font-weight: 600 !important;
}
.chat-area .flex-wrap.bot {
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    border-radius: 16px 16px 16px 4px !important;
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.30) !important;
}

/* İç sarmalayıcılar (message + tıklanabilir button) tüm kutu stillerinden arındırılır */
.chat-area .message,
.chat-area .flex-wrap button {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    cursor: default !important;
}
.chat-area .flex-wrap .prose p:first-child,
.chat-area .flex-wrap .prose ul:first-child,
.chat-area .flex-wrap .prose ol:first-child { margin-top: 0 !important; }
.chat-area .flex-wrap .prose p:last-child,
.chat-area .flex-wrap .prose ul:last-child,
.chat-area .flex-wrap .prose ol:last-child { margin-bottom: 0 !important; }

/* Metin renkleri */
.chat-area .flex-wrap.user,
.chat-area .flex-wrap.user * { color: var(--on-accent) !important; }
.chat-area .flex-wrap.bot,
.chat-area .flex-wrap.bot p,
.chat-area .flex-wrap.bot li,
.chat-area .flex-wrap.bot strong,
.chat-area .flex-wrap.bot h1,
.chat-area .flex-wrap.bot h2,
.chat-area .flex-wrap.bot h3 { color: var(--ink) !important; }
.chat-area .flex-wrap.bot em { color: var(--accent) !important; }
.chat-area .flex-wrap.bot a { color: var(--accent) !important; font-weight: 600; }
.chat-area .flex-wrap.bot code {
    background: rgba(0, 0, 0, 0.28) !important;
    color: #d6def5 !important;
    border: 1px solid var(--line) !important;
    border-radius: 6px !important;
    padding: 1px 6px !important;
    font-size: 0.9em;
}
.chat-area .flex-wrap.bot hr {
    border: none !important;
    border-top: 1px solid var(--line) !important;
    margin: 12px 0 !important;
    background: transparent !important;
}

/* Kopyala / aksiyon ikon butonları: sade, çerçevesiz */
.chat-area .message-buttons { border: none !important; background: transparent !important; }
.chat-area .message-buttons button,
.chat-area button.action {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: var(--ink-faint) !important;
}
.chat-area .message-buttons button:hover,
.chat-area button.action:hover { color: var(--ink) !important; }
.chat-area button svg { color: inherit !important; opacity: 0.85; }

/* ---- Giriş alanı ---- */
.chat-input-row { margin-top: 12px !important; gap: 8px !important; }
textarea, input[type="text"] {
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    color: var(--ink) !important;
    font-size: 15.5px !important;
}
textarea::placeholder, input::placeholder {
    color: rgba(180, 190, 220, 0.6) !important;
    font-weight: 400 !important;
    font-style: italic !important;
}
textarea:focus, input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 4px var(--glow) !important;
    outline: none !important;
}

button.primary {
    background: linear-gradient(150deg, var(--accent), var(--accent-strong)) !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 800 !important;
    font-size: 15px !important;
    color: var(--on-accent) !important;
    box-shadow: 0 10px 28px var(--glow) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
button.primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 14px 34px var(--glow) !important;
}
button.loc-btn, .loc-btn button,
button.clear-btn, .clear-btn button {
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    color: var(--ink-soft) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}
button.loc-btn:hover, .loc-btn button:hover,
button.clear-btn:hover, .clear-btn button:hover {
    border-color: var(--accent) !important;
    color: var(--ink) !important;
    background: var(--surface-hover) !important;
}

/* ---- Boş durum (karşılama + öneri kartları) ---- */
.empty-state {
    min-height: 430px;
    justify-content: center !important;
    padding: 12px 8px !important;
    background: transparent !important;
    border: none !important;
}
.empty-state .greeting {
    text-align: center;
    margin-bottom: 20px;
}
.empty-state .greeting .wave { font-size: 40px; line-height: 1; }
.empty-state .greeting h2 {
    font-size: 23px;
    font-weight: 800;
    color: var(--ink);
    margin: 12px 0 6px 0;
    letter-spacing: -0.3px;
}
.empty-state .greeting p {
    font-size: 14.5px;
    line-height: 1.55;
    color: var(--ink-soft);
    max-width: 460px;
    margin: 0 auto;
}
button.suggestion-btn {
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    color: var(--ink-soft) !important;
    border-radius: 16px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    text-align: left !important;
    padding: 14px 16px !important;
    min-height: 64px;
    white-space: normal !important;
    line-height: 1.4 !important;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25) !important;
    transition: border-color 0.15s ease, color 0.15s ease, transform 0.15s ease,
                box-shadow 0.15s ease, background-color 0.6s ease !important;
}
button.suggestion-btn:hover {
    border-color: var(--accent) !important;
    color: var(--ink) !important;
    background: var(--surface-hover) !important;
    transform: translateY(-2px);
    box-shadow: 0 14px 30px var(--glow) !important;
}

/* ---- Venue kartları ---- */
.map-panel { margin-top: 14px; }
.venue-strip {
    display: flex;
    gap: 10px;
    overflow-x: auto;
    padding: 4px 2px 12px;
    scrollbar-width: thin;
}
.venue-card {
    display: flex;
    flex-direction: column;
    min-width: 158px;
    max-width: 190px;
    flex-shrink: 0;
    gap: 5px;
    background: var(--surface-strong);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 9px 10px 11px;
    overflow: hidden;
}
.venue-card__photo {
    width: 100%;
    height: 88px;
    object-fit: cover;
    border-radius: 9px;
    margin-bottom: 2px;
}
.venue-card__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 6px;
}
.venue-card__name {
    font-weight: 650;
    font-size: 0.82rem;
    line-height: 1.3;
    color: var(--ink);
}
.venue-badge {
    font-size: 0.66rem;
    font-weight: 700;
    border-radius: 6px;
    padding: 2px 6px;
    white-space: nowrap;
}
.venue-badge--open { color: #34e0a1; background: rgba(52, 224, 161, 0.15); }
.venue-badge--closed { color: #ff7a7a; background: rgba(255, 122, 122, 0.15); }
.venue-card__meta { font-size: 0.74rem; color: var(--ink-soft); }
.venue-card__dist { font-size: 0.72rem; color: var(--ink-faint); }
.venue-card__route {
    margin-top: 3px;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--accent) !important;
    text-decoration: none;
}
.venue-card__route:hover { text-decoration: underline; }

/* ---- Kaydırma çubuğu ---- */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--line-strong); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* ---- Footer ---- */
.footer-note {
    text-align: center;
    background: transparent !important;
    margin-top: 22px;
    padding-top: 12px;
    border-top: 1px solid var(--line);
}
.footer-note p,
.footer-note strong { color: var(--ink-faint) !important; font-weight: 600 !important; }
.footer-note hr { display: none; }

/* ---- "Yazıyor..." üç nokta animasyonu ---- */
.typing-indicator {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 2px;
}
.typing-indicator span {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--accent, #7c5cff);
    opacity: 0.45;
    animation: typing-bounce 1.25s ease-in-out infinite;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.18s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.36s; }
@keyframes typing-bounce {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.45; }
    30% { transform: translateY(-5px); opacity: 1; }
}

/* ---- Mobil ---- */
@media (max-width: 860px) {
    .main-row { flex-direction: column !important; }
    .panel-col { position: static; width: 100% !important; }
    .wx-panel { padding: 22px 18px; }
    .wx-icon svg { width: 88px; height: 88px; }
    .wx-temp { font-size: 50px; }
    .brand { font-size: 1.25rem; }
    .brand-tag { display: none; }
    .empty-state { min-height: 360px; }
}
"""
