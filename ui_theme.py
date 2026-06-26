"""WeatherWise UI teması: koyu (dark) glassmorphism tasarım + SVG ikonlar + panel HTML'i.

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

def render_weather_panel(weather: dict, uv=None, lang: str = "tr") -> str:
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
        f'<div class="wx-feels">{"Feels like" if lang == "en" else "Hissedilen"} {feels}°</div>'
        f'<div class="wx-cond">{condition}</div>'
        f'<div class="wx-city">{place}</div>'
        f"{chips_html}"
        "</div>"
    )


def _fmt_review_count(n, lang: str = "tr") -> str:
    if n is None:
        return ""
    label = "reviews" if lang == "en" else "yorum"
    if n >= 1000:
        return f"{n / 1000:.1f}k {label}".replace(".0k", "k")
    return f"{n} {label}"


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


def render_map_panel(venues: list[dict], lang: str = "tr") -> str:
    """Venue kartları + koyu harita (iframe ile)."""
    if not venues:
        return ""

    valid = [v for v in venues if v.get("lat") and v.get("lon")]
    if not valid:
        return ""

    is_en = lang == "en"
    open_txt = "Open" if is_en else "Açık"
    closed_txt = "Closed" if is_en else "Kapalı"
    route_txt = "Get Directions" if is_en else "Rota Al"

    center_lat = sum(v["lat"] for v in valid) / len(valid)
    center_lon = sum(v["lon"] for v in valid) / len(valid)

    # Venue kartları (yatay kaydırılabilir, haritanın üstünde)
    cards_html = ""
    for v in valid:
        rating_str = f"⭐ {v['rating']}" if v.get("rating") else ""
        reviews_str = _fmt_review_count(v.get("review_count"), lang)
        meta_line = " · ".join([p for p in [rating_str, reviews_str] if p])
        dist_str = f"{v['distance_km']} km" if v.get("distance_km") is not None else ""
        maps_url = v.get("maps_url", "#")
        safe_name = _html.escape(v["name"])

        # Açık/Kapalı rozeti
        open_now = v.get("open_now")
        if open_now is True:
            badge = f'<span class="venue-badge venue-badge--open">{open_txt}</span>'
        elif open_now is False:
            badge = f'<span class="venue-badge venue-badge--closed">{closed_txt}</span>'
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
            f'<a class="venue-card__route" href="{maps_url}" target="_blank">🗺 {route_txt}</a>'
            "</div>"
        )

    # iframe için veri listesi (JSON güvenli)
    def _open_label(v):
        if v.get("open_now") is True:
            return f"✅ {open_txt}"
        if v.get("open_now") is False:
            return f"❌ {closed_txt}"
        return ""

    venues_data = [{
        "lat": v["lat"],
        "lon": v["lon"],
        "name": v["name"],
        "rating": v.get("rating"),
        "review_count": v.get("review_count"),
        "review_count_str": _fmt_review_count(v.get("review_count"), lang),
        "open_label": _open_label(v),
        "maps_url": v.get("maps_url", ""),
        "btn_label": route_txt,
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


def render_locations_map(coords: list[tuple[str, float, float]], lang: str = "tr") -> str:
    """Çok pinli harita — LLM'in önerdiği birden fazla yer için (iframe ile)."""
    if not coords:
        return ""
    btn_label = "Get Directions" if lang == "en" else "Yol Tarifi Al"
    venues_data = []
    for name, lat, lon in coords:
        maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
        venues_data.append({
            "lat": lat, "lon": lon, "name": name,
            "rating": None, "review_count": None, "review_count_str": "",
            "open_label": "", "maps_url": maps_url, "btn_label": btn_label, "open_popup": False,
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


def render_panel_skeleton() -> str:
    """Hava paneli yüklenirken gösterilen, içerik şekilli shimmer'lı iskelet."""
    return (
        '<div class="wx-panel wx-skeleton" aria-busy="true" aria-label="Hava durumu yükleniyor">'
        '<div class="sk sk-city"></div>'
        '<div class="sk sk-temp"></div>'
        '<div class="sk sk-cond"></div>'
        '<div class="sk-row">'
        '<div class="sk sk-chip"></div>'
        '<div class="sk sk-chip"></div>'
        '<div class="sk sk-chip"></div>'
        "</div>"
        "</div>"
    )


def _fmt_pref_list(items: list[str], limit: int = 6) -> str:
    """Tür listesini virgüllü metne çevirir; fazlasını '+N' ile özetler."""
    clean = [str(c).strip() for c in items if str(c).strip()]
    shown = clean[:limit]
    text = ", ".join(_html.escape(c) for c in shown)
    extra = len(clean) - len(shown)
    if extra > 0:
        text += f" +{extra}"
    return text


def render_personalization_badge(level_info: dict, lang: str = "tr") -> str:
    """Sidebar kişiselleştirme kartı: Lv N + 5 nokta + beğenilen/beğenilmeyen türler (isimle)."""
    info = level_info or {}
    level = int(info.get("level", 0))
    liked = info.get("liked", []) or []
    disliked = info.get("disliked", []) or []

    title = "Kişiselleştirme" if lang != "en" else "Personalization"
    lvl_label = f"Lv {level}"
    dots = "".join(
        f'<span class="pb-dot{" on" if i < level else ""}"></span>' for i in range(5)
    )

    body_lines: list[str] = []
    if liked:
        lbl = "Liked" if lang == "en" else "Sevdiklerin"
        body_lines.append(
            f'<div class="pb-likes"><span class="pb-tag">{lbl}:</span> {_fmt_pref_list(liked)}</div>'
        )
    if disliked:
        lbl = "Disliked" if lang == "en" else "Sevmediklerin"
        body_lines.append(
            f'<div class="pb-dislikes"><span class="pb-tag">{lbl}:</span> {_fmt_pref_list(disliked)}</div>'
        )

    if not body_lines:
        if level > 0:
            # Aksiyon var ama henüz tür çıkarılamadı.
            msg = ("learning — suggestions are shaped for you"
                   if lang == "en" else "öğreniyor — öneriler sana göre şekilleniyor")
        else:
            msg = ("Give feedback to tailor suggestions"
                   if lang == "en" else "Öneri ver ve beğen, sana göre şekillensin")
        body_lines.append(f'<div class="pb-desc">{msg}</div>')

    return (
        '<div class="pers-badge-inner">'
        f'<div class="pb-head"><span class="pb-title">{title}</span>'
        f'<span class="pb-lvl">{lvl_label}</span></div>'
        f'<div class="pb-dots">{dots}</div>'
        + "".join(body_lines)
        + "</div>"
    )


def render_forecast_chart(forecast: dict, horizon: int = 48, lang: str = "tr"):
    """tools.forecast.get_hourly_forecast() çıktısından Plotly figürü üretir.

    Sıcaklık çizgisi (sol eksen) + yağış olasılığı barları (sağ eksen), yağış
    pencereleri gölgeli, UV zirvesi işaretli. Koyu temaya uygun, saydam zemin.
    Veri yoksa veya plotly yoksa None döner (grafik gizli kalır).
    """
    if not forecast:
        return None
    hours = forecast.get("hours") or []
    if not hours:
        return None

    from datetime import datetime as _dt

    now_iso = _dt.now().strftime("%Y-%m-%dT%H:00")
    upcoming = [h for h in hours if h["iso"] >= now_iso][:horizon]
    if len(upcoming) < 2:
        upcoming = hours[:horizon]
    if len(upcoming) < 2:
        return None

    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    xs = [_dt.fromisoformat(h["iso"]) for h in upcoming]
    temps = [h["temp"] for h in upcoming]
    probs = [h["precip_prob"] for h in upcoming]

    is_en = lang == "en"
    precip_name = "Rain chance" if is_en else "Yağış olasılığı"
    temp_name = "Temperature" if is_en else "Sıcaklık"
    bar_hover = (
        "%{x|%a %H:%M}<br>" + ("Rain %{y}%%" if is_en else "Yağış %%{y}") + "<extra></extra>"
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=xs, y=probs, name=precip_name,
        marker_color="rgba(96,165,250,0.45)", yaxis="y2",
        hovertemplate=bar_hover,
    ))
    fig.add_trace(go.Scatter(
        x=xs, y=temps, name=temp_name, mode="lines",
        line=dict(color="#f5a623", width=3, shape="spline"),
        hovertemplate="%{x|%a %H:%M}<br>%{y}°C<extra></extra>",
    ))

    # Yağış pencerelerini gölgele
    span_start = None
    prev = None
    for h, x in zip(upcoming, xs):
        if h["is_rainy"]:
            if span_start is None:
                span_start = x
            prev = x
        elif span_start is not None:
            fig.add_vrect(x0=span_start, x1=prev, fillcolor="rgba(96,165,250,0.12)",
                          line_width=0, layer="below")
            span_start = None
    if span_start is not None and prev is not None:
        fig.add_vrect(x0=span_start, x1=prev, fillcolor="rgba(96,165,250,0.12)",
                      line_width=0, layer="below")

    # UV zirvesi
    uv_peak = max(upcoming, key=lambda h: h["uv"])
    if uv_peak["uv"] >= 6:
        fig.add_annotation(
            x=_dt.fromisoformat(uv_peak["iso"]), y=uv_peak["temp"],
            text=f"☀️ UV {uv_peak['uv']}", showarrow=True, arrowhead=0,
            font=dict(color="#fcd34d", size=11), arrowcolor="rgba(252,211,77,0.6)",
            ax=0, ay=-28,
        )

    fig.update_layout(
        margin=dict(l=8, r=8, t=28, b=8),
        height=240,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#aab4d0", size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False, tickformat="%a %H:%M", color="#8a93ad"),
        yaxis=dict(title="°C", showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                   color="#8a93ad", zeroline=False),
        yaxis2=dict(title=("Rain %" if is_en else "Yağış %"), overlaying="y", side="right", range=[0, 100],
                    showgrid=False, color="#8a93ad"),
        bargap=0.1,
        hovermode="x unified",
    )
    return fig


def render_time_ribbon(forecast: dict, lang: str = "tr"):
    """Bugünün kalan saatlerini açık-hava uygunluğuna göre boyayan kompakt şerit.

    `tools.forecast.classify_today_hours()` çıktısından HTML üretir: her saat bir hücre
    (yeşil=ideal, sarı=UV, mavi=yağış, kırmızı=sıcak, mor=soğuk), üstte en uzun ideal
    pencere özeti. Veri yetersizse None döner (şerit gizli kalır).
    """
    if not forecast:
        return None
    from tools.forecast import classify_today_hours

    cells = classify_today_hours(forecast)
    if len(cells) < 2:
        return None

    # En uzun ardışık "good" (ideal açık hava) penceresini bul
    best_start = best_len = cur_start = cur_len = 0
    for i, c in enumerate(cells):
        if c["state"] == "good":
            if cur_len == 0:
                cur_start = i
            cur_len += 1
            if cur_len > best_len:
                best_len, best_start = cur_len, cur_start
        else:
            cur_len = 0

    if best_len >= 1:
        a = cells[best_start]["hour"]
        end_hour = cells[best_start + best_len - 1]["hour"]
        b = "23:59" if end_hour >= 23 else f"{end_hour + 1:02d}:00"
        if lang == "en":
            summary = f"🟢 Best window: {a:02d}:00–{b}"
        else:
            summary = f"🟢 En iyi saat: {a:02d}:00–{b}"
    else:
        summary = (
            "No ideal outdoor window today"
            if lang == "en"
            else "Bugün açık hava için ideal pencere görünmüyor"
        )

    # Her ~3 saatte bir etiket göster (ilk hücre dahil)
    cell_html = []
    for i, c in enumerate(cells):
        label = f"{c['hour']:02d}" if (i == 0 or c["hour"] % 3 == 0) else ""
        cell_html.append(
            f'<span class="tr-cell tr-cell--{c["state"]}" title="{c["hour"]:02d}:00">'
            f'<span class="tr-label">{label}</span></span>'
        )

    rain_word = "rain" if lang == "en" else "yağış"
    legend = (
        '<div class="tr-legend">'
        '<span class="tr-dot tr-cell--good"></span>ideal'
        '<span class="tr-dot tr-cell--uv"></span>UV'
        f'<span class="tr-dot tr-cell--rain"></span>{rain_word}'
        "</div>"
    )

    return (
        '<div class="time-ribbon">'
        f'<div class="tr-summary">{summary}</div>'
        f'<div class="tr-track">{"".join(cell_html)}</div>'
        f"{legend}"
        "</div>"
    )


def render_rain_alert(forecast: dict, lang: str = "tr"):
    """Yağmur nowcast uyarısı — `tools.forecast.rain_nowcast()` metnini küçük bir
    'pill' kutusuna sarar. Kayda değer durum yoksa None döner (uyarı gizli kalır)."""
    if not forecast:
        return None
    from tools.forecast import rain_nowcast

    msg = rain_nowcast(forecast, lang)
    if not msg:
        return None
    # Yağmur başlıyorsa "warn" (accent), diniyorsa "calm" tonunu kullan
    tone = "calm" if msg.startswith("🌤") else "warn"
    return f'<div class="rain-alert rain-alert--{tone}">{msg}</div>'


def render_week_heatmap(forecast: dict, lang: str = "tr"):
    """Çok günlü tahminden gün × saat 'ideal pencere' ısı haritası üretir.

    `tools.forecast.classify_week_hours()` çıktısını gün satırlarına, `best_week_window()`
    ile en iyi açık-hava penceresini özet satırına çevirir. Hücre renkleri zaman şeridiyle
    aynı `.tr-cell--{state}` sınıflarını yeniden kullanır. Tek gün/veri yoksa None döner."""
    if not forecast:
        return None
    from tools.forecast import best_week_window, classify_week_hours, _weekday_label

    week = classify_week_hours(forecast)
    if len(week) < 2:
        return None  # tek günde zaman şeridi yeterli; ısı haritası gösterme

    best = best_week_window(forecast)
    if best:
        wd = _weekday_label(best["date"], lang)
        a, b = best["start"], best["end"]
        b_str = "24:00" if b >= 24 else f"{b:02d}:00"
        summary = (
            f"🟢 Best window: {wd} {a:02d}:00–{b_str}"
            if lang == "en"
            else f"🟢 En iyi pencere: {wd} {a:02d}:00–{b_str}"
        )
    else:
        summary = (
            "No ideal outdoor window this week"
            if lang == "en"
            else "Bu hafta açık hava için ideal pencere görünmüyor"
        )

    # Saat eksenini veriden türet (gün gün aynı gündüz penceresi).
    axis = sorted({c["hour"] for day in week for c in day["hours"]})
    if not axis:
        return None

    head_cells = "".join(
        f'<span class="wh-hh">{h:02d}</span>' if h % 4 == 0 else '<span class="wh-hh"></span>'
        for h in axis
    )

    rows_html = []
    for day in week:
        wd = _weekday_label(day["date"], lang)
        state_by_hour = {c["hour"]: c["state"] for c in day["hours"]}
        cells = "".join(
            f'<span class="tr-cell tr-cell--{state_by_hour.get(h, "none")}" title="{wd} {h:02d}:00"></span>'
            for h in axis
        )
        rows_html.append(
            f'<div class="wh-row"><span class="wh-day">{wd}</span>'
            f'<div class="wh-track">{cells}</div></div>'
        )

    rain_word = "rain" if lang == "en" else "yağış"
    legend = (
        '<div class="tr-legend">'
        '<span class="tr-dot tr-cell--good"></span>ideal'
        '<span class="tr-dot tr-cell--uv"></span>UV'
        f'<span class="tr-dot tr-cell--rain"></span>{rain_word}'
        "</div>"
    )

    return (
        '<div class="week-heatmap">'
        f'<div class="wh-summary">{summary}</div>'
        '<div class="wh-grid">'
        f'<div class="wh-row wh-head"><span class="wh-day"></span><div class="wh-track">{head_cells}</div></div>'
        + "".join(rows_html)
        + "</div>"
        f"{legend}"
        "</div>"
    )


def render_travel_compare(home_weather: dict, dest_weather: dict, lang: str = "tr"):
    """Seyahat modunda 'konum vs hedef' kompakt hava karşılaştırma kartı.

    İki şehir de geçerli ve farklı değilse None döner (kart gizli kalır)."""
    if not home_weather or not dest_weather:
        return None
    hc = str(home_weather.get("city", "")).strip()
    dc = str(dest_weather.get("city", "")).strip()
    if not hc or not dc or hc.lower() == dc.lower():
        return None

    ht = round(home_weather.get("temperature", 0))
    dt = round(dest_weather.get("temperature", 0))
    hcond = str(home_weather.get("condition", "")).strip()
    hcond = hcond[:1].upper() + hcond[1:] if hcond else ""
    dcond = str(dest_weather.get("condition", "")).strip()
    dcond = dcond[:1].upper() + dcond[1:] if dcond else ""
    delta = dt - ht
    sign = "+" if delta > 0 else ""

    if lang == "en":
        title = "Trip weather"
        word = "warmer" if delta > 0 else "cooler" if delta < 0 else "the same"
        diff = f"{dc} is {sign}{delta}° {word} than {hc}" if delta else f"{dc} ≈ {hc}"
    else:
        title = "Seyahat havası"
        word = "sıcak" if delta > 0 else "soğuk" if delta < 0 else "aynı"
        diff = f"{dc}, {hc}'den {sign}{delta}° {word}" if delta else f"{dc} ≈ {hc}"

    return (
        '<div class="travel-compare">'
        f'<div class="tc-title">✈️ {title}</div>'
        f'<div class="tc-row"><span class="tc-place">🏠 {hc}</span>'
        f'<span class="tc-temp">{ht}°{(" · " + hcond) if hcond else ""}</span></div>'
        f'<div class="tc-row tc-dest"><span class="tc-place">📍 {dc}</span>'
        f'<span class="tc-temp">{dt}°{(" · " + dcond) if dcond else ""}</span></div>'
        f'<div class="tc-diff">{diff}</div>'
        "</div>"
    )


def render_favorites_html(favs: list, lang: str = "tr") -> str:
    """Kaydedilen favori mekanları sidebar için statik HTML listesine çevirir.

    Her satır: ✅/📍 ad · şehir + 🗺 rota linki. 'done' işaretliler soluk/üstü çizili.
    Favori yoksa "" döner (bölüm görünmez)."""
    if not favs:
        return ""
    title = "⭐ My Saved Places" if lang == "en" else "⭐ Favori Mekanlarım"
    items = []
    for f in favs:
        name = _html.escape(str(f.get("name", "")))
        city = _html.escape(str(f.get("city", "")))
        done = bool(f.get("done"))
        mark = "✅" if done else "📍"
        url = f.get("maps_url") or ""
        route = (
            f'<a class="fav-route" href="{_html.escape(url, quote=True)}" target="_blank" '
            f'title="Rota" rel="noopener">🗺</a>'
            if url else ""
        )
        sub = f'<span class="fav-city">{city}</span>' if city else ""
        items.append(
            f'<div class="fav-item{" done" if done else ""}">'
            f'<span class="fav-name">{mark} {name}</span>{sub}{route}</div>'
        )
    return (
        '<div class="fav-box">'
        f'<div class="fav-title">{title}</div>'
        f'{"".join(items)}'
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
    max-width: 100% !important;
    margin: 0 auto !important;
    padding: 18px 32px !important;
    color: var(--ink) !important;
}
.gradio-container .prose,
.gradio-container .prose * { color: var(--ink) !important; }
footer { display: none !important; }
.main-row { gap: 18px !important; align-items: flex-start !important; width: 100% !important; }

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
.panel-col { position: sticky; top: 14px; align-self: flex-start; min-width: 280px; }
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
/* Yeni içerik eklendiğinde scroll pozisyonu atlamaması için scroll-anchor */
.chat-area .bubble-wrap, .chat-area .wrap, .chat-area > div {
    overflow-anchor: auto;
}
/* Scroll container içindeki son element anchor görevi görür */
.chat-area .bubble-wrap > div:last-child,
.chat-area .wrap > div:last-child {
    overflow-anchor: auto;
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
.chat-area .message-buttons,
.chat-area .icon-button-wrapper {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}
.chat-area .message-buttons button,
.chat-area .icon-button-wrapper button,
.chat-area button.action {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: var(--ink-soft) !important;
}
.chat-area .message-buttons button:hover,
.chat-area .icon-button-wrapper button:hover,
.chat-area button.action:hover { color: var(--ink) !important; }
/* İkon SVG'leri görünür yap: rengi currentColor'a bağla, boyutu sabitle */
.chat-area button svg,
.chat-area .icon-button-wrapper svg {
    color: inherit !important;
    fill: currentColor !important;
    stroke: currentColor !important;
    opacity: 0.85;
    width: 15px !important;
    height: 15px !important;
}
/* Chatbot'un sağ üst araç çubuğunu (paylaş + temizle/çöp) gizle.
   Bu araç çubuğu .message-row DIŞINDA; mesaj başına kopyala butonu korunur.
   Temizle/çöp butonunun Gradio'da kapatma parametresi yok, bu yüzden CSS ile. */
.chat-area .icon-button-wrapper { display: none !important; }
.chat-area .message-row .icon-button-wrapper { display: flex !important; }

/* ===== Güncel Gradio 5 baloncuk yapısı =====
   Yeni sürümlerde rol class'ı (.user/.bot) artık .flex-wrap'te değil;
   satır .message-row.{role}-row, asıl balon ise .message elementinde.
   Bu blok yukarıdaki .flex-wrap.user/.bot kurallarından SONRA gelir ve
   daha yüksek özgüllükle (.user-row .message) kazanır. */
.chat-area .message-row,
.chat-area .message-row .flex-wrap {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}
/* Asıl balon = .message (rol satırdan miras alınır) */
.chat-area .user-row .message,
.chat-area .bot-row .message {
    padding: 11px 15px !important;
}
.chat-area .user-row .message {
    background: linear-gradient(150deg, var(--accent), var(--accent-strong)) !important;
    border: none !important;
    border-radius: 16px 16px 4px 16px !important;
    box-shadow: 0 10px 26px var(--glow) !important;
    font-weight: 600 !important;
}
.chat-area .bot-row .message {
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    border-radius: 16px 16px 16px 4px !important;
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.30) !important;
}
/* Balon içi metin renkleri */
.chat-area .user-row .message,
.chat-area .user-row .message * { color: var(--on-accent) !important; }
.chat-area .bot-row .message,
.chat-area .bot-row .message p,
.chat-area .bot-row .message li,
.chat-area .bot-row .message strong,
.chat-area .bot-row .message h1,
.chat-area .bot-row .message h2,
.chat-area .bot-row .message h3 { color: var(--ink) !important; }
.chat-area .bot-row .message em { color: var(--accent) !important; }
.chat-area .bot-row .message a { color: var(--accent) !important; font-weight: 600; }
.chat-area .bot-row .message code {
    background: rgba(0, 0, 0, 0.28) !important;
    color: #d6def5 !important;
    border: 1px solid var(--line) !important;
    border-radius: 6px !important;
    padding: 1px 6px !important;
    font-size: 0.9em;
}
.chat-area .bot-row .message hr {
    border: none !important;
    border-top: 1px solid var(--line) !important;
    margin: 12px 0 !important;
    background: transparent !important;
}

/* ---- Giriş alanı ---- */
.chat-input-row {
    margin-top: 12px !important;
    gap: 8px !important;
    display: flex !important;
    align-items: center !important;
    flex-shrink: 0 !important;
    width: 100% !important;
}
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
.chat-input-row textarea {
    height: 46px !important;
    min-height: 46px !important;
    max-height: 46px !important;
    resize: none !important;
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
button.loc-btn, .loc-btn button {
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    color: var(--ink-soft) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    width: 100% !important;
}
button.clear-btn, .clear-btn button {
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    color: var(--ink-soft) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}
button.loc-btn:hover, .loc-btn button:hover {
    border-color: var(--accent) !important;
    color: var(--ink) !important;
    background: var(--surface-hover) !important;
}
button.clear-btn:hover, .clear-btn button:hover {
    border-color: var(--accent) !important;
    color: var(--ink) !important;
    background: var(--surface-hover) !important;
}

/* ---- Session sidebar ---- */
.sidebar-toggle, button.sidebar-toggle {
    min-width: 40px !important;
    max-width: 44px !important;
    padding: 6px 10px !important;
    font-size: 1.1rem !important;
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    color: var(--ink-soft) !important;
    border-radius: 12px !important;
}
.sidebar-toggle:hover, button.sidebar-toggle:hover {
    border-color: var(--accent) !important;
    color: var(--ink) !important;
    background: var(--surface-hover) !important;
}
.lang-toggle, button.lang-toggle {
    min-width: 64px !important;
    max-width: 84px !important;
    padding: 6px 12px !important;
    font-size: 0.92rem !important;
    font-weight: 700 !important;
    white-space: nowrap !important;
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    color: var(--ink-soft) !important;
    border-radius: 12px !important;
    flex: 0 0 auto !important;
}
.lang-toggle:hover, button.lang-toggle:hover {
    border-color: var(--accent) !important;
    color: var(--ink) !important;
    background: var(--surface-hover) !important;
}
.session-sidebar {
    position: sticky;
    top: 14px;
    align-self: flex-start;
    min-width: 200px;
    background: var(--surface) !important;
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 12px 10px !important;
    backdrop-filter: blur(22px) saturate(125%);
    -webkit-backdrop-filter: blur(22px) saturate(125%);
    box-shadow: 0 18px 44px rgba(0, 0, 0, 0.38);
    gap: 6px !important;
    max-height: 78vh;
    overflow-y: auto;
}
button.new-chat-btn, .new-chat-btn button {
    width: 100% !important;
    background: linear-gradient(150deg, var(--accent), var(--accent-strong)) !important;
    border: none !important;
    color: #fff !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    margin-bottom: 6px !important;
}
button.new-chat-btn:hover, .new-chat-btn button:hover {
    filter: brightness(1.08);
    box-shadow: 0 6px 18px var(--glow);
}
.session-empty {
    color: var(--ink-soft);
    font-size: 12.5px;
    text-align: center;
    padding: 14px 6px;
    opacity: 0.8;
}

/* Kişiselleştirme seviyesi rozeti (sidebar) */
.pers-badge { margin: 2px 0 10px 0 !important; }
.pers-badge-inner {
    background: var(--surface, rgba(255,255,255,0.04));
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 9px 11px;
}
.pers-badge-inner .pb-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}
.pers-badge-inner .pb-title {
    font-size: 11.5px;
    font-weight: 700;
    color: var(--ink-soft);
    letter-spacing: .3px;
}
.pers-badge-inner .pb-lvl {
    font-size: 11px;
    font-weight: 800;
    color: var(--accent);
}
.pers-badge-inner .pb-dots {
    display: flex;
    gap: 5px;
    margin-bottom: 6px;
}
.pers-badge-inner .pb-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--line-strong, var(--line));
    opacity: 0.55;
}
.pers-badge-inner .pb-dot.on {
    background: var(--accent);
    opacity: 1;
    box-shadow: 0 0 6px var(--glow);
}
.pers-badge-inner .pb-desc {
    font-size: 11px;
    line-height: 1.4;
    color: var(--ink-soft);
    opacity: 0.9;
}
.pers-badge-inner .pb-likes,
.pers-badge-inner .pb-dislikes {
    font-size: 11px;
    line-height: 1.45;
    color: var(--ink);
    word-break: break-word;
}
.pers-badge-inner .pb-dislikes { color: var(--ink-soft); opacity: 0.85; }
.pers-badge-inner .pb-tag {
    font-weight: 700;
    color: var(--accent);
    margin-right: 2px;
}
.pers-badge-inner .pb-dislikes .pb-tag { color: var(--ink-soft); }

