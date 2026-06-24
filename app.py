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
import threading  # noqa: E402

import gradio as gr  # noqa: E402

from chat import (  # noqa: E402
    chat_skywise,
    clear_last_location,
    get_last_locations,
    generate_next_suggestion,
    generate_location_suggestions,
    generate_session_title,
    get_current_language,
    set_user_location,
)
from tools.memory import get_activity_preferences, update_activity_preferences  # noqa: E402
from ui_theme import (  # noqa: E402
    CUSTOM_CSS,
    render_locations_map,
    render_map_panel,
    render_panel_placeholder,
    render_weather_panel,
    weather_to_theme,
)
from tools.forecast import clear_last_forecast  # noqa: E402
from tools.weather import (  # noqa: E402
    clear_last_weather,
    get_last_weather,
    get_weather,
    get_weather_by_coords,
)
from tools.venue import clear_last_venues, geocode_city, get_last_venues  # noqa: E402
from tools.sessions import (  # noqa: E402
    delete_session,
    list_sessions,
    load_session,
    new_session_id,
    rename_session,
    save_session,
)

DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Istanbul")
IS_HF_SPACE = bool(os.getenv("SPACE_ID"))

# Aktif bir respond_from_history generator'unu işaretçi flag'i ile durdurur.
# set() → generator bir sonraki yield öncesi temiz şekilde durur (Error göstermez).
_abort = threading.Event()

# Anonim kullanıcıyı tarayıcı tarafında kalıcı bir kimlikle tanı (localStorage).
ANON_ID_JS = """
() => {
    let id = localStorage.getItem('skywise_anon_id');
    if (!id) {
        id = (window.crypto && crypto.randomUUID)
            ? crypto.randomUUID()
            : String(Date.now()) + Math.random().toString(16).slice(2);
        localStorage.setItem('skywise_anon_id', id);
    }
    return id;
}
"""

ORNEK_SORULAR = [
    "🏃 Spor & Fitness",
    "🌿 Doğa & Yürüyüş",
    "🎨 Kültür & Müze",
    "🍽️ Yemek & Kafe",
]

# Kullanıcının kategori butonlarından seçtiği metni aktivite tercihine eşleyen sözlük.
# Tercih kaydı için kullanılır — key: buton etiketi, value: kayıt edilecek kategoriler.
CATEGORY_PREFS: dict[str, list[str]] = {
    "🏃 Spor & Fitness": ["spor", "fitness"],
    "🌿 Doğa & Yürüyüş": ["doğa", "yürüyüş"],
    "🎨 Kültür & Müze": ["kültür", "müze"],
    "🍽️ Yemek & Kafe": ["yemek", "kafe"],
    "🏃 Sports & Fitness": ["sports", "fitness"],
    "🌿 Nature & Hiking": ["nature", "hiking"],
    "🎨 Culture & Museum": ["culture", "museum"],
    "🍽️ Food & Café": ["food", "café"],
}

KARSILAMA_HTML = """
<div class="greeting">
    <div class="wave">🌤️</div>
    <h2>Merhaba! Ben SkyWise</h2>
    <p>Bulunduğun şehrin hava durumuna göre sana en uygun aktiviteleri öneririm.
    Aşağıdan kategori seç ya da istediğini yaz — hemen öneriler hazırlayayım.</p>
</div>
"""

