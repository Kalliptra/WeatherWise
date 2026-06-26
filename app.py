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
    _detect_language,
    chat_skywise,
    clear_last_location,
    clear_pending_nearby,
    did_last_turn_recommend,
    get_last_locations,
    get_pending_nearby,
    generate_next_suggestion,
    generate_location_suggestions,
    generate_session_title,
    get_current_language,
    get_travel_destination,
    get_user_location,
    set_current_language,
    set_user_location,
    week_planner_requested,
)
import i18n  # noqa: E402
from i18n import t  # noqa: E402
from tools.memory import (  # noqa: E402
    add_favorite,
    apply_feedback,
    get_activity_preferences,
    get_personalization_level,
    list_favorites,
    record_feedback,
    remove_favorite,
    reset_preferences,
    toggle_favorite_done,
    update_activity_preferences,
)
from ui_theme import (  # noqa: E402
    CUSTOM_CSS,
    render_locations_map,
    render_map_panel,
    render_panel_placeholder,
    render_panel_skeleton,
    render_personalization_badge,
    render_rain_alert,
    render_time_ribbon,
    render_travel_compare,
    render_weather_panel,
    render_week_heatmap,
    weather_to_theme,
)
from tools.forecast import clear_last_forecast, get_last_forecast  # noqa: E402
from tools.weather import (  # noqa: E402
    clear_last_weather,
    get_last_weather,
    get_weather,
    get_weather_by_coords,
)
from tools.venue import clear_last_venues, find_venues, geocode_city, get_last_venues  # noqa: E402
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

# Arayüzün ilk açılışta (JS dil tespiti gelmeden önce) kullanacağı varsayılan dil.
# Gerçek dil demo.load → LANG_JS ile tespit edilip apply_language ile uygulanır.
DEFAULT_LANG = "tr"

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

# Kullanıcının UI dil tercihi (localStorage) ya da tarayıcı dilinden ilk dil tespiti.
# Kaydedilmiş seçim öncelikli; yoksa navigator.language → tr/en (bulamazsa tr).
LANG_JS = """
() => {
    try {
        let saved = localStorage.getItem('skywise_lang');
        if (saved === 'tr' || saved === 'en') return saved;
        let nav = (navigator.language || navigator.userLanguage || '').toLowerCase();
        if (nav.startsWith('en')) return 'en';
        return 'tr';
    } catch (e) {
        return 'tr';
    }
}
"""

# Dil değiştirme butonuna basıldığında seçimi tarayıcıda kalıcı yapar.
SAVE_LANG_JS = "(lang) => { try { localStorage.setItem('skywise_lang', lang); } catch (e) {} }"

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

# Temayı body'ye uygula + havaya duyarlı ambient partikül overlay'ini (#wx-fx) doldur.
# Aynı tür için yeniden üretmez (data-kind); reduced-motion'da temizler.
THEME_JS = """
(t) => {
    const theme = t || 'clear-day';
    document.body.dataset.theme = theme;
    const fx = document.getElementById('wx-fx');
    if (!fx) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        fx.innerHTML = ''; fx.dataset.kind = 'none'; return;
    }
    let kind = 'none';
    if (theme === 'rain' || theme === 'storm') kind = 'rain';
    else if (theme === 'snow') kind = 'snow';
    else if (theme === 'night') kind = 'stars';
    if (fx.dataset.kind === kind) return;
    fx.dataset.kind = kind;
    fx.innerHTML = '';
    fx.className = kind === 'none' ? '' : 'wx-fx-' + kind;
    if (kind === 'none') return;
    const n = kind === 'rain' ? 36 : 26;
    for (let i = 0; i < n; i++) {
        const el = document.createElement('span');
        el.className = 'wx-fx-particle';
        el.style.left = (Math.random() * 100).toFixed(2) + '%';
        if (kind === 'rain') {
            const dur = 0.5 + Math.random() * 0.55;
            el.style.animationDuration = dur.toFixed(2) + 's';
            el.style.animationDelay = (-Math.random() * dur).toFixed(2) + 's';
            el.style.setProperty('--h', (14 + Math.random() * 12).toFixed(0) + 'px');
        } else if (kind === 'snow') {
            const dur = 6 + Math.random() * 6;
            el.style.animationDuration = dur.toFixed(2) + 's';
            el.style.animationDelay = (-Math.random() * dur).toFixed(2) + 's';
            const s = (3 + Math.random() * 4).toFixed(1);
            el.style.width = s + 'px'; el.style.height = s + 'px';
            el.style.setProperty('--drift', (Math.random() * 40 - 20).toFixed(0) + 'px');
        } else {
            el.style.top = (Math.random() * 55).toFixed(2) + '%';
            const dur = 2 + Math.random() * 3;
            el.style.animationDuration = dur.toFixed(2) + 's';
            el.style.animationDelay = (-Math.random() * dur).toFixed(2) + 's';
            const s = (1.5 + Math.random() * 2).toFixed(1);
            el.style.width = s + 'px'; el.style.height = s + 'px';
        }
        fx.appendChild(el);
    }
}
"""

# Yanıt beklenirken gösterilen "yazıyor..." göstergesi (dile duyarlı, i18n'den).
typing_indicator = i18n.typing_indicator
_is_typing = i18n.is_typing

