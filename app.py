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

import gradio as gr  # noqa: E402

from agent import chat_skywise  # noqa: E402


CUSTOM_CSS = """
/* ---- Skyline · Clear · editorial warm palette ---- */
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400;1,500&family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --accent: #f59e0b;
    --accent-2: #d97706;
    --accent-ink: #3a2410;
    --glow: rgba(217, 119, 6, 0.32);
    --ink: #2c1810;
    --ink-soft: #5a4630;
    --ink-faint: #8a7560;
    --ink-ghost: #bfa890;
    --line: rgba(58, 36, 16, 0.10);
    --glass: rgba(255, 253, 247, 0.55);
    --glass-2: rgba(255, 253, 247, 0.78);
    --glass-line: rgba(255, 255, 255, 0.7);
    --radius: 18px;
    --font-serif: 'Cormorant Garamond', Georgia, serif;
    --font-ui: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    color-scheme: light;
}

html, body, gradio-app {
    min-height: 100vh;
    background:
        radial-gradient(1100px 600px at 50% -10%, rgba(245, 158, 11, 0.22), transparent 60%),
        linear-gradient(180deg, #fbf2dc 0%, #f6e3bf 45%, #e8cf9d 100%) fixed !important;
    color: var(--ink) !important;
    font-family: var(--font-ui) !important;
}
.gradio-container {
    background: transparent !important;
    max-width: 1040px !important;
    margin: 0 auto !important;
    padding-top: 28px !important;
}
.gradio-container .main,
.gradio-container .wrap,
.gradio-container .app { background: transparent !important; }

/* ---- Hero (eyebrow + serif headline + lede) ---- */
.hero {
    text-align: center;
    background: transparent !important;
    padding: 14px 0 22px 0 !important;
}
.hero .eyebrow {
    display: inline-block;
    font-size: 12px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--accent-2) !important;
    font-weight: 700;
    margin-bottom: 14px;
}
.hero h1 {
    font-family: var(--font-serif) !important;
    font-weight: 400 !important;
    font-size: 3rem !important;
    line-height: 1.12 !important;
    letter-spacing: -0.5px !important;
    color: var(--ink) !important;
    max-width: 760px;
    margin: 0 auto 14px auto !important;
}
.hero h1 em, .hero h1 i { color: var(--accent-2) !important; font-style: italic; }
.hero p {
    font-size: 17px !important;
    line-height: 1.55 !important;
    color: var(--ink-soft) !important;
    max-width: 600px;
    margin: 0 auto !important;
}

/* ---- Surface card (warm glass) ---- */
.surface-card {
    background: var(--glass) !important;
    backdrop-filter: blur(14px) saturate(120%) !important;
    -webkit-backdrop-filter: blur(14px) saturate(120%) !important;
    border: 1px solid var(--glass-line) !important;
    border-radius: var(--radius) !important;
    box-shadow:
        0 1px 0 rgba(255, 255, 255, 0.6) inset,
        0 18px 50px rgba(58, 36, 16, 0.12) !important;
    padding: 22px !important;
}
.surface-card,
.surface-card label,
.surface-card span,
.surface-card p { color: var(--ink) !important; }
.surface-card label {
    font-size: 11px !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    color: var(--ink-faint) !important;
    font-weight: 700 !important;
}

/* ---- Inputs ---- */
.surface-card textarea,
.surface-card input,
textarea, input[type="text"] {
    background: var(--glass-2) !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    color: var(--ink) !important;
    font-family: var(--font-ui) !important;
    font-size: 16px !important;
}
textarea::placeholder, input::placeholder {
    color: var(--ink-ghost) !important;
    font-weight: 500 !important;
}
textarea:focus, input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.18) !important;
    outline: none !important;
}

/* ---- Primary button (warm gradient) ---- */
button.primary,
.surface-card button.primary {
    background: linear-gradient(150deg, var(--accent), var(--accent-2)) !important;
    border: none !important;
    border-radius: 14px !important;
    font-family: var(--font-ui) !important;
    font-weight: 800 !important;
    font-size: 15px !important;
    color: var(--accent-ink) !important;
    padding: 13px 24px !important;
    box-shadow: 0 10px 28px var(--glow) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
button.primary:hover,
.surface-card button.primary:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 14px 32px var(--glow) !important;
}

/* ---- Secondary buttons ---- */
.surface-card button:not(.primary) {
    background: var(--glass-2) !important;
    border: 1px solid var(--line) !important;
    color: var(--ink-soft) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    transition: border-color 0.15s ease, color 0.15s ease !important;
}
.surface-card button:not(.primary):hover {
    border-color: var(--accent) !important;
    color: var(--ink) !important;
}

/* ---- Chat area ---- */
.chat-area {
    background: transparent !important;
    border: none !important;
}
.chat-area .message.user,
.chat-area .message-bubble-border.user {
    background: linear-gradient(150deg, var(--accent), var(--accent-2)) !important;
    color: var(--accent-ink) !important;
    border: none !important;
    border-radius: 16px 16px 4px 16px !important;
    font-weight: 600 !important;
    box-shadow: 0 8px 22px var(--glow) !important;
}
.chat-area .message.user p,
.chat-area .message.user strong { color: var(--accent-ink) !important; }
.chat-area .message.bot,
.chat-area .message-bubble-border.bot {
    background: var(--glass-2) !important;
    color: var(--ink) !important;
    border: 1px solid var(--glass-line) !important;
    border-radius: 16px 16px 16px 4px !important;
    box-shadow: 0 6px 18px rgba(58, 36, 16, 0.08) !important;
}
.chat-area .message.bot p,
.chat-area .message.bot li,
.chat-area .message.bot strong,
.chat-area .message.bot h1,
.chat-area .message.bot h2,
.chat-area .message.bot h3 { color: var(--ink) !important; }
.chat-area .message.bot em { color: var(--accent-2) !important; }
.chat-area .message.bot a { color: var(--accent-2) !important; font-weight: 600; }
.chat-area .message.bot code {
    background: rgba(58, 36, 16, 0.06) !important;
    color: var(--ink) !important;
    border: 1px solid var(--line) !important;
    border-radius: 6px !important;
    padding: 1px 6px !important;
    font-size: 0.9em;
}
.chat-input-row { margin-top: 14px !important; }

/* ---- Examples chips (glass pills) ---- */
.surface-card .examples,
.surface-card [class*="examples"] button,
.surface-card .gradio-examples button {
    background: var(--glass) !important;
    border: 1px solid var(--glass-line) !important;
    color: var(--ink-soft) !important;
    border-radius: 999px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    padding: 8px 15px !important;
    transition: border-color 0.15s ease, color 0.15s ease, transform 0.15s ease !important;
}
.surface-card .examples button:hover,
.surface-card [class*="examples"] button:hover {
    border-color: var(--accent) !important;
    color: var(--ink) !important;
    transform: translateY(-1px);
}
.surface-card [class*="examples"] > label,
.surface-card .gradio-examples > label {
    color: var(--ink-faint) !important;
    font-size: 11px !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
}

/* ---- Scrollbar ---- */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(58, 36, 16, 0.18); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-2); }

/* ---- Footer ---- */
.footer-note {
    text-align: center;
    background: transparent !important;
    margin-top: 22px;
    padding-top: 14px;
    border-top: 1px solid var(--line);
}
.footer-note p,
.footer-note strong { color: var(--ink-faint) !important; font-weight: 600 !important; }
"""