ONBOARDING_HTML = """
<div class="greeting">
    <div class="wave">🌤️</div>
    <h2>Merhaba! Ben SkyWise</h2>
    <div class="onboarding-question">
        <p><strong>Hangi tür aktiviteleri seversin?</strong></p>
        <p>Aşağıdan bir kategori seç — bulunduğun yerin havasına göre hemen öneriler hazırlayayım.</p>
    </div>
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
        if (!sugBox) return;
        var val = sugBox.value || sugBox.textContent || '';
        if (!val.trim()) return;
        var chatInput = document.querySelector('.chat-input-row textarea');
        if (!chatInput) return;
        e.preventDefault();
        // Svelte/React controlled input için native setter kullan
        var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
        nativeSetter.call(chatInput, val);
        chatInput.dispatchEvent(new Event('input', { bubbles: true }));
        chatInput.focus();
    });

    // Chat alanı içindeki scroll edilebilir container'ı bul.
    // scrollIntoView KULLANMA — tüm sayfayı kaydırır ve "kayma" efekti yaratır.
    function findScrollTarget() {
        var chatArea = document.querySelector('.chat-area');
        if (!chatArea) return null;

        function walk(node) {
            if (!node || !node.children) return null;
            var cs = window.getComputedStyle(node);
            var oy = cs.overflowY;
            if ((oy === 'scroll' || oy === 'auto') && node.scrollHeight > node.clientHeight + 4) {
                return node;
            }
            for (var i = 0; i < node.children.length; i++) {
                var r = walk(node.children[i]);
                if (r) return r;
            }
            return null;
        }

        return walk(chatArea) || chatArea;
    }

    function scrollChatToBottom() {
        var target = findScrollTarget();
        if (target) target.scrollTop = target.scrollHeight;
    }

    // requestAnimationFrame ile bir frame sonraya ertele → layout hesaplandıktan sonra çalışır.
    // setTimeout yerine rAF kullanmak, scroll'un içerik yerleştikten hemen sonra tetiklenmesini sağlar.
    var _rafPending = false;
    var chatObserver = new MutationObserver(function() {
        if (!_rafPending) {
            _rafPending = true;
            requestAnimationFrame(function() {
                scrollChatToBottom();
                _rafPending = false;
            });
        }
    });

    function attachChatObserver() {
        var chatEl = document.querySelector('.chat-area');
        if (chatEl) {
            chatObserver.observe(chatEl, { childList: true, subtree: true, characterData: true });
        } else {
            setTimeout(attachChatObserver, 300);
        }
    }
    attachChatObserver();
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


def _persist_turn(history, session_id, sessions, user_message, anon_id):
    """Turun sonunda session'ı (mesajlar + panel snapshot) kaydeder ve güncel
    session listesini döndürür. Başlık ilk turda LLM ile üretilir, sonra korunur."""
    weather = get_last_weather()
    venues = get_last_venues()
    locs = get_last_locations()
    focus_city = (weather or {}).get("city") if weather else (locs[0] if locs else "")
    panel = {
        "weather": weather,
        "venues": venues,
        "locations": locs,
        "focus_city": focus_city,
    }
    existing = next((s for s in (sessions or []) if s.get("id") == session_id), None)
    if existing and existing.get("title"):
        title = existing["title"]
    else:
        title = generate_session_title(user_message, get_current_language())
    try:
        save_session(anon_id, session_id, messages=history, panel=panel, title=title)
    except Exception:
        pass
    try:
        return list_sessions(anon_id)
    except Exception:
        return sessions


def respond_from_history(history, queued, session_id, sessions, anon_id):
    """Yields: (chatbot, textbox, empty_state, weather_panel, theme_state, map_panel,
    show_loc_btn, location_state, suggestion_box, queued_state, queued_display,
    session_id_state, sessions_state)."""
    _abort.clear()
    if not queued:
        return

    user_message = queued[0]
    remaining = list(queued[1:])
    qd = render_queued_display(remaining)

    # Kullanıcı bir kategori butonu seçtiyse tercihi Redis'e kaydet
    if anon_id and user_message in CATEGORY_PREFS:
        try:
            update_activity_preferences(anon_id, CATEGORY_PREFS[user_message])
        except Exception:
            pass

    if not session_id:
        session_id = new_session_id()

    history = list(history or [])
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": TYPING_INDICATOR})

    yield gr.update(value=history, visible=True), gr.update(), gr.update(visible=False), gr.update(), gr.update(), gr.update(), gr.update(visible=False), [], gr.update(), remaining, qd, session_id, sessions

    convo_for_agent = history[:-1]
    clear_last_weather()
    clear_last_venues()
    clear_last_location()
    clear_last_forecast()
    panel_sent = False
    map_sent = False

    try:
        for partial in chat_skywise(convo_for_agent, anon_id=anon_id or None):
            if _abort.is_set():
                return
            history[-1]["content"] = partial if partial else TYPING_INDICATOR
            weather = get_last_weather()
            venues = get_last_venues()

            if weather is not None and not panel_sent:
                panel_sent = True
                yield history, gr.update(), gr.update(), render_weather_panel(weather), weather_to_theme(weather), gr.update(), gr.update(), gr.update(), gr.update(), remaining, qd, session_id, sessions
            elif venues and not map_sent:
                map_sent = True
                map_html = render_map_panel(venues)
                yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=map_html, visible=bool(map_html)), gr.update(visible=False), gr.update(), gr.update(), remaining, qd, session_id, sessions
            else:
                yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), remaining, qd, session_id, sessions

        if not map_sent:
            venues = get_last_venues()
            if venues:
                map_html = render_map_panel(venues)
                if map_html:
                    yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=map_html, visible=True), gr.update(visible=False), gr.update(), gr.update(), remaining, qd, session_id, sessions
                    map_sent = True

        if not map_sent:
            locs = get_last_locations()
            if locs:
                btn_label = (
                    f"📍 {locs[0]} konumunu haritada göster"
                    if len(locs) == 1
                    else f"📍 Bunları haritada göster ({len(locs)} yer)"
                )
                yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=btn_label, visible=True), locs, gr.update(), remaining, qd, session_id, sessions

        new_sessions = _persist_turn(history, session_id, sessions, user_message, anon_id)

        hint, suggestion = generate_next_suggestion(history)
        default_placeholder = "Etkinlik sor... (örn: \"Bugün koşu için hava uygun mu?\")"
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
            session_id,
            new_sessions,
        )

    except ValueError as e:
        history[-1]["content"] = f"> ⚠️ {e}"
        new_sessions = _persist_turn(history, session_id, sessions, user_message, anon_id)
        yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), remaining, qd, session_id, new_sessions
    except Exception as e:
        history[-1]["content"] = f"> ⚠️ Bir hata oluştu: {e}"
        new_sessions = _persist_turn(history, session_id, sessions, user_message, anon_id)
        yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), remaining, qd, session_id, new_sessions


def clear_chat():
    """'Yeni Sohbet' — sohbeti ve panelleri temizler, aktif session id'yi sıfırlar."""
    _abort.set()
    clear_last_venues()
    clear_last_location()
    clear_last_forecast()
    return (
        gr.update(value=[], visible=False),
        gr.update(visible=True),
        "",
        gr.update(value="", visible=False),
        gr.update(visible=False),
        "",
        [],
        "",
        "",
        gr.update(visible=False),
    )