# Gradio'nun kendi koyu modunu zorla (dahili bileşenler de koyuya uysun) +
# tema set edilene kadar varsayılan accent görünsün
FORCE_DARK_JS = """
() => {
    const app = document.querySelector('gradio-app');
    if (app) app.setAttribute('theme', 'dark');
    document.documentElement.classList.add('dark');
    if (!document.body.dataset.theme) document.body.dataset.theme = 'clear-day';

    document.addEventListener('keydown', function(e) {
        if (e.key !== 'Tab' || e.shiftKey) return;
        var sugBox = document.querySelector('#skywise-suggestion textarea, #skywise-suggestion input');
        if (!sugBox) return;
        var val = sugBox.value || sugBox.textContent || '';
        if (!val.trim()) return;
        // Tek satırlık Textbox Gradio'da <input> olarak render edilir (textarea değil),
        // bu yüzden ikisini de seç ve doğru prototip setter'ını kullan.
        var chatInput = document.querySelector('.chat-input-row textarea, .chat-input-row input');
        if (!chatInput) return;
        e.preventDefault();
        // Svelte/React controlled input için native setter kullan (input vs textarea)
        var proto = chatInput.tagName === 'TEXTAREA'
            ? window.HTMLTextAreaElement.prototype
            : window.HTMLInputElement.prototype;
        var nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
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


def render_queued_display(queued: list, lang: str = DEFAULT_LANG) -> str:
    if not queued:
        return ""
    badge = t(lang, "queued_badge")
    items = "".join(
        f'<div class="queued-msg-row"><span class="queued-msg-text">{q}</span>'
        f'<span class="queued-badge">{badge}</span></div>'
        for q in queued
    )
    return f'<div class="queued-display">{items}</div>'


def pre_submit(user_message: str, queued: list, lang: str = DEFAULT_LANG):
    msg = (user_message or "").strip()
    base = list(queued or [])
    if not msg:
        return "", base, render_queued_display(base, lang)
    new_queued = base + [msg]
    return "", new_queued, render_queued_display(new_queued, lang)


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


def respond_from_history(history, queued, session_id, sessions, anon_id, lang=DEFAULT_LANG):
    """Yields: (chatbot, textbox, empty_state, weather_panel, theme_state, map_panel,
    show_loc_btn, location_state, suggestion_box, queued_state, queued_display,
    session_id_state, sessions_state).

    `lang` = aktif UI dili. Cevap dili (turn_lang) ise bağımsız belirlenir:
    kart tıklamasıysa UI dili, yazılan mesajsa o mesajdan tespit edilir."""
    _abort.clear()
    if not queued:
        return

    user_message = queued[0]
    remaining = list(queued[1:])
    qd = render_queued_display(remaining, lang)

    # Bu turun cevap dili: hazır kart tıklamasıysa kartın (UI) dili — metin tespiti
    # kartlarda yanılabildiği için açıkça zorlanır; yazılan mesajda ise mesajdan tespit.
    is_card = user_message in CATEGORY_PREFS
    turn_lang = lang if is_card else _detect_language(user_message)

    # Kullanıcı bir kategori butonu seçtiyse tercihi Redis'e kaydet
    if anon_id and is_card:
        try:
            update_activity_preferences(anon_id, CATEGORY_PREFS[user_message])
        except Exception:
            pass

    if not session_id:
        session_id = new_session_id()

    history = list(history or [])
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": typing_indicator(lang)})

    yield gr.update(value=history, visible=True), gr.update(), gr.update(visible=False), gr.update(), gr.update(), gr.update(visible=False), gr.update(visible=False), [], gr.update(), remaining, qd, session_id, sessions

    convo_for_agent = history[:-1]
    clear_last_weather()
    clear_last_venues()
    clear_last_location()
    clear_last_forecast()
    clear_pending_nearby()
    panel_sent = False

    try:
        for partial in chat_skywise(convo_for_agent, anon_id=anon_id or None, force_language=turn_lang):
            if _abort.is_set():
                return
            history[-1]["content"] = partial if partial else typing_indicator(lang)
            weather = get_last_weather()

            if weather is not None and not panel_sent:
                panel_sent = True
                yield history, gr.update(), gr.update(), render_weather_panel(weather, lang=get_current_language()), weather_to_theme(weather), gr.update(), gr.update(), gr.update(), gr.update(), remaining, qd, session_id, sessions
            else:
                yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), remaining, qd, session_id, sessions

        # Harita görünürlüğü (deterministik):
        #  - venue_search somut mekan döndürdüyse öneri konuma bağlıdır → harita otomatik açılır.
        #  - Genel aktivite ([NEARBY:kategori]) → "Yakındaki yerleri göster" butonu (tık: arama + harita).
        #  - Anılan spesifik yer adları (LOC, venue yok) → "Haritada göster" butonu.
        venues = get_last_venues()
        locs = get_last_locations()
        cat, city = get_pending_nearby()
        if venues:
            map_html = render_map_panel(venues, lang=get_current_language())
            if map_html:
                yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(value=map_html, visible=True), gr.update(visible=False), locs, gr.update(), remaining, qd, session_id, sessions
        elif cat and city:
            yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(visible=False), gr.update(value=t(turn_lang, "nearby_btn"), visible=True), locs, gr.update(), remaining, qd, session_id, sessions
        elif locs:
            yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(visible=False), gr.update(value=t(turn_lang, "show_on_map"), visible=True), locs, gr.update(), remaining, qd, session_id, sessions

        new_sessions = _persist_turn(history, session_id, sessions, user_message, anon_id)

        hint, suggestion = generate_next_suggestion(history)
        default_placeholder = t(lang, "placeholder")
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
        err = "An error occurred" if turn_lang == "en" else "Bir hata oluştu"
        history[-1]["content"] = f"> ⚠️ {err}: {e}"
        new_sessions = _persist_turn(history, session_id, sessions, user_message, anon_id)
        yield history, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), remaining, qd, session_id, new_sessions


def clear_chat():
    """'Yeni Sohbet' — sohbeti ve panelleri temizler, aktif session id'yi sıfırlar.
    Hava panelini kullanıcının algılanan konumuna döndürür (önceki sohbette başka bir
    şehre bakılmış olabilir)."""
    _abort.set()
    clear_last_venues()
    clear_last_location()
    clear_last_forecast()
    clear_last_weather()
    weather_panel, theme = _location_weather_panel()
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
        gr.update(value="", visible=False),    # time_ribbon
        gr.update(value="", visible=False),    # rain_alert
        gr.update(value="", visible=False),    # week_heatmap
        gr.update(value="", visible=False),    # travel_panel
        weather_panel,
        theme,
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

    lang = get_current_language()
    weather_html = render_weather_panel(weather, lang=lang) if weather else render_panel_placeholder(t(lang, "no_weather_session"))
    theme = weather_to_theme(weather) if weather else "clear-day"

    if venues:
        map_html = render_map_panel(venues, lang=lang)
        map_upd = gr.update(value=map_html, visible=bool(map_html))
        loc_btn_upd = gr.update(visible=False)
    else:
        map_upd = gr.update(value="", visible=False)
        if locs:
            if lang == "en":
                btn_label = (
                    f"📍 Show {locs[0]} on map"
                    if len(locs) == 1
                    else f"📍 Show these on map ({len(locs)} places)"
                )
            else:
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
            render_panel_skeleton(),
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


def _locations_to_map_html(location_names) -> str:
    """Lokasyon adlarını geocode edip harita HTML'i üretir. Hiçbiri geocode
    edilemezse "" döner."""
    if not location_names:
        return ""
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
        return ""
    return render_locations_map(coords, lang=get_current_language())


def show_map_on_demand():
    """Harita butonu — bu turun mekanlarını/yerlerini haritada açar.
    Genel aktivitede ([NEARBY]) önce kategoriyi konuma göre arar; aksi halde
    mevcut venue verisini (puan/foto), yoksa LOC yer adlarını kullanır."""
    cat, city = get_pending_nearby()
    if cat and city and not get_last_venues():
        try:
            find_venues(city, cat)  # _LAST_VENUES doldurur (yüksek puanlı mekanlar)
        except Exception:
            pass
    venues = get_last_venues()
    map_html = render_map_panel(venues, lang=get_current_language()) if venues else _locations_to_map_html(get_last_locations())
    if not map_html:
        return gr.update(), gr.update(visible=False)
    return gr.update(value=map_html, visible=True), gr.update(visible=False)


def check_and_show_onboarding(anon_id: str, lang: str = DEFAULT_LANG):
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
    cats = i18n.cards(lang)
    return (
        gr.update(value=i18n.onboarding_html(lang)),
        gr.update(value=cats[0]),
        gr.update(value=cats[1]),
        gr.update(value=cats[2]),
        gr.update(value=cats[3]),
    )


def trigger_preference_reset(anon_id, lang: str = DEFAULT_LANG):
    """'Tercihlerimi Sıfırla' — kayıtlı aktivite tercihlerini siler, sohbeti
    temizler ve onboarding ekranını yeniden gösterir.
    Dönüş: NEW_CHAT_OUTPUTS + ONBOARDING_OUTPUTS (15 değer)
    """
    _abort.set()
    if anon_id:
        try:
            reset_preferences(anon_id)
        except Exception:
            pass
    clear_last_venues()
    clear_last_location()
    clear_last_forecast()
    clear_last_weather()
    cats = i18n.cards(lang)
    weather_panel, theme = _location_weather_panel()
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
        gr.update(value="", visible=False),    # time_ribbon
        gr.update(value="", visible=False),    # rain_alert
        gr.update(value="", visible=False),    # week_heatmap
        gr.update(value="", visible=False),    # travel_panel
        weather_panel,                         # weather_panel
        theme,                                 # theme_state
        gr.update(value=i18n.onboarding_html(lang)),  # greeting_html
        gr.update(value=cats[0]),              # sug1
        gr.update(value=cats[1]),              # sug2
        gr.update(value=cats[2]),              # sug3
        gr.update(value=cats[3]),              # sug4
    )


def load_default_city():
    # Geolocation zaten gerçek konumu uyguladıysa varsayılan şehirle üzerine yazma.
    if get_user_location():
        return gr.update(), gr.update()
    lang = get_current_language()
    try:
        weather = get_weather(DEFAULT_CITY)
        return render_weather_panel(weather, lang=lang), weather_to_theme(weather)
    except Exception:
        return render_panel_placeholder(t(lang, "weather_unavailable")), "clear-day"


def _location_weather_panel():
    """Kullanıcının algılanan konumuna (yoksa varsayılan şehre) göre hava panelini
    yeniden üretir. Yeni sohbet/tercih sıfırlama sırasında paneli kullanıcının kendi
    konumuna döndürmek için kullanılır. Dönüş: (weather_panel, theme_state)."""
    city = get_user_location() or DEFAULT_CITY
    try:
        weather = get_weather(city)
        return render_weather_panel(weather, lang=get_current_language()), weather_to_theme(weather)
    except Exception:
        return gr.update(), gr.update()


def finish_startup(lang: str = DEFAULT_LANG):
    """Açılış yüklemeleri (hava durumu + oturumlar + onboarding) bitince çağrılır.
    Girişleri aktif eder ve 'Hazırlanıyor' durumunu gizler.
    Dönüş: (textbox, send_btn, sug1, sug2, sug3, sug4, startup_status)."""
    return (
        gr.update(interactive=True, placeholder=t(lang, "placeholder")),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(visible=False),
    )


def set_busy():
    """Cevap üretilirken 'Gönder'i kilitler (sıraya-alma textbox üzerinden korunur)."""
    return gr.update(interactive=False)


def set_idle():
    """Cevap bitince 'Gönder'i yeniden aktif eder."""
    return gr.update(interactive=True)


def update_time_ribbon():
    """Bu turda çekilen saatlik tahminden 'en iyi saat' şeridini üretir (yoksa gizler)."""
    try:
        html = render_time_ribbon(get_last_forecast(), lang=get_current_language())
    except Exception:
        html = None
    if not html:
        return gr.update(value="", visible=False)
    return gr.update(value=html, visible=True)


def update_rain_alert():
    """Bu turda çekilen saatlik tahminden yağmur nowcast uyarısını üretir (yoksa gizler)."""
    try:
        html = render_rain_alert(get_last_forecast(), lang=get_current_language())
    except Exception:
        html = None
    if not html:
        return gr.update(value="", visible=False)
    return gr.update(value=html, visible=True)


def update_week_heatmap():
    """Çok günlü plan turunda (forecast_tool) gün × saat ısı haritasını üretir.
    Yalnızca bu turda hafta planı istendiyse ve ≥2 günlük veri varsa gösterir."""
    if not week_planner_requested():
        return gr.update(value="", visible=False)
    try:
        html = render_week_heatmap(get_last_forecast(), lang=get_current_language())
    except Exception:
        html = None
    if not html:
        return gr.update(value="", visible=False)
    return gr.update(value=html, visible=True)


def update_travel_panel():
    """Seyahat modunda (bu turda hedef şehir tespit edildiyse) konum vs hedef hava
    karşılaştırmasını üretir. Hedef yoksa, konum yoksa veya şehirler aynıysa gizler."""
    dest = get_travel_destination()
    home_city = get_user_location()
    if not dest or not home_city:
        return gr.update(value="", visible=False)
    dest_weather = get_last_weather()
    try:
        if not dest_weather or str(dest_weather.get("city", "")).lower() != dest.lower():
            dest_weather = get_weather(dest)
    except Exception:
        dest_weather = None
    try:
        home_weather = get_weather(home_city)
    except Exception:
        home_weather = None
    try:
        html = render_travel_compare(home_weather, dest_weather, get_current_language())
    except Exception:
        html = None
    if not html:
        return gr.update(value="", visible=False)
    return gr.update(value=html, visible=True)


def _process_feedback(anon_id, content, liked, lang):
    """Geri bildirim ortak işlemi: sayaç + kategori çıkarımı (senkron) + toast.

    Kategori taşıma (apply_feedback) senkron yapılır ki hemen ardından render edilen
    kart güncel liked/disliked'i yansıtsın — aksi halde 👎, eski liked kategorileri
    yüzünden 'like' gibi görünüyordu.
    """
    record_feedback(anon_id, liked)  # sayaç (feedback_count) → seviye
    apply_feedback(anon_id, content, bool(liked), lang)  # kategori taşıma → kart listesi
    if liked:
        gr.Info("Tercihin kaydedildi 👍 — bunu daha sık öneririm" if lang != "en"
                else "Noted 👍 — I'll suggest this more")
    else:
        gr.Info("Anlaşıldı 👎 — bunu bir daha pek önermem" if lang != "en"
                else "Got it 👎 — I'll avoid this from now on")


def _last_assistant_content(history):
    """history'deki son geçerli asistan mesajının metnini döner (typing göstergesi hariç)."""
    for msg in reversed(history or []):
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            content = msg.get("content")
            if content and not _is_typing(content):
                return content
    return None


