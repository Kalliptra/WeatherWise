import gradio_client.utils as _gcu

_original_jspt = _gcu._json_schema_to_python_type
_original_get_type = _gcu.get_type


def _safe_get_type(schema):
    if isinstance(schema, bool):
        return "Any"
    return _original_get_type(schema)


def _safe_jspt(schema, defs=None):
    if isinstance(schema, bool):
        return "Any"
    return _original_jspt(schema, defs)


_gcu.get_type = _safe_get_type
_gcu._json_schema_to_python_type = _safe_jspt

import os  # noqa: E402

import gradio as gr  # noqa: E402

from chat import chat_skywise, clear_last_location, get_last_locations, generate_next_suggestion, generate_location_suggestions, set_user_location  # noqa: E402
from ui_theme import (  # noqa: E402
    CUSTOM_CSS,
    render_locations_map,
    render_map_panel,
    render_panel_placeholder,
    render_weather_panel,
    weather_to_theme,
)
from tools.weather import (  # noqa: E402
    clear_last_weather,
    get_last_weather,
    get_weather,
    get_weather_by_coords,
)
from tools.venue import clear_last_venues, geocode_city, get_last_venues  # noqa: E402

DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Istanbul")

ORNEK_SORULAR = [
    "Bugün İstanbul'da hava nasıl, ne yapabilirim?",
    "Ankara'da iç mekân aktiviteleri öner",
    "What can I do in Paris today?",
    "Recommend a museum in London",
]

KARSILAMA_HTML = """
<div class="greeting">
    <div class="wave">🌙</div>
    <h2>Merhaba! Ben SkyWise</h2>
    <p>Hava durumuna göre aktivite öneren asistanın. Bir şehir ve nasıl bir
    aktivite aradığını yaz; senin için anlık öneriler ve harita hazırlayayım.</p>
</div>
"""

GEO_JS = """
async () => {
    try {
        const pos = await new Promise((resolve, reject) =>
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                timeout: 6000,
                maximumAge: 600000,
            })
        );
        return pos.coords.latitude.toFixed(4) + "," + pos.coords.longitude.toFixed(4);
    } catch (e) {
        return "";
    }
}
"""

THEME_JS = "(t) => { document.body.dataset.theme = t || 'clear-day'; }"

# Yanıt beklenirken gösterilen "yazıyor..." üç nokta animasyonu
TYPING_INDICATOR = (
    '<div class="typing-indicator"><span></span><span></span><span></span></div>'
)

# Gradio'nun kendi koyu modunu zorla (dahili bileşenler de koyuya uysun) +
# tema set edilene kadar varsayılan accent görünsün
FORCE_DARK_JS = """
() => {
    const app = document.querySelector('gradio-app');
    if (app) app.setAttribute('theme', 'dark');
    document.documentElement.classList.add('dark');
    if (!document.body.dataset.theme) document.body.dataset.theme = 'clear-day';

    document.addEventListener('keydown', function(e) {
        if (e.key !== 'Tab') return;
        var sugBox = document.querySelector('#skywise-suggestion textarea, #skywise-suggestion input');
        if (!sugBox || !sugBox.value) return;
        var chatInput = document.querySelector('.chat-input-row textarea');
        if (!chatInput) return;
        e.preventDefault();
        chatInput.value = sugBox.value;
        chatInput.dispatchEvent(new Event('input', { bubbles: true }));
        chatInput.focus();
    });
}
"""


def render_queued_display(queued: list) -> str:
    if not queued:
        return ""
    items = "".join(
        f'<div class="queued-msg-row"><span class="queued-msg-text">{q}</span>'
        f'<span class="queued-badge">🕒 Sırada</span></div>'
        for q in queued
    )
    return f'<div class="queued-display">{items}</div>'


def pre_submit(user_message: str, queued: list):
    msg = (user_message or "").strip()
    base = list(queued or [])
    if not msg:
        return "", base, render_queued_display(base)
    new_queued = base + [msg]
    return "", new_queued, render_queued_display(new_queued)