/* Açık öneri geri bildirim satırı (👍/👎) — sohbet ile giriş arasında */
.feedback-row {
    align-items: center !important;
    gap: 8px !important;
    padding: 4px 2px 2px 2px !important;
    flex-wrap: wrap;
}
.feedback-row .feedback-q {
    font-size: 12.5px;
    color: var(--ink-soft);
    margin-right: 2px;
}
button.fb-btn, .fb-btn button {
    background: transparent !important;
    border: 1px solid var(--line) !important;
    color: var(--ink) !important;
    border-radius: 999px !important;
    font-weight: 600 !important;
    font-size: 12.5px !important;
    padding: 4px 14px !important;
    min-width: 0 !important;
    flex: 0 0 auto !important;
}
button.fb-btn:hover, .fb-btn button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    box-shadow: 0 4px 12px var(--glow);
}
/* Ayrı kapatma (✕) butonu — değerlendirme + takvim alanları */
button.dismiss-btn, .dismiss-btn button {
    background: transparent !important;
    border: 1px solid var(--line) !important;
    color: var(--ink-soft) !important;
    border-radius: 999px !important;
    font-size: 12px !important;
    line-height: 1 !important;
    padding: 4px 9px !important;
    min-width: 0 !important;
    flex: 0 0 auto !important;
}
button.dismiss-btn:hover, .dismiss-btn button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: var(--surface-hover) !important;
}
.feedback-row .dismiss-btn { margin-left: auto; }  /* ✕'i satırın sağına it */
.calendar-row {
    align-items: center !important;
    gap: 8px !important;
}
.session-row, .session-rename-row {
    gap: 4px !important;
    align-items: center !important;
    margin: 0 !important;
}
.session-row { border-radius: 10px; }
.session-row.active {
    background: var(--surface-hover) !important;
    box-shadow: inset 0 0 0 1px var(--accent);
}
button.session-select, .session-select button {
    text-align: left !important;
    justify-content: flex-start !important;
    background: transparent !important;
    border: none !important;
    color: var(--ink) !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    border-radius: 10px !important;
    padding: 8px 10px !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
button.session-select:hover, .session-select button:hover {
    background: var(--surface-strong) !important;
}
button.session-icon, .session-icon button {
    background: transparent !important;
    border: none !important;
    color: var(--ink-soft) !important;
    padding: 6px !important;
    font-size: 0.9rem !important;
    opacity: 0.7;
}
button.session-icon:hover, .session-icon button:hover {
    opacity: 1;
    color: var(--ink) !important;
    background: var(--surface-strong) !important;
}

/* Sohbet adı düzenleme alanı — dar sidebar'da dikey yerleşim + okunur input/buton */
.session-rename-row {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 6px !important;
    width: 100% !important;
    padding: 6px !important;
    margin: 2px 0 !important;
    background: var(--surface-hover) !important;
    border-radius: 10px !important;
}
.session-rename-row textarea,
.session-rename-row input {
    width: 100% !important;
    box-sizing: border-box !important;
    min-height: 38px !important;
    font-size: 13px !important;
    line-height: 1.35 !important;
    color: var(--ink) !important;
    background: var(--surface-strong) !important;
    border: 1px solid var(--accent) !important;
    border-radius: 8px !important;
    padding: 8px 10px !important;
    resize: none !important;
}
.session-rename-row button.session-icon,
.session-rename-row .session-icon button {
    align-self: flex-end !important;
    opacity: 1 !important;
    color: #fff !important;
    background: var(--accent) !important;
    border-radius: 8px !important;
    padding: 6px 16px !important;
    min-width: 48px !important;
    font-size: 1rem !important;
}
.session-rename-row button.session-icon:hover,
.session-rename-row .session-icon button:hover {
    background: var(--accent-strong, var(--accent)) !important;
    color: #fff !important;
}

/* ---- Sırada bekleyen mesajlar ---- */
.queued-display-wrapper { padding: 4px 0 0; }
.queued-display { display: flex; flex-direction: column; gap: 6px; }
.queued-msg-row {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
    padding: 0 12px;
}
.queued-msg-text {
    background: rgba(124, 58, 237, 0.15);
    border: 1px solid rgba(124, 58, 237, 0.25);
    border-radius: 18px 18px 4px 18px;
    padding: 8px 14px;
    color: var(--ink-soft);
    font-size: 0.92em;
    opacity: 0.7;
    max-width: 70%;
    word-break: break-word;
}
.queued-badge {
    color: var(--ink-soft);
    font-size: 0.72em;
    opacity: 0.55;
    white-space: nowrap;
}

/* ---- Boş durum (karşılama + öneri kartları) ---- */
/* min-height chatbot height (520px) ile eşleşmeli → geçişte layout kayması olmaz */
.empty-state {
    min-height: 520px;
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
.empty-state .greeting .onboarding-question {
    margin-top: 18px;
    padding: 16px 20px;
    background: var(--surface-strong);
    border-radius: 14px;
    border-left: 3px solid var(--accent);
    text-align: left;
    max-width: 460px;
    margin-left: auto;
    margin-right: auto;
}
.empty-state .greeting .onboarding-question p {
    margin: 4px auto;
    color: var(--ink);
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

/* ---- "En iyi saat" şeridi ---- */
.time-ribbon {
    margin-top: 14px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 12px 14px;
}
.tr-summary {
    font-size: 13px;
    font-weight: 600;
    color: var(--ink);
    margin-bottom: 9px;
}
.tr-track {
    display: flex;
    gap: 2px;
    align-items: flex-end;
}
.tr-cell {
    flex: 1 1 0;
    height: 26px;
    border-radius: 4px;
    position: relative;
    display: flex;
    justify-content: center;
    align-items: flex-end;
}
.tr-label {
    font-size: 9px;
    color: var(--ink-faint);
    position: absolute;
    bottom: -15px;
    white-space: nowrap;
}
.tr-track { margin-bottom: 16px; }
.tr-cell--good { background: rgba(74,222,128,0.55); }
.tr-cell--uv   { background: rgba(251,191,36,0.6); }
.tr-cell--rain { background: rgba(96,165,250,0.6); }
.tr-cell--hot  { background: rgba(248,113,113,0.6); }
.tr-cell--cold { background: rgba(167,139,250,0.6); }
.tr-legend {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--ink-faint);
    margin-top: 6px;
}
.tr-dot {
    width: 10px;
    height: 10px;
    border-radius: 3px;
    display: inline-block;
    margin-left: 10px;
}
.tr-legend .tr-dot:first-child { margin-left: 0; }

/* ---- Yağmur nowcast uyarısı ---- */
.rain-alert-wrap { padding: 0; }
.rain-alert {
    margin-top: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12.5px;
    font-weight: 600;
    line-height: 1.35;
    border-radius: 14px;
    padding: 10px 14px;
    border: 1px solid var(--line);
    background: var(--surface-strong);
    color: var(--ink);
}
.rain-alert--warn {
    border-color: rgba(96, 165, 250, 0.5);
    background: rgba(96, 165, 250, 0.14);
    box-shadow: 0 6px 18px rgba(96, 165, 250, 0.18);
}
.rain-alert--calm {
    border-color: rgba(74, 222, 128, 0.4);
    background: rgba(74, 222, 128, 0.12);
}

/* ---- Akıllı hafta planlayıcı ısı haritası ---- */
.week-heatmap {
    margin-top: 14px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    padding: 12px 14px;
}
.wh-summary {
    font-size: 13px;
    font-weight: 600;
    color: var(--ink);
    margin-bottom: 10px;
}
.wh-grid { display: flex; flex-direction: column; gap: 3px; }
.wh-row { display: flex; align-items: center; gap: 8px; }
.wh-day {
    flex: 0 0 32px;
    font-size: 10.5px;
    font-weight: 600;
    color: var(--ink-faint);
    text-align: right;
}
.wh-track { display: flex; gap: 2px; flex: 1 1 auto; }
.wh-track .tr-cell { height: 16px; border-radius: 3px; }
.wh-head { margin-bottom: 1px; }
.wh-head .wh-track { gap: 2px; }
.wh-hh {
    flex: 1 1 0;
    font-size: 9px;
    color: var(--ink-faint);
    text-align: center;
    white-space: nowrap;
}
.tr-cell--none { background: rgba(255, 255, 255, 0.06); }
.week-heatmap .tr-legend { margin-top: 9px; }

/* ---- Takvime ekle butonu ---- */
button.calendar-btn, .calendar-btn button {
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    color: var(--ink-soft) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    margin-top: 4px !important;
}
button.calendar-btn:hover, .calendar-btn button:hover {
    border-color: var(--accent) !important;
    color: var(--ink) !important;
    background: var(--surface-hover) !important;
}

/* ---- Favori mekanlar (sidebar listesi + kaydet/yönet kontrolleri) ---- */
.fav-title {
    font-size: 11.5px;
    font-weight: 700;
    color: var(--ink-soft);
    letter-spacing: .3px;
    margin: 12px 2px 6px;
}
.fav-box { margin-top: 4px; }
.fav-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    border-radius: 10px;
    font-size: 12.5px;
    color: var(--ink);
}
.fav-item:hover { background: var(--surface-strong); }
.fav-name {
    flex: 1 1 auto;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.fav-city { color: var(--ink-faint); font-size: 11px; flex: 0 0 auto; }
.fav-route { flex: 0 0 auto; text-decoration: none; opacity: 0.85; }
.fav-route:hover { opacity: 1; }
.fav-item.done .fav-name { color: var(--ink-faint); text-decoration: line-through; opacity: 0.78; }
.fav-manage-row { gap: 4px !important; align-items: center !important; margin: 2px 0 6px !important; }
.fav-save-row { gap: 6px !important; align-items: center !important; margin-top: 8px !important; }
button.fav-save-btn, .fav-save-btn button {
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    color: var(--ink-soft) !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 13px !important;
}
button.fav-save-btn:hover, .fav-save-btn button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: var(--surface-hover) !important;
}

/* ---- Seyahat karşılaştırma kartı ---- */
.travel-compare {
    margin-top: 14px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-left: 3px solid var(--accent);
    border-radius: 16px;
    padding: 11px 14px;
}
.tc-title {
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: .3px;
    color: var(--ink-soft);
    margin-bottom: 8px;
}
.tc-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    font-size: 13px;
    padding: 3px 0;
}
.tc-place { color: var(--ink-soft); font-weight: 600; }
.tc-temp { color: var(--ink); font-weight: 700; }
.tc-dest .tc-place, .tc-dest .tc-temp { color: var(--accent); }
.tc-diff {
    margin-top: 7px;
    font-size: 11.5px;
    color: var(--ink-faint);
    text-align: right;
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

/* ---- Suggestion store: DOM'da olsun ama görünmesin ---- */
.skywise-offscreen {
    position: absolute !important;
    left: -9999px !important;
    width: 1px !important;
    height: 1px !important;
    overflow: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
    tab-index: -1 !important;
}

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
.typing-indicator .typing-label {
    width: auto;
    height: auto;
    margin-left: 4px;
    background: none;
    border-radius: 0;
    animation: none;
    color: var(--ink-faint);
    font-size: 0.82em;
    font-style: italic;
    opacity: 0.7;
    letter-spacing: 0.01em;
}
@keyframes typing-bounce {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.45; }
    30% { transform: translateY(-5px); opacity: 1; }
}