def refresh_badge(anon_id):
    """Sidebar kişiselleştirme rozetini güncel seviyeyle yeniler."""
    return render_personalization_badge(
        get_personalization_level(anon_id), get_current_language()
    )


def make_calendar_file(history):
    """'Takvime ekle' — son öneriden zamanlı etkinlik çıkarır, .ics üretir ve indirme
    için dosya yolunu döner. Zamanlı etkinlik yoksa toast gösterir, dosyayı değiştirmez."""
    import os
    import tempfile
    from datetime import date

    from tools.calendar_ics import build_ics, extract_events

    lang = get_current_language()
    content = _last_assistant_content(history)
    if not content:
        return gr.update()
    try:
        events = extract_events(content, lang)
        ics = build_ics(events, date.today().isoformat())
    except Exception:
        ics = ""
    if not ics:
        gr.Info(t(lang, "calendar_none"))
        return gr.update()
    path = os.path.join(tempfile.gettempdir(), "skywise_plan.ics")
    with open(path, "w", encoding="utf-8") as f:
        f.write(ics)
    gr.Info(t(lang, "calendar_ready"))
    return gr.update(value=path)


# ---- Favori mekan handler'ları ----

def load_favorites_on_start(anon_id):
    try:
        return list_favorites(anon_id)
    except Exception:
        return []