HOSGELDIN_MESAJI = (
    "Merhaba! 👋 Ben **SkyWise** — hava durumuna göre aktivite öneren asistanın.\n\n"
    "Hangi şehirde olduğunu ve nasıl bir aktivite aradığını söyle, sana özel "
    "öneriler hazırlayayım. Sonradan istediğin gibi sorularla detaylandırabilirsin "
    "— örneğin _\"o ilk kafe hakkında biraz daha bilgi?\"_ veya _\"müze sevmiyorum, "
    "başka ne yapabilirim?\"_ gibi."
)


def _initial_history() -> list[dict]:
    return [{"role": "assistant", "content": HOSGELDIN_MESAJI}]


def respond(user_message: str, history: list[dict]):
    user_message = (user_message or "").strip()
    if not user_message:
        yield history, ""
        return

    history = list(history or [])
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": ""})

    convo_for_agent = history[:-1]

    try:
        for partial in chat_skywise(convo_for_agent):
            history[-1]["content"] = partial
            yield history, ""
    except ValueError as e:
        history[-1]["content"] = f"> ⚠️ {e}"
        yield history, ""
    except Exception as e:
        history[-1]["content"] = f"> ⚠️ Bir hata oluştu: {e}"
        yield history, ""


with gr.Blocks(
    title="SkyWise — Hava Durumu Aktivite Asistanı",
    theme=gr.themes.Base(
        primary_hue="amber",
        neutral_hue="stone",
        font=gr.themes.GoogleFont("Inter"),
    ).set(
        body_background_fill="#fbf2dc",
        body_text_color="#2c1810",
        background_fill_primary="rgba(255,253,247,0.78)",
        background_fill_secondary="rgba(255,253,247,0.55)",
        border_color_primary="rgba(58,36,16,0.10)",
        block_background_fill="rgba(255,253,247,0.55)",
        block_border_color="rgba(255,255,255,0.7)",
        input_background_fill="rgba(255,253,247,0.78)",
        input_border_color="rgba(58,36,16,0.10)",
    ),
    css=CUSTOM_CSS,
) as demo:
    gr.HTML(
        """
        <div class="hero">
            <div class="eyebrow">Hava Durumu Aktivite Asistanı</div>
            <h1>Bugün hava <em>ne yapmaya</em> uygun?</h1>
            <p>Şehrini yaz, dilersen ilgi alanlarını ekle — bugünün havasına en uygun aktiviteleri anında öner.</p>
        </div>
        """,
    )

    with gr.Column(elem_classes="surface-card"):
        chatbot = gr.Chatbot(
            value=_initial_history(),
            type="messages",
            height=520,
            elem_classes="chat-area",
            show_copy_button=True,
            avatar_images=(None, None),
            label="SkyWise Sohbet",
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

        gr.Examples(
            examples=[
                "Bugün İstanbul'da hava nasıl, ne yapabilirim?",
                "Ankara'da iç mekân aktiviteleri öner",
                "Antalya'da plaj ve yüzme için bugün uygun mu?",
                "Eskişehir'de bu hafta sonu için müze önerin var mı?",
            ],
            inputs=textbox,
            label="Örnek sorular",
        )

    gr.Markdown(
        """
        ---
        **SEN4018 Dönem Projesi** | Samet Soydan & Emre Sarkuş | Bahçeşehir Üniversitesi
        """,
        elem_classes="footer-note",
    )

    textbox.submit(respond, [textbox, chatbot], [chatbot, textbox], api_name=False)
    send_btn.click(respond, [textbox, chatbot], [chatbot, textbox], api_name=False)
    clear_btn.click(lambda: _initial_history(), None, chatbot, api_name=False)


if __name__ == "__main__":
    demo.launch(show_error=True, show_api=False, server_name="127.0.0.1")