/* ---- Skeleton shimmer (hava paneli yüklenirken) ---- */
.wx-skeleton {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
}
.wx-skeleton .sk {
    border-radius: 10px;
    background: linear-gradient(
        100deg,
        rgba(255, 255, 255, 0.04) 30%,
        rgba(255, 255, 255, 0.12) 50%,
        rgba(255, 255, 255, 0.04) 70%
    );
    background-size: 220% 100%;
    animation: sk-shimmer 1.4s ease-in-out infinite;
}
.wx-skeleton .sk-city { width: 55%; height: 18px; }
.wx-skeleton .sk-temp { width: 40%; height: 46px; border-radius: 14px; }
.wx-skeleton .sk-cond { width: 65%; height: 14px; }
.wx-skeleton .sk-row { display: flex; gap: 10px; margin-top: 6px; }
.wx-skeleton .sk-chip { width: 56px; height: 26px; border-radius: 13px; }
@keyframes sk-shimmer {
    0% { background-position: 180% 0; }
    100% { background-position: -80% 0; }
}

/* ---- Açılış "Hazırlanıyor" durumu ---- */
.startup-status-wrapper { padding: 2px 0 6px; }
.startup-status {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 9px;
    padding: 9px 14px;
    border-radius: 14px;
    background: var(--surface);
    border: 1px solid var(--line);
    color: var(--ink-soft);
    font-size: 0.88em;
    letter-spacing: 0.01em;
    backdrop-filter: blur(14px) saturate(120%);
    -webkit-backdrop-filter: blur(14px) saturate(120%);
    animation: startup-pulse 1.8s ease-in-out infinite;
}
.startup-status .startup-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex: 0 0 auto;
    border: 2px solid rgba(255, 255, 255, 0.18);
    border-top-color: var(--accent, #7c5cff);
    animation: startup-spin 0.8s linear infinite;
}
@keyframes startup-spin { to { transform: rotate(360deg); } }
@keyframes startup-pulse { 0%, 100% { opacity: 0.85; } 50% { opacity: 1; } }