def update_fav_controls(lang=DEFAULT_LANG):
    """Bu turun mekanlarına göre 'favoriye kaydet' kontrolünü (dropdown + buton) günceller.
    Mekan yoksa kontrolü gizler. Dönüş: (fav_save_row, fav_dd)."""
    venues = get_last_venues()
    names = [v.get("name") for v in (venues or []) if v.get("name")]
    if not names:
        return gr.update(visible=False), gr.update(choices=[], value=None)
    return gr.update(visible=True), gr.update(choices=names, value=names[0])


def on_save_favorite(selected_name, anon_id):
    """Seçili mekanı (bu turun venue verisinden) favorilere ekler ve listeyi döndürür."""
    if not anon_id or not selected_name:
        return gr.update()
    venue = next((v for v in (get_last_venues() or []) if v.get("name") == selected_name), None)
    if not venue:
        return gr.update()
    city = (get_last_weather() or {}).get("city") or (get_user_location() or "")
    try:
        add_favorite(anon_id, {
            "name": venue.get("name"),
            "city": city,
            "category": venue.get("type", ""),
            "lat": venue.get("lat"),
            "lon": venue.get("lon"),
            "maps_url": venue.get("maps_url", ""),
        })
        gr.Info(t(get_current_language(), "fav_saved"))
        return list_favorites(anon_id)
    except Exception:
        return gr.update()


def on_toggle_favorite(name, city, anon_id):
    try:
        toggle_favorite_done(anon_id, name, city)
        return list_favorites(anon_id)
    except Exception:
        return gr.update()


def on_remove_favorite(name, city, anon_id):
    try:
        remove_favorite(anon_id, name, city)
        return list_favorites(anon_id)
    except Exception:
        return gr.update()


def on_feedback_click(history, anon_id, liked):
    """Açık 👍/👎 butonu: son öneriye geri bildirim uygular, rozeti günceller ve
    feedback satırını gizler (toast bilgilendirir; yeni öneri gelene kadar görünmez).

    Döner: (pers_badge HTML, feedback_row görünürlük güncellemesi).
    """
    hide = gr.update(visible=False)
    lang = get_current_language()
    content = _last_assistant_content(history)
    if not anon_id or not content:
        return gr.update(), hide
    _process_feedback(anon_id, content, liked, lang)
    return render_personalization_badge(get_personalization_level(anon_id), lang), hide


