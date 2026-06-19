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

from chat import chat_skywise  # noqa: E402
from ui_theme import (  # noqa: E402
    CUSTOM_CSS,
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

DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Istanbul")

ORNEK_SORULAR = [
    "Bugün İstanbul'da hava nasıl, ne yapabilirim?",
    "Ankara'da iç mekân aktiviteleri öner",
    "Antalya'da plaj ve yüzme için bugün uygun mu?",
    "Eskişehir'de bu hafta sonu için müze önerin var mı?",
]

KARSILAMA_HTML = """
<div class="greeting">
    <div class="wave">👋</div>
    <h2>Merhaba! Ben SkyWise</h2>
    <p>Hava durumuna göre aktivite öneren asistanın. Hangi şehirde olduğunu
    ve nasıl bir aktivite aradığını söyle, sana özel öneriler hazırlayayım.</p>
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


def respond(user_message: str, history: list[dict]):
    """Yields: (chatbot, textbox, empty_state, weather_panel, theme_state)."""
    user_message = (user_message or "").strip()
    if not user_message:
        yield gr.update(), "", gr.update(), gr.update(), gr.update()
        return

    history = list(history or [])
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": ""})

    # Kullanıcı mesajı anında görünsün; boş durum kartları kaybolsun
    yield gr.update(value=history, visible=True), "", gr.update(visible=False), gr.update(), gr.update()

    convo_for_agent = history[:-1]
    clear_last_weather()
    panel_sent = False

    try:
        for partial in chat_skywise(convo_for_agent):
            history[-1]["content"] = partial
            weather = get_last_weather()
            if weather is not None and not panel_sent:
                panel_sent = True
                yield history, "", gr.update(), render_weather_panel(weather), weather_to_theme(weather)
            else:
                yield history, "", gr.update(), gr.update(), gr.update()
    except ValueError as e:
        history[-1]["content"] = f"> ⚠️ {e}"
        yield history, "", gr.update(), gr.update(), gr.update()
    except Exception as e:
        history[-1]["content"] = f"> ⚠️ Bir hata oluştu: {e}"
        yield history, "", gr.update(), gr.update(), gr.update()


def clear_chat():
    return gr.update(value=[], visible=False), gr.update(visible=True), ""


def load_default_city():
    try:
        weather = get_weather(DEFAULT_CITY)
        return render_weather_panel(weather), weather_to_theme(weather)
    except Exception:
        return render_panel_placeholder("Hava durumu alınamadı."), "clear-day"


def apply_geolocation(coords: str):
    try:
        lat, lon = (float(x) for x in (coords or "").split(","))
        weather = get_weather_by_coords(lat, lon)
        return render_weather_panel(weather), weather_to_theme(weather)
    except Exception:
        # Konum reddedildi/alınamadı → varsayılan şehir zaten ekranda
        return gr.update(), gr.update()


with gr.Blocks(
    title="SkyWise — Hava Durumu Aktivite Asistanı",
    theme=gr.themes.Base(
        primary_hue="blue",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    ),
    css=CUSTOM_CSS,
) as demo:
    gr.HTML(
        """
        <div class="hero">
            <div class="eyebrow">Hava Durumu Aktivite Asistanı</div>
            <h1>SkyWise</h1>
            <p>Şehrini yaz, bugünün havasına en uygun aktiviteleri anında öner.</p>
        </div>
        """,
    )

    with gr.Row(elem_classes="main-row"):
        with gr.Column(scale=2, min_width=260, elem_classes="panel-col"):
            weather_panel = gr.HTML(render_panel_placeholder("Hava durumu yükleniyor..."))

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
                clear_btn = gr.Button("🗑 Sohbeti Temizle", size="sm")

    gr.Markdown(
        """
        ---
        **SEN4018 Dönem Projesi** | Samet Soydan & Emre Sarkuş | Bahçeşehir Üniversitesi
        """,
        elem_classes="footer-note",
    )

    theme_state = gr.Textbox(visible=False, elem_id="theme-state")
    geo_coords = gr.Textbox(visible=False, elem_id="geo-coords")

    OUTPUTS = [chatbot, textbox, empty_state, weather_panel, theme_state]

    textbox.submit(respond, [textbox, chatbot], OUTPUTS, api_name=False)
    send_btn.click(respond, [textbox, chatbot], OUTPUTS, api_name=False)
    for sug in (sug1, sug2, sug3, sug4):
        sug.click(respond, [sug, chatbot], OUTPUTS, api_name=False)
    clear_btn.click(clear_chat, None, [chatbot, empty_state, textbox], api_name=False)

    theme_state.change(None, theme_state, None, js=THEME_JS, api_name=False)

    demo.load(load_default_city, None, [weather_panel, theme_state], api_name=False)
    demo.load(None, None, geo_coords, js=GEO_JS, api_name=False)
    geo_coords.change(apply_geolocation, geo_coords, [weather_panel, theme_state], api_name=False)


if __name__ == "__main__":
    demo.launch(show_error=True, show_api=False, server_name="127.0.0.1")