# ---- Session handler'ları ----

def load_sessions_on_start(anon_id):
    try:
        return list_sessions(anon_id)
    except Exception:
        return []


def on_select_session(sid, anon_id):
    """Bir session'a tıklanınca sohbeti + hava/harita panelini geri yükler."""
    try:
        data = load_session(anon_id, sid)
    except Exception:
        data = None
    if not data:
        return (gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), sid)

    messages = data.get("messages") or []
    weather = data.get("weather")
    venues = data.get("venues") or []
    locs = data.get("locations") or []

    weather_html = render_weather_panel(weather) if weather else render_panel_placeholder("Bu sohbet için kayıtlı hava durumu yok.")
    theme = weather_to_theme(weather) if weather else "clear-day"

    if venues:
        map_html = render_map_panel(venues)
        map_upd = gr.update(value=map_html, visible=bool(map_html))
        loc_btn_upd = gr.update(visible=False)
    else:
        map_upd = gr.update(value="", visible=False)
        if locs:
            btn_label = (
                f"📍 {locs[0]} konumunu haritada göster"
                if len(locs) == 1
                else f"📍 Bunları haritada göster ({len(locs)} yer)"
            )
            loc_btn_upd = gr.update(value=btn_label, visible=True)
        else:
            loc_btn_upd = gr.update(visible=False)

    return (
        gr.update(value=messages, visible=True),
        gr.update(visible=False),
        weather_html,
        theme,
        map_upd,
        loc_btn_upd,
        locs,
        sid,
    )


