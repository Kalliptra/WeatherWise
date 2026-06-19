"""SkyWise UI teması: hava durumuna göre dinamik renk paletleri, SVG ikonlar ve panel HTML'i.

Tema, `document.body.dataset.theme` üzerinden seçilir; her tema yalnızca CSS
değişkenlerini override eder, bileşen stilleri tek bir yerde tanımlıdır.
"""


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

    meta_parts = []
    if sunset_str:
        meta_parts.append(f"🌅 {sunset_str}")
    if uv_index is not None and uv_level:
        meta_parts.append(f"☀ UV {uv_index} ({uv_level})")
    meta_html = (
        f'<div class="wx-meta">{"&nbsp;&nbsp;|&nbsp;&nbsp;".join(meta_parts)}</div>'
        if meta_parts else ""
    )

    return (
        '<div class="wx-panel">'
        f'<div class="wx-icon">{icon}</div>'
        f'<div class="wx-temp">{temp}°</div>'
        f'<div class="wx-feels">Hissedilen {feels}°</div>'
        f'<div class="wx-cond">{condition}</div>'
        f'<div class="wx-city">{place}</div>'
        f"{meta_html}"
        "</div>"
    )


def render_map_panel(venues: list[dict]) -> str:
    """Leaflet.js haritası — venue listesi için marker'lar ve rota linkleri içerir."""
    if not venues:
        return ""

    valid = [v for v in venues if v.get("lat") and v.get("lon")]
    if not valid:
        return ""

    center_lat = sum(v["lat"] for v in valid) / len(valid)
    center_lon = sum(v["lon"] for v in valid) / len(valid)

    markers_js = ""
    for v in valid:
        name = v["name"].replace("'", "\\'").replace('"', '\\"')
        rating = f" ⭐{v['rating']}" if v.get("rating") else ""
        maps_url = v.get("maps_url", "")
        popup = f"{name}{rating}"
        if maps_url:
            popup += f'<br><a href=\\"{maps_url}\\" target=\\"_blank\\" style=\\"color:#4fa3c7;font-weight:600\\">🗺 Rota Al</a>'
        markers_js += (
            f"L.marker([{v['lat']}, {v['lon']}])"
            f".addTo(map)"
            f".bindPopup('{popup}');\n"
        )

    return f"""
<div style="margin-top:14px;">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<div id="skywise-map" style="height:240px;border-radius:16px;overflow:hidden;border:1px solid rgba(0,0,0,0.12);"></div>
<script>
setTimeout(function() {{
  if (typeof L === 'undefined') return;
  if (document.getElementById('skywise-map')._leaflet_id) return;
  var map = L.map('skywise-map').setView([{center_lat}, {center_lon}], 14);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '© OpenStreetMap contributors'
  }}).addTo(map);
  {markers_js}
}}, 300);
</script>
</div>
"""


def render_panel_placeholder(message: str) -> str:
    return (
        '<div class="wx-panel wx-panel-empty">'
        f'<div class="wx-icon">{ICONS["clouds"]}</div>'
        f'<div class="wx-cond">{message}</div>'
        "</div>"
    )