/* ---- "Meşgul" / devre dışı giriş durumları ---- */
.chat-input-row button.primary:disabled,
.chat-input-row button.primary[disabled] {
    opacity: 0.55 !important;
    cursor: progress !important;
    filter: saturate(0.7);
}
.chat-input-row textarea:disabled,
.chat-input-row input:disabled {
    opacity: 0.6 !important;
    cursor: not-allowed !important;
}
.suggestion-btn:disabled,
.suggestion-btn[disabled] {
    opacity: 0.5 !important;
    cursor: not-allowed !important;
}

/* ---- Havaya duyarlı ambient arka plan animasyonu ---- */
/* Host bloğu yer kaplamasın; #wx-fx position:fixed ile viewport'u kaplar. */
.wx-fx-host {
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    border: 0 !important;
    overflow: visible !important;
}
#wx-fx {
    position: fixed;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
    z-index: 2;
}
.wx-fx-particle { position: absolute; top: -24px; will-change: transform, opacity; }

/* Yağmur (storm dahil) — ince, ekran karışımıyla hafif parıltılı çizgiler */
.wx-fx-rain { mix-blend-mode: screen; opacity: 0.5; }
.wx-fx-rain .wx-fx-particle {
    width: 1.5px;
    height: var(--h, 18px);
    background: linear-gradient(to bottom, rgba(180, 210, 255, 0), rgba(180, 210, 255, 0.75));
    animation: wx-rain linear infinite;
}
@keyframes wx-rain {
    0% { transform: translateY(-12vh); }
    100% { transform: translateY(112vh); }
}