def respond_from_history(history: list[dict], queued: list):
    """Yields: (chatbot, textbox, empty_state, weather_panel, theme_state, map_panel, show_loc_btn, location_state, suggestion_box, queued_state, queued_display)."""
    if not queued:
        return

    user_message = queued[0]
    remaining = list(queued[1:])
    qd = render_queued_display(remaining)

    history = list(history or [])
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": TYPING_INDICATOR})

    yield gr.update(value=history, visible=True), gr.update(), gr.update(visible=False), gr.update(), gr.update(), gr.update(), gr.update(visible=False), [], gr.update(), remaining, qd

    convo_for_agent = history[:-1]
    clear_last_weather()
    clear_last_venues()
    clear_last_location()
    panel_sent = False
    map_sent = False

    try:
        for partial in chat_skywise(convo_for_agent):
            history[-1]["content"] = partial if partial else TYPING_INDICATOR
            weather = get_last_weather()
            venues = get_last_venues()

            if weather is not None and not panel_sent:
                panel_sent = True
                yield history, gr.update(), gr.update(), render_weather_panel(weather), weather_to_theme(weather), gr.update(), gr.update(), gr.update(), gr.update(), remaining, qd
            elif venues and not map_sent:
                map_sent = True
                map_html = render_map_panel(venues)
                yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=map_html, visible=bool(map_html)), gr.update(visible=False), gr.update(), gr.update(), remaining, qd
            else:
                yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), remaining, qd

        if not map_sent:
            venues = get_last_venues()
            if venues:
                map_html = render_map_panel(venues)
                if map_html:
                    yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=map_html, visible=True), gr.update(visible=False), gr.update(), gr.update(), remaining, qd
                    map_sent = True

        if not map_sent:
            locs = get_last_locations()
            if locs:
                btn_label = (
                    f"📍 {locs[0]} konumunu haritada göster"
                    if len(locs) == 1
                    else f"📍 Bunları haritada göster ({len(locs)} yer)"
                )
                yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=btn_label, visible=True), locs, gr.update(), remaining, qd

        hint, suggestion = generate_next_suggestion(history)
        default_placeholder = "Mesajını yaz... (örn: \"Bugün İstanbul'da ne yapsam?\")"
        yield (
            gr.update(),
            gr.update(value="", placeholder=hint if hint else default_placeholder),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            suggestion,
            remaining,
            qd,
        )

    except ValueError as e:
        history[-1]["content"] = f"> ⚠️ {e}"
        yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), remaining, qd
    except Exception as e:
        history[-1]["content"] = f"> ⚠️ Bir hata oluştu: {e}"
        yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), remaining, qd


def clear_chat():
    clear_last_venues()
    clear_last_location()
    return (
        gr.update(value=[], visible=False),
        gr.update(visible=True),
        "",
        gr.update(value="", visible=False),
        gr.update(visible=False),
        "",
        [],
        "",
    )


def show_location_on_map(location_names):
    """Lokasyon adlarını geocode edip haritada gösterir (tek veya çok)."""
    if not location_names:
        return gr.update(), gr.update(visible=False)
    if isinstance(location_names, str):
        location_names = [location_names]
    coords = []
    for name in location_names:
        try:
            lat, lon = geocode_city(name)
            coords.append((name, lat, lon))
        except Exception:
            continue
    if not coords:
        return gr.update(), gr.update(visible=False)
    map_html = render_locations_map(coords)
    return gr.update(value=map_html, visible=True), gr.update(visible=False)


def load_default_city():
    try:
        weather = get_weather(DEFAULT_CITY)
        return render_weather_panel(weather), weather_to_theme(weather)
    except Exception:
        return render_panel_placeholder("Hava durumu alınamadı."), "clear-day"


_GENEL_ONERILER = [
    "Bulunduğum yerde bugün hava nasıl?",
    "Yakınımda ne yapabilirim?",
    "What's the weather like near me today?",
    "Recommend something to do nearby",
]


def apply_geolocation(coords: str):
    try:
        lat, lon = (float(x) for x in (coords or "").split(","))
        weather = get_weather_by_coords(lat, lon)
        set_user_location(weather["city"])
        suggestions = generate_location_suggestions(weather["city"], weather["country"], weather)
        btn_updates = [gr.update(value=s) for s in suggestions]
        return render_weather_panel(weather), weather_to_theme(weather), *btn_updates
    except Exception:
        btn_updates = [gr.update(value=s) for s in _GENEL_ONERILER]
        return gr.update(), gr.update(), *btn_updates