def on_delete_session(sid, active_id, anon_id):
    """Session'ı siler; silinen aktif session ise sohbeti temizler."""
    try:
        delete_session(anon_id, sid)
        new_list = list_sessions(anon_id)
    except Exception:
        new_list = []
    if active_id == sid:
        clear_last_forecast()
        return (
            new_list,
            gr.update(value=[], visible=False),
            gr.update(visible=True),
            render_panel_placeholder("Hava durumu yükleniyor..."),
            gr.update(value="", visible=False),
            gr.update(visible=False),
            "",
            "",
        )
    return (new_list, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update())


def on_rename_session(sid, new_title, anon_id):
    try:
        rename_session(anon_id, sid, new_title)
        new_list = list_sessions(anon_id)
    except Exception:
        new_list = []
    return new_list, gr.update(visible=False)


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


def check_and_show_onboarding(anon_id: str):
    """Sayfa yüklenince çalışır. Tercihi olmayan (yeni) anonim kullanıcıya onboarding
    ekranı gösterir. Karşılama HTML'i günceller; butonlar kategori seçeneklerine dönüşür.
    Tercihi kayıtlı kullanıcılar için normal görünüm korunur.
    Dönüş: (greeting_html, sug1, sug2, sug3, sug4)
    """
    noop = (gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
    if not anon_id:
        return noop
    prefs = get_activity_preferences(anon_id)
    if prefs:
        return noop
    cats = ORNEK_SORULAR
    return (
        gr.update(value=ONBOARDING_HTML),
        gr.update(value=cats[0]),
        gr.update(value=cats[1]),
        gr.update(value=cats[2]),
        gr.update(value=cats[3]),
    )


def trigger_preference_update():
    """'Tercihlerimi Güncelle' — sohbeti temizler ve onboarding ekranını gösterir.
    Dönüş: NEW_CHAT_OUTPUTS + ONBOARDING_OUTPUTS (15 değer)
    """
    _abort.set()
    clear_last_venues()
    clear_last_location()
    clear_last_forecast()
    cats = ORNEK_SORULAR
    return (
        gr.update(value=[], visible=False),   # chatbot
        gr.update(visible=True),               # empty_state
        "",                                    # textbox
        gr.update(value="", visible=False),    # map_panel
        gr.update(visible=False),              # show_loc_btn
        "",                                    # location_state
        [],                                    # queued_state
        "",                                    # queued_display
        "",                                    # session_id_state
        gr.update(visible=False),              # forecast_plot
        gr.update(value=ONBOARDING_HTML),      # greeting_html
        gr.update(value=cats[0]),              # sug1
        gr.update(value=cats[1]),              # sug2
        gr.update(value=cats[2]),              # sug3
        gr.update(value=cats[3]),              # sug4
    )


def load_default_city():
    try:
        weather = get_weather(DEFAULT_CITY)
        return render_weather_panel(weather), weather_to_theme(weather)
    except Exception:
        return render_panel_placeholder("Hava durumu alınamadı."), "clear-day"


def update_forecast_chart():
    """Bu turda çekilen saatlik tahminden Plotly grafiği üretir (yoksa gizler)."""
    try:
        fig = render_forecast_chart(get_last_forecast())
    except Exception:
        fig = None
    if fig is None:
        return gr.update(visible=False)
    return gr.update(value=fig, visible=True)


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
    with gr.Row(elem_classes="topbar-row"):
        toggle_sidebar_btn = gr.Button("◀", elem_classes="sidebar-toggle", scale=0)
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
    # Anonim kimlik ve session state'leri
    anon_id_box = gr.Textbox(visible=False)  # localStorage anon-id (JS ile dolar)
    session_id_state = gr.State("")      # aktif session id; "" = henüz kaydedilmemiş yeni sohbet
    sessions_state = gr.State([])        # sidebar için session metadata listesi
    sidebar_visible = gr.State(True)

    with gr.Row(elem_classes="main-row"):
        with gr.Column(scale=1, min_width=200, elem_classes="session-sidebar", visible=True) as sidebar_col:
            new_chat_btn = gr.Button("➕ Yeni Sohbet", elem_classes="new-chat-btn")
            pref_update_btn = gr.Button("⚙️ Tercihlerimi Güncelle", elem_classes="new-chat-btn", size="sm")

            @gr.render(inputs=[sessions_state, session_id_state])
            def render_sessions(sessions, active_id):
                if not sessions:
                    gr.HTML("<div class='session-empty'>Henüz sohbet yok</div>")
                    return
                for s in sessions:
                    sid = s.get("id")
                    title = s.get("title") or "Sohbet"
                    row_cls = "session-row" + (" active" if sid == active_id else "")
                    with gr.Row(elem_classes=row_cls):
                        sel_btn = gr.Button(title, elem_classes="session-select", scale=8)
                        rename_btn = gr.Button("✏️", elem_classes="session-icon", scale=1, min_width=36)
                        del_btn = gr.Button("🗑", elem_classes="session-icon", scale=1, min_width=36)
                    with gr.Row(visible=False, elem_classes="session-rename-row") as rename_row:
                        rename_box = gr.Textbox(value=title, show_label=False, container=False, scale=8)
                        rename_save = gr.Button("✓", elem_classes="session-icon", scale=1, min_width=36)

                    sel_btn.click(
                        lambda a, _s=sid: on_select_session(_s, a),
                        [anon_id_box],
                        [chatbot, empty_state, weather_panel, theme_state, map_panel, show_loc_btn, location_state, session_id_state],
                        api_name=False,
                    )
                    rename_btn.click(lambda: gr.update(visible=True), None, rename_row, api_name=False)
                    rename_save.click(
                        lambda t, a, _s=sid: on_rename_session(_s, t, a),
                        [rename_box, anon_id_box],
                        [sessions_state, rename_row],
                        api_name=False,
                    )
                    del_btn.click(
                        lambda act, a, _s=sid: on_delete_session(_s, act, a),
                        [session_id_state, anon_id_box],
                        [sessions_state, chatbot, empty_state, weather_panel, map_panel, show_loc_btn, location_state, session_id_state],
                        api_name=False,
                    )

        with gr.Column(scale=2, min_width=260, elem_classes="panel-col"):
            weather_panel = gr.HTML(render_panel_placeholder("Hava durumu yükleniyor..."))
            forecast_plot = gr.Plot(visible=False, elem_classes="forecast-plot", show_label=False)
            map_panel = gr.HTML(value="", visible=False)
            show_loc_btn = gr.Button("📍 Konumu Haritada Göster", visible=False, elem_classes="loc-btn")

        with gr.Column(scale=5, elem_classes="chat-surface"):
            with gr.Column(visible=True, elem_classes="empty-state") as empty_state:
                greeting_html = gr.HTML(KARSILAMA_HTML)
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
                    placeholder="Etkinlik sor... (örn: \"Bugün koşu için hava uygun mu?\")",
                    scale=9,
                    container=False,
                    lines=1,
                    max_lines=1,
                    show_label=False,
                )
                send_btn = gr.Button("Gönder ↗", variant="primary", scale=1)

    gr.Markdown(
        """
        ---
        **SEN4018 Dönem Projesi** | Samet Soydan & Emre Sarkuş | Bahçeşehir Üniversitesi
        """,
        elem_classes="footer-note",
    )

    theme_state = gr.Textbox(visible=False, elem_id="theme-state")
    geo_coords = gr.Textbox(visible=False, elem_id="geo-coords")
    suggestion_box = gr.Textbox(
        elem_id="skywise-suggestion",
        elem_classes="skywise-offscreen",
        interactive=True,
        container=False,
        show_label=False,
    )

    RESPOND_OUTPUTS = [chatbot, textbox, empty_state, weather_panel, theme_state, map_panel, show_loc_btn, location_state, suggestion_box, queued_state, queued_display, session_id_state, sessions_state]
    RESPOND_INPUTS = [chatbot, queued_state, session_id_state, sessions_state, anon_id_box]
    PRE_OUTPUTS = [textbox, queued_state, queued_display]
    NEW_CHAT_OUTPUTS = [chatbot, empty_state, textbox, map_panel, show_loc_btn, location_state, queued_state, queued_display, session_id_state, forecast_plot]

    for trigger in (textbox.submit, send_btn.click):
        (trigger(pre_submit, [textbox, queued_state], PRE_OUTPUTS, api_name=False)
         .then(respond_from_history, RESPOND_INPUTS, RESPOND_OUTPUTS, concurrency_limit=1, api_name=False)
         .then(update_forecast_chart, None, forecast_plot, api_name=False))
    for sug in (sug1, sug2, sug3, sug4):
        (sug.click(pre_submit, [sug, queued_state], PRE_OUTPUTS, api_name=False)
         .then(respond_from_history, RESPOND_INPUTS, RESPOND_OUTPUTS, concurrency_limit=1, api_name=False)
         .then(update_forecast_chart, None, forecast_plot, api_name=False))
    new_chat_btn.click(clear_chat, None, NEW_CHAT_OUTPUTS, api_name=False)
    show_loc_btn.click(show_location_on_map, location_state, [map_panel, show_loc_btn], api_name=False)

    toggle_sidebar_btn.click(
        # Açıkken "◀" (kapat), kapalıyken "☰" (aç) ikonu göster.
        lambda vis: (gr.update(visible=not vis), not vis, gr.update(value="☰" if vis else "◀")),
        sidebar_visible, [sidebar_col, sidebar_visible, toggle_sidebar_btn], api_name=False,
    )

    theme_state.change(None, theme_state, None, js=THEME_JS, api_name=False)

    demo.load(load_default_city, None, [weather_panel, theme_state], api_name=False)
    demo.load(None, None, geo_coords, js=GEO_JS, api_name=False)
    geo_coords.change(apply_geolocation, geo_coords, [weather_panel, theme_state, sug1, sug2, sug3, sug4], api_name=False)
    ONBOARDING_OUTPUTS = [greeting_html, sug1, sug2, sug3, sug4]

    # Anon-id (JS) → session listesi → onboarding kontrolü sırasıyla yüklenir.
    (demo.load(None, None, anon_id_box, js=ANON_ID_JS, api_name=False)
        .then(load_sessions_on_start, anon_id_box, sessions_state, api_name=False)
        .then(check_and_show_onboarding, anon_id_box, ONBOARDING_OUTPUTS, api_name=False))

    pref_update_btn.click(
        trigger_preference_update,
        None,
        NEW_CHAT_OUTPUTS + ONBOARDING_OUTPUTS,
        api_name=False,
    )


if __name__ == "__main__":
    demo.queue(max_size=20)
    # HF Spaces'in reverse-proxy'si konteynere ulaşabilsin diye 0.0.0.0'a bağlan;
    # yerelde 127.0.0.1 kalsın.
    server_name = "0.0.0.0" if IS_HF_SPACE else "127.0.0.1"
    demo.launch(show_error=True, show_api=False, server_name=server_name)