def on_feedback(history, anon_id, evt: gr.LikeData):
    """Native chatbot 👍/👎 (hover) → ortak feedback işlemi, rozet günceli + satırı gizle.

    Döner: (pers_badge HTML, feedback_row görünürlük güncellemesi).
    """
    no_change = (gr.update(), gr.update())
    if not anon_id:
        return no_change
    # evt.index messages modunda ilgili mesajın indeksidir; kullanıcı mesajına veya
    # yazıyor-göstergesine basılan geri bildirimi yoksay.
    idx = evt.index if isinstance(evt.index, int) else (evt.index or [0])[0]
    msgs = history or []
    if not (0 <= idx < len(msgs)):
        return no_change
    msg = msgs[idx]
    if not isinstance(msg, dict):
        return no_change
    content = msg.get("content")
    if msg.get("role") != "assistant" or not content or _is_typing(content):
        return no_change

    lang = get_current_language()
    _process_feedback(anon_id, content, bool(evt.liked), lang)
    return render_personalization_badge(get_personalization_level(anon_id), lang), gr.update(visible=False)


def apply_geolocation(coords: str, anon_id: str = "", lang: str = DEFAULT_LANG):
    """Tarayıcıdan gelen koordinatlarla hava durumunu konuma göre günceller.

    Onboarding sırasındaki (tercihi olmayan) kullanıcıda öneri butonlarına dokunmaz —
    kategori butonları korunur ve gereksiz LLM çağrısı yapılmaz. Yalnızca tercihi olan
    kullanıcılar için konuma özel öneriler üretilir (UI dilinde).
    """
    noop_sugs = (gr.update(), gr.update(), gr.update(), gr.update())
    try:
        lat, lon = (float(x) for x in (coords or "").split(","))
        weather = get_weather_by_coords(lat, lon)
        set_user_location(weather["city"])
        try:
            has_prefs = bool(get_activity_preferences(anon_id)) if anon_id else False
        except Exception:
            has_prefs = False
        if not has_prefs:
            # Onboarding aktif: kategori butonlarını koru, sadece hava/temayı güncelle.
            return render_weather_panel(weather, lang=get_current_language()), weather_to_theme(weather), *noop_sugs
        suggestions = generate_location_suggestions(weather["city"], weather["country"], weather, lang=lang)
        btn_updates = [gr.update(value=s) for s in suggestions]
        return render_weather_panel(weather, lang=get_current_language()), weather_to_theme(weather), *btn_updates
    except Exception:
        return gr.update(), gr.update(), *noop_sugs


# ---- Dil (UI) yardımcıları ----

def _topbar_brand_html(lang: str) -> str:
    return (
        '<div class="topbar">'
        '<div class="brand"><span class="brand-logo">◐</span> SkyWise</div>'
        f'<div class="brand-tag">{t(lang, "brand_tag")}</div>'
        "</div>"
    )


def _startup_status_html(lang: str) -> str:
    return (
        '<div class="startup-status"><span class="startup-dot"></span>'
        f'{t(lang, "startup_status")}</div>'
    )


def _feedback_q_html(lang: str) -> str:
    return f"<span class='feedback-q'>{t(lang, 'feedback_q')}</span>"


def apply_language(lang: str):
    """Seçilen UI diline göre tüm statik arayüz metinlerini günceller.
    Dönüş sırası LANG_CHROME_OUTPUTS ile birebir aynıdır."""
    lang = i18n.normalize_lang(lang)
    cards = i18n.cards(lang)
    return (
        lang,                                          # lang_state
        gr.update(value=t(lang, "lang_toggle")),       # lang_toggle_btn
        gr.update(value=_topbar_brand_html(lang)),     # topbar_html
        gr.update(value=i18n.greeting_html(lang)),     # greeting_html
        gr.update(value=cards[0]),                     # sug1
        gr.update(value=cards[1]),                     # sug2
        gr.update(value=cards[2]),                     # sug3
        gr.update(value=cards[3]),                     # sug4
        gr.update(value=t(lang, "new_chat")),          # new_chat_btn
        gr.update(value=t(lang, "reset_prefs")),       # pref_update_btn
        gr.update(value=t(lang, "show_map_btn")),      # show_loc_btn
        gr.update(value=_feedback_q_html(lang)),       # feedback_q_html
        gr.update(value=t(lang, "fb_like")),           # fb_like
        gr.update(value=t(lang, "fb_dislike")),        # fb_dislike
        gr.update(value=t(lang, "send")),              # send_btn
        gr.update(placeholder=t(lang, "placeholder")), # textbox
        gr.update(value=_startup_status_html(lang)),   # startup_status
        # DownloadButton: buton metni `label`tır; `value` dosya yoludur — value'yu
        # ETİKETLE EZME (aksi halde tıkta o metni dosya sanıp 'File not allowed' verir).
        gr.update(label=t(lang, "calendar_btn")),      # dl_btn
        gr.update(value=t(lang, "fav_save_btn")),      # fav_save_btn
    )


def bootstrap_language(lang: str):
    """İlk açılışta (tarayıcı/localStorage) tespit edilen dili uygular ve sohbet
    dilini de bu dile tohumlar (henüz mesaj yokken yan paneller UI diline uysun)."""
    lang = i18n.normalize_lang(lang)
    set_current_language(lang)
    return apply_language(lang)


def toggle_language(current: str):
    """Dil geçiş butonu — iki dil arasında geçiş yapar (UI dili)."""
    new_lang = "en" if i18n.normalize_lang(current) == "tr" else "tr"
    return apply_language(new_lang)