with gr.Blocks(
    title="SkyWise — Hava Durumu Aktivite Asistanı",
    theme=gr.themes.Base(
        primary_hue="indigo",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    ),
    css=CUSTOM_CSS,
    js=FORCE_DARK_JS,
) as demo:
    gr.HTML(
        """
        <div class="topbar">
            <div class="brand"><span class="brand-logo">◐</span> SkyWise</div>
            <div class="brand-tag">Hava durumuna göre kişisel aktivite asistanın</div>
        </div>
        """,
    )

    location_state = gr.State("")
    queued_state = gr.State([])

    with gr.Row(elem_classes="main-row"):
        with gr.Column(scale=2, min_width=260, elem_classes="panel-col"):
            weather_panel = gr.HTML(render_panel_placeholder("Hava durumu yükleniyor..."))
            map_panel = gr.HTML(value="", visible=False)
            show_loc_btn = gr.Button("📍 Konumu Haritada Göster", visible=False, elem_classes="loc-btn")

        with gr.Column(scale=5, elem_classes="chat-surface"):
            with gr.Column(visible=True, elem_classes="empty-state") as empty_state:
                gr.HTML(KARSILAMA_HTML)
                with gr.Row():
                    sug1 = gr.Button(ORNEK_SORULAR[0], elem_classes="suggestion-btn")
                    sug2 = gr.Button(ORNEK_SORULAR[1], elem_classes="suggestion-btn")
                with gr.Row():
                    sug3 = gr.Button(ORNEK_SORULAR[2], elem_classes="suggestion-btn")
                    sug4 = gr.Button(ORNEK_SORULAR[3], elem_classes="suggestion-btn")

            chatbot = gr.Chatbot(
                value=[],
                visible=False,
                type="messages",
                height=520,
                elem_classes="chat-area",
                show_copy_button=True,
                show_label=False,
                avatar_images=(None, None),
            )

            queued_display = gr.HTML(value="", elem_classes="queued-display-wrapper")

            with gr.Row(elem_classes="chat-input-row"):
                textbox = gr.Textbox(
                    placeholder="Mesajını yaz... (örn: \"Bugün İstanbul'da ne yapsam?\")",
                    scale=9,
                    container=False,
                    lines=1,
                    show_label=False,
                )
                send_btn = gr.Button("Gönder ↗", variant="primary", scale=1)

            with gr.Row():
                clear_btn = gr.Button("🗑 Sohbeti Temizle", size="sm", elem_classes="clear-btn")

    gr.Markdown(
        """
        ---
        **SEN4018 Dönem Projesi** | Samet Soydan & Emre Sarkuş | Bahçeşehir Üniversitesi
        """,
        elem_classes="footer-note",
    )

    theme_state = gr.Textbox(visible=False, elem_id="theme-state")
    geo_coords = gr.Textbox(visible=False, elem_id="geo-coords")
    suggestion_box = gr.Textbox(visible=False, elem_id="skywise-suggestion", interactive=False)

    RESPOND_OUTPUTS = [chatbot, textbox, empty_state, weather_panel, theme_state, map_panel, show_loc_btn, location_state, suggestion_box, queued_state, queued_display]
    PRE_OUTPUTS = [textbox, queued_state, queued_display]

    for trigger in (textbox.submit, send_btn.click):
        (trigger(pre_submit, [textbox, queued_state], PRE_OUTPUTS, api_name=False)
         .then(respond_from_history, [chatbot, queued_state], RESPOND_OUTPUTS, concurrency_limit=1, api_name=False))
    for sug in (sug1, sug2, sug3, sug4):
        (sug.click(pre_submit, [sug, queued_state], PRE_OUTPUTS, api_name=False)
         .then(respond_from_history, [chatbot, queued_state], RESPOND_OUTPUTS, concurrency_limit=1, api_name=False))
    clear_btn.click(
        clear_chat, None,
        [chatbot, empty_state, textbox, map_panel, show_loc_btn, location_state, queued_state, queued_display],
        api_name=False,
    )
    show_loc_btn.click(show_location_on_map, location_state, [map_panel, show_loc_btn], api_name=False)

    theme_state.change(None, theme_state, None, js=THEME_JS, api_name=False)

    demo.load(load_default_city, None, [weather_panel, theme_state], api_name=False)
    demo.load(None, None, geo_coords, js=GEO_JS, api_name=False)
    geo_coords.change(apply_geolocation, geo_coords, [weather_panel, theme_state, sug1, sug2, sug3, sug4], api_name=False)


if __name__ == "__main__":
    demo.queue(max_size=20)
    demo.launch(show_error=True, show_api=False, server_name="127.0.0.1")
