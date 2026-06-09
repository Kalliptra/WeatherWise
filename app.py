import gradio as gr
from agent import run_skywise


def skywise_interface(city: str, preferences: str):
    if not city.strip():
        return "Lütfen bir şehir adı girin.", "", "", ""

    try:
        result = run_skywise(city.strip(), preferences.strip() or "genel aktiviteler")
    except ValueError as e:
        return str(e), "", "", ""
    except Exception as e:
        return f"Bir hata oluştu: {str(e)}", "", "", ""

    weather_info = (
        f"📍 {result['city']}, {result['country']}\n"
        f"🌡️ {result['temperature']}°C\n"
        f"☁️ {result['condition'].capitalize()}\n"
        f"💧 Nem: {result['humidity']}%\n"
        f"💨 Rüzgar: {result['wind_speed']} km/h"
    )

    recommendation = result["recommendation"]

    supervisor_status = "✅ Onaylandı" if result["supervisor_approved"] else "⚠️ Düzeltildi"
    supervisor_info = (
        f"{supervisor_status}\n"
        f"Puan: {result['supervisor_score']}/10\n"
        f"Yorum: {result['supervisor_comment']}"
    )

    return weather_info, recommendation, supervisor_info


with gr.Blocks(
    title="SkyWise — Hava Durumu Aktivite Asistanı",
    theme=gr.themes.Soft(),
) as demo:
    gr.Markdown(
        """
        # ☁️ SkyWise
        ### Hava Durumuna Göre Aktivite Öneri Asistanı
        Gerçek zamanlı hava durumu verisini analiz ederek sana en uygun aktiviteleri önerir.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
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
            weather_output = gr.Textbox(
                label="Hava Durumu",
                lines=6,
                interactive=False,
            )
            recommendation_output = gr.Textbox(
                label="Aktivite Önerileri",
                lines=10,
                interactive=False,
            )
            supervisor_output = gr.Textbox(
                label="Kalite Değerlendirmesi (Supervisor Agent)",
                lines=4,
                interactive=False,
            )

    submit_btn.click(
        fn=skywise_interface,
        inputs=[city_input, preferences_input],
        outputs=[weather_output, recommendation_output, supervisor_output],
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
        """
    )


if __name__ == "__main__":
    demo.launch(show_error=True)