/* Kar — yumuşak, hafif yana savrulan taneler */
.wx-fx-snow { opacity: 0.72; }
.wx-fx-snow .wx-fx-particle {
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 0 4px rgba(255, 255, 255, 0.5);
    animation: wx-snow linear infinite;
}
@keyframes wx-snow {
    0% { transform: translate(0, -8vh); opacity: 0; }
    12% { opacity: 1; }
    88% { opacity: 1; }
    100% { transform: translate(var(--drift, 0), 110vh); opacity: 0.4; }
}

/* Gece — üst bölgede sönüp parlayan yıldızlar */
.wx-fx-stars { opacity: 0.9; }
.wx-fx-stars .wx-fx-particle {
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 0 6px rgba(255, 255, 255, 0.7);
    animation: wx-twinkle ease-in-out infinite;
}
@keyframes wx-twinkle {
    0%, 100% { opacity: 0.15; transform: scale(0.7); }
    50% { opacity: 0.95; transform: scale(1); }
}

@media (prefers-reduced-motion: reduce) {
    #wx-fx { display: none !important; }
}

/* ---- Mobil ---- */
@media (max-width: 860px) {
    .main-row { flex-direction: column !important; }
    .panel-col { position: static; width: 100% !important; }
    .session-sidebar { position: static; width: 100% !important; max-height: 220px; }
    .wx-panel { padding: 22px 18px; }
    .wx-icon svg { width: 88px; height: 88px; }
    .wx-temp { font-size: 50px; }
    .brand { font-size: 1.25rem; }
    .brand-tag { display: none; }
    .empty-state { min-height: 360px; }
}
"""