# ---- CSS -------------------------------------------------------------------

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Gökyüzü gradyanı renk duraklarını kayıtlı property yap → yumuşak crossfade */
@property --sky-1 { syntax: '<color>'; inherits: true; initial-value: #58aee9; }
@property --sky-2 { syntax: '<color>'; inherits: true; initial-value: #a8d4f5; }
@property --sky-3 { syntax: '<color>'; inherits: true; initial-value: #fdf0d5; }

/* ---- Tema paletleri (yalnızca değişkenler) ---- */
body, body[data-theme="clear-day"] {
    --sky-1: #58aee9;
    --sky-2: #a8d4f5;
    --sky-3: #fdf0d5;
    --accent: #f29f05;
    --accent-strong: #e08700;
    --on-accent: #2b1f06;
    --ink: #16314a;
    --ink-soft: #3d5a75;
    --ink-faint: #6c87a0;
    --hero-ink: #10283d;
    --hero-soft: #2f4f6c;
    --line: rgba(22, 49, 74, 0.14);
    --surface: rgba(255, 255, 255, 0.45);
    --surface-strong: rgba(255, 255, 255, 0.74);
    --glow: rgba(242, 159, 5, 0.32);
    --icon-main: #ffc233;
    --icon-soft: #ffffff;
    color-scheme: light;
}
body[data-theme="night"] {
    --sky-1: #0a0f2c;
    --sky-2: #16204a;
    --sky-3: #2b3a6e;
    --accent: #8ab4ff;
    --accent-strong: #5f8fe8;
    --on-accent: #0a132e;
    --ink: #e9eefc;
    --ink-soft: #b8c4e6;
    --ink-faint: #8593c0;
    --hero-ink: #f2f5ff;
    --hero-soft: #c3cdea;
    --line: rgba(233, 238, 252, 0.16);
    --surface: rgba(255, 255, 255, 0.07);
    --surface-strong: rgba(255, 255, 255, 0.13);
    --glow: rgba(138, 180, 255, 0.26);
    --icon-main: #ffe9a8;
    --icon-soft: #cfe0ff;
    color-scheme: dark;
}
body[data-theme="clouds"] {
    --sky-1: #8da9bf;
    --sky-2: #b9cad8;
    --sky-3: #edf2f6;
    --accent: #4a7ba6;
    --accent-strong: #3a6388;
    --on-accent: #f4f9fd;
    --ink: #243646;
    --ink-soft: #4a6075;
    --ink-faint: #76889a;
    --hero-ink: #1c2c3a;
    --hero-soft: #3c5266;
    --line: rgba(36, 54, 70, 0.14);
    --surface: rgba(255, 255, 255, 0.5);
    --surface-strong: rgba(255, 255, 255, 0.78);
    --glow: rgba(74, 123, 166, 0.26);
    --icon-main: #7d9cb5;
    --icon-soft: #ffffff;
    color-scheme: light;
}
body[data-theme="rain"] {
    --sky-1: #3f5b75;
    --sky-2: #6e8aa3;
    --sky-3: #b6c6d4;
    --accent: #4fa3c7;
    --accent-strong: #3c87ab;
    --on-accent: #06222e;
    --ink: #20323f;
    --ink-soft: #486073;
    --ink-faint: #7b8fa0;
    --hero-ink: #eef4f9;
    --hero-soft: #c2d2de;
    --line: rgba(32, 50, 63, 0.15);
    --surface: rgba(255, 255, 255, 0.42);
    --surface-strong: rgba(255, 255, 255, 0.72);
    --glow: rgba(79, 163, 199, 0.3);
    --icon-main: #5d7f99;
    --icon-soft: #4fa3c7;
    color-scheme: light;
}
body[data-theme="storm"] {
    --sky-1: #131120;
    --sky-2: #221f3a;
    --sky-3: #3b3560;
    --accent: #ffd23f;
    --accent-strong: #f0b90b;
    --on-accent: #241c02;
    --ink: #ece9f8;
    --ink-soft: #c2bcdd;
    --ink-faint: #8d86b3;
    --hero-ink: #f4f2fc;
    --hero-soft: #cdc7e6;
    --line: rgba(236, 233, 248, 0.16);
    --surface: rgba(255, 255, 255, 0.07);
    --surface-strong: rgba(255, 255, 255, 0.12);
    --glow: rgba(255, 210, 63, 0.24);
    --icon-main: #ffd23f;
    --icon-soft: #6f6899;
    color-scheme: dark;
}
body[data-theme="snow"] {
    --sky-1: #c8e0f0;
    --sky-2: #e4eff7;
    --sky-3: #ffffff;
    --accent: #3f8fc4;
    --accent-strong: #2f74a3;
    --on-accent: #f3f9fd;
    --ink: #1f3b50;
    --ink-soft: #46607a;
    --ink-faint: #7e95a9;
    --hero-ink: #183245;
    --hero-soft: #3a566f;
    --line: rgba(31, 59, 80, 0.12);
    --surface: rgba(255, 255, 255, 0.55);
    --surface-strong: rgba(255, 255, 255, 0.85);
    --glow: rgba(63, 143, 196, 0.22);
    --icon-main: #6db3e0;
    --icon-soft: #b5d9f0;
    color-scheme: light;
}
body[data-theme="fog"] {
    --sky-1: #aab3ae;
    --sky-2: #c9cfc9;
    --sky-3: #ebece8;
    --accent: #5f7268;
    --accent-strong: #4b5c53;
    --on-accent: #f2f5f1;
    --ink: #2c3531;
    --ink-soft: #54625b;
    --ink-faint: #828e87;
    --hero-ink: #232b27;
    --hero-soft: #46534c;
    --line: rgba(44, 53, 49, 0.13);
    --surface: rgba(255, 255, 255, 0.5);
    --surface-strong: rgba(255, 255, 255, 0.75);
    --glow: rgba(95, 114, 104, 0.22);
    --icon-main: #93a09a;
    --icon-soft: #c5cdc8;
    color-scheme: light;
}

/* ---- Zemin ---- */
html, body {
    min-height: 100vh;
}
body {
    background: linear-gradient(180deg, var(--sky-1) 0%, var(--sky-2) 55%, var(--sky-3) 100%) fixed !important;
    transition: --sky-1 0.9s ease, --sky-2 0.9s ease, --sky-3 0.9s ease;
    color: var(--ink) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
gradio-app, .gradio-container,
.gradio-container .main,
.gradio-container .wrap,
.gradio-container .app {
    background: transparent !important;
}
.gradio-container {
    max-width: 1180px !important;
    margin: 0 auto !important;
    padding-top: 24px !important;
    color: var(--ink) !important;
}
footer { display: none !important; }

/* Tema geçişinde bileşen renkleri de yumuşasın */
.wx-panel, .chat-surface, .chat-area .message.user, .chat-area .message.bot,
.suggestion-btn, button.primary, textarea, input[type="text"] {
    transition: background-color 0.6s ease, color 0.6s ease,
                border-color 0.6s ease, box-shadow 0.6s ease !important;
}

/* ---- Hero ---- */
.hero {
    text-align: center;
    background: transparent !important;
    padding: 4px 0 18px 0 !important;
}
.hero .eyebrow {
    display: inline-block;
    font-size: 11px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--hero-soft) !important;
    font-weight: 700;
    margin-bottom: 10px;
}
.hero h1 {
    font-weight: 800 !important;
    font-size: 2.1rem !important;
    line-height: 1.15 !important;
    letter-spacing: -0.6px !important;
    color: var(--hero-ink) !important;
    margin: 0 auto 6px auto !important;
}
.hero p {
    font-size: 15px !important;
    line-height: 1.5 !important;
    color: var(--hero-soft) !important;
    max-width: 560px;
    margin: 0 auto !important;
}

/* ---- Hava paneli ---- */
.wx-panel {
    background: var(--surface) !important;
    backdrop-filter: blur(16px) saturate(130%);
    -webkit-backdrop-filter: blur(16px) saturate(130%);
    border: 1px solid var(--line);
    border-radius: 24px;
    padding: 34px 22px;
    text-align: center;
    box-shadow: 0 18px 50px rgba(10, 20, 35, 0.14);
}
.panel-col { position: sticky; top: 16px; align-self: flex-start; }
.wx-icon svg {
    width: 112px;
    height: 112px;
    display: block;
    margin: 0 auto 10px auto;
    filter: drop-shadow(0 6px 14px rgba(10, 20, 35, 0.18));
}
.wx-temp {
    font-size: 64px;
    font-weight: 800;
    letter-spacing: -2px;
    line-height: 1;
    color: var(--ink);
}
.wx-feels {
    font-size: 14px;
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
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin-top: 4px;
}
.wx-panel-empty .wx-cond { font-weight: 600; color: var(--ink-faint); }
.wx-meta {
    font-size: 12px;
    font-weight: 600;
    color: var(--ink-faint);
    margin-top: 10px;
    letter-spacing: 0.04em;
}

/* ---- Chat yüzeyi ---- */
.chat-surface {
    background: var(--surface) !important;
    backdrop-filter: blur(16px) saturate(130%);
    -webkit-backdrop-filter: blur(16px) saturate(130%);
    border: 1px solid var(--line) !important;
    border-radius: 24px !important;
    box-shadow: 0 18px 50px rgba(10, 20, 35, 0.14) !important;
    padding: 18px !important;
}
.chat-surface label, .chat-surface span, .chat-surface p { color: var(--ink) !important; }

.chat-area {
    background: transparent !important;
    border: none !important;
}
.chat-area .message.user,
.chat-area .message-bubble-border.user {
    background: linear-gradient(150deg, var(--accent), var(--accent-strong)) !important;
    color: var(--on-accent) !important;
    border: none !important;
    border-radius: 16px 16px 4px 16px !important;
    font-weight: 600 !important;
    box-shadow: 0 8px 22px var(--glow) !important;
}
.chat-area .message.user p,
.chat-area .message.user strong { color: var(--on-accent) !important; }
.chat-area .message.bot,
.chat-area .message-bubble-border.bot {
    background: var(--surface-strong) !important;
    color: var(--ink) !important;
    border: 1px solid var(--line) !important;
    border-radius: 16px 16px 16px 4px !important;
    box-shadow: 0 6px 18px rgba(10, 20, 35, 0.08) !important;
}
.chat-area .message.bot p,
.chat-area .message.bot li,
.chat-area .message.bot strong,
.chat-area .message.bot h1,
.chat-area .message.bot h2,
.chat-area .message.bot h3 { color: var(--ink) !important; }
.chat-area .message.bot em { color: var(--accent-strong) !important; }
.chat-area .message.bot a { color: var(--accent-strong) !important; font-weight: 600; }
.chat-area .message.bot code {
    background: var(--surface) !important;
    color: var(--ink) !important;
    border: 1px solid var(--line) !important;
    border-radius: 6px !important;
    padding: 1px 6px !important;
    font-size: 0.9em;
}

/* ---- Giriş alanı ---- */
.chat-input-row { margin-top: 12px !important; }
textarea, input[type="text"] {
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    color: var(--ink) !important;
    font-size: 16px !important;
}
textarea::placeholder, input::placeholder {
    color: var(--ink-faint) !important;
    font-weight: 500 !important;
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
    box-shadow: 0 14px 32px var(--glow) !important;
}
.chat-surface button:not(.primary):not(.suggestion-btn) {
    background: var(--surface-strong) !important;
    border: 1px solid var(--line) !important;
    color: var(--ink-soft) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}
.chat-surface button:not(.primary):not(.suggestion-btn):hover {
    border-color: var(--accent) !important;
    color: var(--ink) !important;
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
    margin-bottom: 18px;
}
.empty-state .greeting .wave { font-size: 38px; line-height: 1; }
.empty-state .greeting h2 {
    font-size: 22px;
    font-weight: 800;
    color: var(--ink);
    margin: 10px 0 6px 0;
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
    box-shadow: 0 4px 14px rgba(10, 20, 35, 0.06) !important;
    transition: border-color 0.15s ease, color 0.15s ease, transform 0.15s ease,
                box-shadow 0.15s ease, background-color 0.6s ease !important;
}
button.suggestion-btn:hover {
    border-color: var(--accent) !important;
    color: var(--ink) !important;
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(10, 20, 35, 0.12) !important;
}

/* ---- Kaydırma çubuğu ---- */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--line); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-strong); }

/* ---- Footer ---- */
.footer-note {
    text-align: center;
    background: transparent !important;
    margin-top: 20px;
    padding-top: 12px;
    border-top: 1px solid var(--line);
}
.footer-note p,
.footer-note strong { color: var(--ink-faint) !important; font-weight: 600 !important; }

/* ---- Mobil ---- */
@media (max-width: 860px) {
    .main-row { flex-direction: column !important; }
    .panel-col { position: static; width: 100% !important; }
    .wx-panel { padding: 22px 18px; }
    .wx-icon svg { width: 84px; height: 84px; }
    .wx-temp { font-size: 48px; }
    .hero h1 { font-size: 1.6rem !important; }
    .empty-state { min-height: 360px; }
}
"""
