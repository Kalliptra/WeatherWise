import gradio as gr
from agent import run_skywise


CUSTOM_CSS = """
/* ---- Sky gradient background ---- */
html, body, gradio-app {
    min-height: 100vh;
    background: linear-gradient(160deg, #a1c4fd 0%, #c2e9fb 38%, #fbc2eb 100%) fixed !important;
}
.gradio-container {
    background: transparent !important;
    max-width: 1080px !important;
    margin: 0 auto !important;
    padding-top: 8px !important;
}
/* Let the gradient show through default wrappers */
.gradio-container .main,
.gradio-container .wrap,
.gradio-container .app {
    background: transparent !important;
}

/* ---- Frosted glass cards ---- */
.glass-card {
    background: rgba(255, 255, 255, 0.55) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255, 255, 255, 0.45) !important;
    border-radius: 20px !important;
    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.18) !important;
    padding: 22px !important;
}
.glass-card,
.glass-card label,
.glass-card span,
.glass-card p,
.glass-card h1,
.glass-card h2,
.glass-card h3 {
    color: #1e293b !important;
}

/* Make inputs inside cards feel light */
.glass-card textarea,
.glass-card input {
    background: rgba(255, 255, 255, 0.7) !important;
    border: 1px solid rgba(148, 163, 184, 0.35) !important;
    border-radius: 12px !important;
    color: #0f172a !important;
}

/* ---- Output cards ---- */
.output-card {
    margin-bottom: 16px !important;
    min-height: 70px;
}
.output-card h3 {
    margin-top: 0 !important;
    margin-bottom: 8px !important;
}

/* ---- Hero header ---- */
.hero {
    text-align: center;
    background: transparent !important;
    padding: 14px 0 4px 0 !important;
}
.hero h1 {
    font-size: 2.6rem !important;
    font-weight: 800 !important;
    margin-bottom: 2px !important;
    color: #0f3d6e !important;
    text-shadow: 0 2px 12px rgba(255, 255, 255, 0.5);
}
.hero h3 {
    font-weight: 600 !important;
    color: #1d4e89 !important;
    margin-top: 0 !important;
}
.hero p {
    color: #28527a !important;
    max-width: 640px;
    margin: 6px auto 0 auto !important;
}

/* ---- Primary button ---- */
button.primary,
.glass-card button.primary {
    background: linear-gradient(135deg, #38bdf8, #2563eb) !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
}
button.primary:hover,
.glass-card button.primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 22px rgba(37, 99, 235, 0.45) !important;
}

/* ---- Footer ---- */
.footer-note {
    text-align: center;
    background: transparent !important;
}
.footer-note p,
.footer-note strong {
    color: #28527a !important;
}
"""


WEATHER_PLACEHOLDER = (
    "### 🌤️ Hava Durumu\n"
    "Bir şehir gir ve **Öneri Al** butonuna bas — güncel hava durumu burada görünecek."
)
RECOMMENDATION_PLACEHOLDER = (
    "### 🎯 Aktivite Önerileri\n"
    "Sana özel aktivite önerileri burada listelenecek."
)


def skywise_interface(city: str, preferences: str):
    if not city.strip():
        return "> ⚠️ Lütfen bir şehir adı girin.", ""

    try:
        result = run_skywise(city.strip(), preferences.strip() or "genel aktiviteler")
    except ValueError as e:
        return f"> ⚠️ {str(e)}", ""
    except Exception as e:
        return f"> ⚠️ Bir hata oluştu: {str(e)}", ""

    weather_info = (
        f"### 📍 {result['city']}, {result['country']}\n"
        f"**🌡️ {result['temperature']}°C**  ·  ☁️ {result['condition'].capitalize()}\n\n"
        f"💧 Nem %{result['humidity']}   💨 Rüzgar {result['wind_speed']} km/h"
    )

    recommendation = f"### 🎯 Aktivite Önerileri\n{result['recommendation']}"

    return weather_info, recommendation


with gr.Blocks(
    title="SkyWise — Hava Durumu Aktivite Asistanı",
    theme=gr.themes.Soft(primary_hue="sky", neutral_hue="slate"),
    css=CUSTOM_CSS,
) as demo:
    gr.Markdown(
        """
        # ☁️ SkyWise
        ### Hava Durumuna Göre Aktivite Öneri Asistanı
        Gerçek zamanlı hava durumu verisini analiz ederek sana en uygun aktiviteleri önerir.
        """,
        elem_classes="hero",
    )

    with gr.Row():
        with gr.Column(scale=1, elem_classes="glass-card"):
            city_input = gr.Textbox(
                label="Şehir",
                placeholder="İstanbul, Ankara, İzmir...",
                max_lines=1,
            )
            preferences_input = gr.Textbox(
                label="Tercihleriniz (isteğe bağlı)",
                placeholder="Örn: doğa yürüyüşü, müze, kafe, spor...",
                max_lines=2,
            )
            submit_btn = gr.Button("Öneri Al 🚀", variant="primary")

        with gr.Column(scale=2):
            weather_output = gr.Markdown(
                value=WEATHER_PLACEHOLDER,
                elem_classes=["glass-card", "output-card"],
            )
            recommendation_output = gr.Markdown(
                value=RECOMMENDATION_PLACEHOLDER,
                elem_classes=["glass-card", "output-card"],
            )

    submit_btn.click(
        fn=skywise_interface,
        inputs=[city_input, preferences_input],
        outputs=[weather_output, recommendation_output],
    )

    gr.Examples(
        examples=[
            ["Istanbul", "doğa yürüyüşü, kafe"],
            ["Ankara", "müze, alışveriş"],
            ["Antalya", "plaj, yüzme, snorkel"],
            ["London", "indoor aktiviteler, müze"],
        ],
        inputs=[city_input, preferences_input],
    )

    gr.Markdown(
        """
        ---
        **SEN4018 Dönem Projesi** | Samet Soydan & Emre Sarkuş | Bahçeşehir Üniversitesi
        """,
        elem_classes="footer-note",
    )


if __name__ == "__main__":
    demo.launch(show_error=True)