with gr.Blocks(
    title="SkyWise — Hava Durumu Aktivite Asistanı",
    theme=gr.themes.Base(
        primary_hue="indigo",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    ),
    css=CUSTOM_CSS,
    js=FORCE_DARK_JS,
    fill_width=True,
) as demo:
    # Havaya duyarlı ambient partikül overlay'i (position:fixed; THEME_JS doldurur).
    gr.HTML('<div id="wx-fx" aria-hidden="true"></div>', elem_classes="wx-fx-host")
    with gr.Row(elem_classes="topbar-row"):
        toggle_sidebar_btn = gr.Button("◀", elem_classes="sidebar-toggle", scale=0)
        topbar_html = gr.HTML(_topbar_brand_html(DEFAULT_LANG))
        lang_toggle_btn = gr.Button(
            t(DEFAULT_LANG, "lang_toggle"), elem_classes="lang-toggle", scale=0
        )

    location_state = gr.State("")
    queued_state = gr.State([])
    # Anonim kimlik ve session state'leri
    anon_id_box = gr.Textbox(visible=False)  # localStorage anon-id (JS ile dolar)
    session_id_state = gr.State("")      # aktif session id; "" = henüz kaydedilmemiş yeni sohbet
    sessions_state = gr.State([])        # sidebar için session metadata listesi
    favorites_state = gr.State([])       # sidebar favori mekan listesi
    sidebar_visible = gr.State(True)
    # UI dili: varsayılan + JS ile (localStorage/tarayıcı) doldurulan kutu
    lang_state = gr.State(DEFAULT_LANG)
    lang_box = gr.Textbox(visible=False)  # LANG_JS ile dolar → bootstrap_language

    with gr.Row(elem_classes="main-row"):
        with gr.Column(scale=1, min_width=200, elem_classes="session-sidebar", visible=True) as sidebar_col:
            new_chat_btn = gr.Button(t(DEFAULT_LANG, "new_chat"), elem_classes="new-chat-btn")
            pref_update_btn = gr.Button(t(DEFAULT_LANG, "reset_prefs"), elem_classes="new-chat-btn", size="sm")
            pers_badge = gr.HTML(render_personalization_badge({}, DEFAULT_LANG), elem_classes="pers-badge")

            @gr.render(inputs=[sessions_state, session_id_state, lang_state])
            def render_sessions(sessions, active_id, lang):
                if not sessions:
                    gr.HTML(f"<div class='session-empty'>{t(lang, 'sessions_empty')}</div>")
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
                        show_progress="hidden",
                        api_name=False,
                    )
                    rename_btn.click(lambda: gr.update(visible=True), None, rename_row, show_progress="hidden", api_name=False)
                    rename_save.click(
                        lambda t, a, _s=sid: on_rename_session(_s, t, a),
                        [rename_box, anon_id_box],
                        [sessions_state, rename_row],
                        show_progress="hidden",
                        api_name=False,
                    )
                    del_btn.click(
                        lambda act, a, _s=sid: on_delete_session(_s, act, a),
                        [session_id_state, anon_id_box],
                        [sessions_state, chatbot, empty_state, weather_panel, map_panel, show_loc_btn, location_state, session_id_state],
                        show_progress="hidden",
                        api_name=False,
                    )

            @gr.render(inputs=[favorites_state, lang_state])
            def render_favorites(favs, lang):
                if not favs:
                    return
                gr.HTML(f"<div class='fav-title'>{t(lang, 'favorites_title')}</div>")
                for f in favs:
                    name = f.get("name", "")
                    city = f.get("city", "")
                    done = bool(f.get("done"))
                    check = "✅" if done else "⬜"
                    label = f"{check} {name}" + (f" · {city}" if city else "")
                    with gr.Row(elem_classes="fav-row" + (" done" if done else "")):
                        done_btn = gr.Button(label, elem_classes="fav-select", scale=8)
                        del_fav_btn = gr.Button("🗑", elem_classes="session-icon", scale=1, min_width=36)
                    done_btn.click(
                        lambda a, _n=name, _c=city: on_toggle_favorite(_n, _c, a),
                        [anon_id_box], favorites_state, show_progress="hidden", api_name=False,
                    )
                    del_fav_btn.click(
                        lambda a, _n=name, _c=city: on_remove_favorite(_n, _c, a),
                        [anon_id_box], favorites_state, show_progress="hidden", api_name=False,
                    )

        with gr.Column(scale=2, min_width=260, elem_classes="panel-col"):
            weather_panel = gr.HTML(render_panel_skeleton())
            rain_alert = gr.HTML(value="", visible=False, elem_classes="rain-alert-wrap")
            time_ribbon = gr.HTML(value="", visible=False, elem_classes="time-ribbon-wrap")
            week_heatmap = gr.HTML(value="", visible=False, elem_classes="week-heatmap-wrap")
            travel_panel = gr.HTML(value="", visible=False, elem_classes="travel-panel-wrap")
            map_panel = gr.HTML(value="", visible=False)
            show_loc_btn = gr.Button(t(DEFAULT_LANG, "show_map_btn"), visible=False, elem_classes="loc-btn")
            with gr.Row(visible=False, elem_classes="fav-save-row") as fav_save_row:
                fav_dd = gr.Dropdown(
                    choices=[], value=None, show_label=False, container=False,
                    scale=8, elem_classes="fav-dd",
                )
                fav_save_btn = gr.Button(
                    t(DEFAULT_LANG, "fav_save_btn"), elem_classes="fav-save-btn", scale=3, min_width=88
                )

        with gr.Column(scale=5, elem_classes="chat-surface"):
            with gr.Column(visible=True, elem_classes="empty-state") as empty_state:
                greeting_html = gr.HTML(i18n.greeting_html(DEFAULT_LANG))
                _init_cards = i18n.cards(DEFAULT_LANG)
                with gr.Row():
                    sug1 = gr.Button(_init_cards[0], elem_classes="suggestion-btn", interactive=False)
                    sug2 = gr.Button(_init_cards[1], elem_classes="suggestion-btn", interactive=False)
                with gr.Row():
                    sug3 = gr.Button(_init_cards[2], elem_classes="suggestion-btn", interactive=False)
                    sug4 = gr.Button(_init_cards[3], elem_classes="suggestion-btn", interactive=False)

            chatbot = gr.Chatbot(
                value=[],
                visible=False,
                type="messages",
                height=520,
                elem_classes="chat-area",
                show_copy_button=True,
                show_share_button=False,
                show_label=False,
                avatar_images=(None, None),
            )

            with gr.Row(visible=False, elem_classes="feedback-row") as feedback_row:
                feedback_q_html = gr.HTML(_feedback_q_html(DEFAULT_LANG))
                fb_like = gr.Button(t(DEFAULT_LANG, "fb_like"), elem_classes="fb-btn")
                fb_dislike = gr.Button(t(DEFAULT_LANG, "fb_dislike"), elem_classes="fb-btn")

            # Öneri turundan sonra görünür olur; tıkta son öneriden .ics üretip indirir.
            dl_btn = gr.DownloadButton(t(DEFAULT_LANG, "calendar_btn"), visible=False, elem_classes="calendar-btn")

            queued_display = gr.HTML(value="", elem_classes="queued-display-wrapper")

            startup_status = gr.HTML(
                _startup_status_html(DEFAULT_LANG),
                visible=True,
                elem_classes="startup-status-wrapper",
            )

            with gr.Row(elem_classes="chat-input-row"):
                textbox = gr.Textbox(
                    placeholder=t(DEFAULT_LANG, "textbox_loading"),
                    scale=9,
                    container=False,
                    lines=1,
                    max_lines=1,
                    show_label=False,
                    interactive=False,
                )
                send_btn = gr.Button(t(DEFAULT_LANG, "send"), variant="primary", scale=1, interactive=False)

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
    RESPOND_INPUTS = [chatbot, queued_state, session_id_state, sessions_state, anon_id_box, lang_state]
    PRE_OUTPUTS = [textbox, queued_state, queued_display]
    NEW_CHAT_OUTPUTS = [chatbot, empty_state, textbox, map_panel, show_loc_btn, location_state, queued_state, queued_display, session_id_state, time_ribbon, rain_alert, week_heatmap, travel_panel, weather_panel, theme_state]
    # Dil geçişinde güncellenecek tüm statik arayüz bileşenleri (apply_language sırası ile birebir).
    LANG_CHROME_OUTPUTS = [lang_state, lang_toggle_btn, topbar_html, greeting_html, sug1, sug2, sug3, sug4, new_chat_btn, pref_update_btn, show_loc_btn, feedback_q_html, fb_like, fb_dislike, send_btn, textbox, startup_status, dl_btn, fav_save_btn]

    # Feedback satırı yalnızca gerçek bir aktivite önerisi yapıldığında görünür;
    # netleştirme sorusu / yalnızca-hava turlarında gizli kalır.
    reveal_feedback = lambda: gr.update(visible=did_last_turn_recommend())
    reveal_calendar = lambda: gr.update(visible=did_last_turn_recommend())
    hide_feedback = lambda: gr.update(visible=False)
    for trigger in (textbox.submit, send_btn.click):
        (trigger(pre_submit, [textbox, queued_state, lang_state], PRE_OUTPUTS, show_progress="hidden", api_name=False)
         .then(set_busy, None, send_btn, show_progress="hidden", api_name=False)
         .then(respond_from_history, RESPOND_INPUTS, RESPOND_OUTPUTS, concurrency_limit=1, show_progress="hidden", api_name=False)
         .then(update_time_ribbon, None, time_ribbon, show_progress="hidden", api_name=False)
         .then(update_rain_alert, None, rain_alert, show_progress="hidden", api_name=False)
         .then(update_week_heatmap, None, week_heatmap, show_progress="hidden", api_name=False)
         .then(update_travel_panel, None, travel_panel, show_progress="hidden", api_name=False)
         .then(reveal_feedback, None, feedback_row, show_progress="hidden", api_name=False)
         .then(reveal_calendar, None, dl_btn, show_progress="hidden", api_name=False)
         .then(update_fav_controls, None, [fav_save_row, fav_dd], show_progress="hidden", api_name=False)
         .then(set_idle, None, send_btn, show_progress="hidden", api_name=False))
    for sug in (sug1, sug2, sug3, sug4):
        (sug.click(pre_submit, [sug, queued_state, lang_state], PRE_OUTPUTS, show_progress="hidden", api_name=False)
         .then(set_busy, None, send_btn, show_progress="hidden", api_name=False)
         .then(respond_from_history, RESPOND_INPUTS, RESPOND_OUTPUTS, concurrency_limit=1, show_progress="hidden", api_name=False)
         .then(update_time_ribbon, None, time_ribbon, show_progress="hidden", api_name=False)
         .then(update_rain_alert, None, rain_alert, show_progress="hidden", api_name=False)
         .then(update_week_heatmap, None, week_heatmap, show_progress="hidden", api_name=False)
         .then(update_travel_panel, None, travel_panel, show_progress="hidden", api_name=False)
         .then(reveal_feedback, None, feedback_row, show_progress="hidden", api_name=False)
         .then(reveal_calendar, None, dl_btn, show_progress="hidden", api_name=False)
         .then(update_fav_controls, None, [fav_save_row, fav_dd], show_progress="hidden", api_name=False)
         .then(set_idle, None, send_btn, show_progress="hidden", api_name=False))

    # Native chatbot (hover) 👍/👎 ve açık feedback butonları aynı işlemi paylaşır;
    # ikisi de rozeti günceller ve feedback satırını gizler (yeni öneri gelene kadar).
    chatbot.like(on_feedback, [chatbot, anon_id_box], [pers_badge, feedback_row], api_name=False)
    fb_like.click(lambda h, a: on_feedback_click(h, a, True), [chatbot, anon_id_box], [pers_badge, feedback_row], show_progress="hidden", api_name=False)
    fb_dislike.click(lambda h, a: on_feedback_click(h, a, False), [chatbot, anon_id_box], [pers_badge, feedback_row], show_progress="hidden", api_name=False)
    # Takvime ekle: son öneriden .ics üret ve indir.
    dl_btn.click(make_calendar_file, chatbot, dl_btn, show_progress="hidden", api_name=False)
    # Favoriye kaydet: seçili mekanı favorilere ekle → sidebar listesini yenile.
    fav_save_btn.click(on_save_favorite, [fav_dd, anon_id_box], favorites_state, show_progress="hidden", api_name=False)
    # Yeni sohbet: panelleri temizle + konumu kullanıcının konumuna döndür, ardından
    # tarayıcı geolocation'ı yeniden çek (gerçekten taşındıysa geo_coords.change tetiklenir).
    (new_chat_btn.click(clear_chat, None, NEW_CHAT_OUTPUTS, show_progress="hidden", api_name=False)
        .then(hide_feedback, None, feedback_row, show_progress="hidden", api_name=False)
        .then(hide_feedback, None, dl_btn, show_progress="hidden", api_name=False)
        .then(hide_feedback, None, fav_save_row, show_progress="hidden", api_name=False)
        .then(None, None, geo_coords, js=GEO_JS, api_name=False))
    (show_loc_btn.click(show_map_on_demand, None, [map_panel, show_loc_btn], show_progress="hidden", api_name=False)
        .then(update_fav_controls, None, [fav_save_row, fav_dd], show_progress="hidden", api_name=False))

    toggle_sidebar_btn.click(
        # Açıkken "◀" (kapat), kapalıyken "☰" (aç) ikonu göster.
        lambda vis: (gr.update(visible=not vis), not vis, gr.update(value="☰" if vis else "◀")),
        sidebar_visible, [sidebar_col, sidebar_visible, toggle_sidebar_btn], show_progress="hidden", api_name=False,
    )

    # Dil geçiş butonu: tüm statik arayüzü çevirir, ardından seçimi localStorage'a yazar.
    (lang_toggle_btn.click(toggle_language, lang_state, LANG_CHROME_OUTPUTS, show_progress="hidden", api_name=False)
        .then(None, lang_state, None, js=SAVE_LANG_JS, api_name=False))

    theme_state.change(None, theme_state, None, js=THEME_JS, api_name=False)

    ONBOARDING_OUTPUTS = [greeting_html, sug1, sug2, sug3, sug4]
    STARTUP_ENABLE_OUTPUTS = [textbox, send_btn, sug1, sug2, sug3, sug4, startup_status]

    # Hava durumu (varsayılan şehir) bağımsız/paralel yüklenir — girişleri bloklamaz.
    # Geolocation gerçek konumu uygularsa load_default_city üzerine yazmaz (yarış önlenir).
    # Ayrıca güvenlik ağı: Python load'ın `.then`'i güvenilir tetiklenir; anon_id.change
    # zinciri herhangi bir sebeple çalışmasa bile girişler burada kesin açılır.
    (demo.load(load_default_city, None, [weather_panel, theme_state], show_progress="hidden", api_name=False)
        .then(finish_startup, lang_box, STARTUP_ENABLE_OUTPUTS, show_progress="hidden", api_name=False))
    demo.load(None, None, geo_coords, js=GEO_JS, api_name=False)
    geo_coords.change(apply_geolocation, [geo_coords, anon_id_box, lang_state], [weather_panel, theme_state, sug1, sug2, sug3, sug4], show_progress="hidden", api_name=False)

    # UI dili: localStorage/tarayıcı tespiti (LANG_JS) → bootstrap_language tüm chrome'u çevirir.
    demo.load(None, None, lang_box, js=LANG_JS, api_name=False)
    lang_box.change(bootstrap_language, lang_box, LANG_CHROME_OUTPUTS, show_progress="hidden", api_name=False)

    # Giriş kilidi yalnızca hızlı Redis okumalarına bağlıdır: anon-id (JS) → oturum listesi →
    # onboarding kontrolü → girişleri aç. Hava durumu beklenmez (skeleton ile dolar).
    #
    # Tetikleyici olarak JS load'ın `.then`'i yerine anon_id_box.change kullanılır:
    # JS-load'dan SONRA `.then` zinciri Gradio 4.44'te güvenilir tetiklenmiyor ve
    # finish_startup çalışmayınca girişler kilitli kalıyordu. .change ise (geo_coords
    # ile aynı kanıtlanmış desen) JS değeri set edince güvenilir tetiklenir.
    demo.load(None, None, anon_id_box, js=ANON_ID_JS, api_name=False)
    (anon_id_box.change(load_sessions_on_start, anon_id_box, sessions_state, show_progress="hidden", api_name=False)
        .then(load_favorites_on_start, anon_id_box, favorites_state, show_progress="hidden", api_name=False)
        .then(check_and_show_onboarding, [anon_id_box, lang_box], ONBOARDING_OUTPUTS, show_progress="hidden", api_name=False)
        .then(refresh_badge, anon_id_box, pers_badge, show_progress="hidden", api_name=False)
        .then(finish_startup, lang_box, STARTUP_ENABLE_OUTPUTS, show_progress="hidden", api_name=False))

    (pref_update_btn.click(
        trigger_preference_reset,
        [anon_id_box, lang_state],
        NEW_CHAT_OUTPUTS + ONBOARDING_OUTPUTS,
        show_progress="hidden",
        api_name=False,
    )
        .then(hide_feedback, None, feedback_row, show_progress="hidden", api_name=False)
        .then(hide_feedback, None, dl_btn, show_progress="hidden", api_name=False)
        .then(hide_feedback, None, fav_save_row, show_progress="hidden", api_name=False)
        .then(refresh_badge, anon_id_box, pers_badge, show_progress="hidden", api_name=False))


if __name__ == "__main__":
    demo.queue(max_size=20)
    # HF Spaces'in reverse-proxy'si konteynere ulaşabilsin diye 0.0.0.0'a bağlan;
    # yerelde 127.0.0.1 kalsın.
    server_name = "0.0.0.0" if IS_HF_SPACE else "127.0.0.1"
    demo.launch(show_error=True, show_api=False, server_name=server_name)
