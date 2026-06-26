"""WeatherWise arayüz çevirileri (i18n).

Statik UI metinlerinin tek doğruluk kaynağı. Sohbet cevabının dili buradan
bağımsızdır (o, kullanıcının yazdığı dile göre `chat.py` tarafından belirlenir);
burada yalnızca arayüz "chrome" metinleri ve kategori kartları tutulur.
"""

from __future__ import annotations

# ---- Statik arayüz metinleri -------------------------------------------------

UI: dict[str, dict[str, str]] = {
    "tr": {
        "brand_tag": "Hava durumuna göre kişisel aktivite asistanın",
        "new_chat": "➕ Yeni Sohbet",
        "reset_prefs": "🔄 Tercihlerimi Sıfırla",
        "sessions_empty": "Henüz sohbet yok",
        "show_map_btn": "📍 Haritada Göster",
        "feedback_q": "Bu öneri işine yaradı mı?",
        "fb_like": "👍 Beğendim",
        "fb_dislike": "👎 Pek değil",
        "startup_status": "Senin için hava durumu ve öneriler hazırlanıyor…",
        "textbox_loading": "Hazırlanıyor…",
        "placeholder": 'Etkinlik sor... (örn: "Bugün koşu için hava uygun mu?")',
        "send": "Gönder ↗",
        "queued_badge": "🕒 Sırada",
        "typing": "yanıt hazırlanıyor",
        "nearby_btn": "📍 Yakındaki yerleri göster",
        "show_on_map": "📍 Haritada göster",
        "no_weather_session": "Bu sohbet için kayıtlı hava durumu yok.",
        "weather_unavailable": "Hava durumu alınamadı.",
        "calendar_btn": "📅 Takvime ekle",
        "calendar_none": "Takvime eklenecek zamanlı bir etkinlik bulunamadı.",
        "calendar_ready": "Takvim dosyan hazır — indirilen .ics'i takvimine aktarabilirsin.",
        "favorites_title": "⭐ Favori Mekanlarım",
        "fav_save_ph": "Kaydetmek için mekan seç…",
        "fav_save_btn": "⭐ Kaydet",
        "fav_saved": "Mekan favorilere eklendi ⭐",
        # Geçiş butonu hedef dili gösterir (TR'deyken İngilizce'ye geçilir)
        "lang_toggle": "🌐 EN",
    },
    "en": {
        "brand_tag": "Your personal weather-based activity assistant",
        "new_chat": "➕ New Chat",
        "reset_prefs": "🔄 Reset My Preferences",
        "sessions_empty": "No chats yet",
        "show_map_btn": "📍 Show on Map",
        "feedback_q": "Was this suggestion helpful?",
        "fb_like": "👍 Liked it",
        "fb_dislike": "👎 Not really",
        "startup_status": "Preparing weather and suggestions for you…",
        "textbox_loading": "Loading…",
        "placeholder": 'Ask about an activity... (e.g., "Is the weather good for a run today?")',
        "send": "Send ↗",
        "queued_badge": "🕒 Queued",
        "typing": "preparing a response",
        "nearby_btn": "📍 Show nearby places",
        "show_on_map": "📍 Show on map",
        "no_weather_session": "No saved weather for this chat.",
        "weather_unavailable": "Weather unavailable.",
        "calendar_btn": "📅 Add to calendar",
        "calendar_none": "No timed activity found to add to the calendar.",
        "calendar_ready": "Your calendar file is ready — import the downloaded .ics into your calendar.",
        "favorites_title": "⭐ My Saved Places",
        "fav_save_ph": "Pick a place to save…",
        "fav_save_btn": "⭐ Save",
        "fav_saved": "Saved to favorites ⭐",
        "lang_toggle": "🌐 TR",
    },
}

# ---- Kategori kartları -------------------------------------------------------
# Kartın value'su aynı zamanda chat'e gönderilen mesajdır; bu yüzden kart dilini
# değiştirmek hem görüneni hem de cevap dilini belirler. CATEGORY_PREFS (app.py)
# her iki dildeki etiketleri de tanır.

CARDS: dict[str, list[str]] = {
    "tr": [
        "🏃 Spor & Fitness",
        "🌿 Doğa & Yürüyüş",
        "🎨 Kültür & Müze",
        "🍽️ Yemek & Kafe",
    ],
    "en": [
        "🏃 Sports & Fitness",
        "🌿 Nature & Hiking",
        "🎨 Culture & Museum",
        "🍽️ Food & Café",
    ],
}

# ---- Karşılama / onboarding HTML --------------------------------------------

GREETING: dict[str, str] = {
    "tr": """
<div class="greeting">
    <div class="wave">🌤️</div>
    <h2>Merhaba! Ben WeatherWise</h2>
    <p>Bulunduğun şehrin hava durumuna göre sana en uygun aktiviteleri öneririm.
    Aşağıdan kategori seç ya da istediğini yaz — hemen öneriler hazırlayayım.</p>
</div>
""",
    "en": """
<div class="greeting">
    <div class="wave">🌤️</div>
    <h2>Hi! I'm WeatherWise</h2>
    <p>Based on the weather in your city, I suggest the activities that suit you best.
    Pick a category below or just type what you want — I'll prepare suggestions right away.</p>
</div>
""",
}

ONBOARDING: dict[str, str] = {
    "tr": """
<div class="greeting">
    <div class="wave">🌤️</div>
    <h2>Merhaba! Ben WeatherWise</h2>
    <div class="onboarding-question">
        <p><strong>Hangi tür aktiviteleri seversin?</strong></p>
        <p>Aşağıdan bir kategori seç — bulunduğun yerin havasına göre hemen öneriler hazırlayayım.</p>
    </div>
</div>
""",
    "en": """
<div class="greeting">
    <div class="wave">🌤️</div>
    <h2>Hi! I'm WeatherWise</h2>
    <div class="onboarding-question">
        <p><strong>What kind of activities do you enjoy?</strong></p>
        <p>Pick a category below — I'll prepare suggestions based on your local weather right away.</p>
    </div>
</div>
""",
}


def normalize_lang(lang: str | None) -> str:
    """Desteklenen dile indirger (tr/en); bilinmeyen → tr."""
    return lang if lang in UI else "tr"


def t(lang: str, key: str) -> str:
    """Verilen dilde UI metnini döner; eksikse Türkçe'ye düşer."""
    lang = normalize_lang(lang)
    return UI[lang].get(key) or UI["tr"][key]


def cards(lang: str) -> list[str]:
    return CARDS[normalize_lang(lang)]


def greeting_html(lang: str) -> str:
    return GREETING[normalize_lang(lang)]


def onboarding_html(lang: str) -> str:
    return ONBOARDING[normalize_lang(lang)]


def typing_indicator(lang: str = "tr") -> str:
    """Yanıt beklenirken gösterilen 'yazıyor...' göstergesi (dile duyarlı etiket)."""
    return (
        '<div class="typing-indicator">'
        "<span></span><span></span><span></span>"
        f'<span class="typing-label">{t(lang, "typing")}</span>'
        "</div>"
    )


def is_typing(content) -> bool:
    """Bir mesaj içeriğinin 'yazıyor...' göstergesi olup olmadığını yapısal kontrol eder
    (dil etiketinden bağımsız)."""
    return isinstance(content, str) and 'class="typing-indicator"' in content
