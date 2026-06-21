"""Sohbet tabanlı SkyWise katmanı — ReAct agent + supervisor gate."""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Iterator
from typing import Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from core.llms import evaluator_llm, itinerary_llm, react_llm
from core.prompts import get_prompt
from core.graph import _parse_supervisor
from tools.memory import extract_and_update, format_memory_block, load_memory
from tools.uv import get_uv_index
from tools.venue import find_venues, format_venues_for_llm
from tools.weather import (
    calculate_comfort_index,
    format_weather_summary,
    get_forecast,
    get_last_weather,
    get_weather,
)

# ---- Dil tespiti ----

_TURKISH_CHARS = set("ğışçöüĞİŞÇÖÜ")
_TURKISH_WORDS = {
    "merhaba", "nasıl", "bugün", "hava", "istanbul", "ankara",
    "ne", "için", "ben", "bir", "ve", "de", "da", "mi", "mu",
    "var", "yok", "evet", "hayır", "lütfen", "teşekkür",
}

_current_language: str = "tr"
_last_locations: list[str] = []
_user_location: Optional[str] = None  # Kullanıcının bildirdiği güncel konum

_LOC_TAG_RE = re.compile(r'\[LOC:([^\]]+)\]')

# Kullanıcının "şu an buradayım" tarzı konum bildirimlerini yakalayan kalıplar.
# Yakalanan grup şehir adıdır (büyük harfle başlamalı → yaygın kelimeleri eler).
_LOC_UPDATE_PATTERNS = (
    # TR: "İstanbul'dayım", "Ankara'dayim", "Berlin'deyim", "İzmir'deyim"
    re.compile(r"\b([A-ZÇĞİÖŞÜ][\wçğıöşü]+)['’]?(?:de|da|te|ta)y[ıi]m\b", re.UNICODE),
    # TR: "Berlin'e taşındım/geldim/vardım/ulaştım"
    re.compile(
        r"\b([A-ZÇĞİÖŞÜ][\wçğıöşü]+)['’]?[ae]\s+"
        r"(?:taşındım|tasindim|geldim|vardım|vardim|ulaştım|ulastim|yerleştim|yerlestim)\b",
        re.UNICODE,
    ),
    # TR: "konumum Berlin", "yeni konumum Berlin", "şu an Berlin'deyim" (üstte)
    re.compile(r"konum(?:um)?\s+([A-ZÇĞİÖŞÜ][\wçğıöşü]+)", re.UNICODE),
    # EN: "I'm in Berlin", "I am now in Berlin", "currently in Berlin"
    re.compile(r"\b(?:i['’]?m|i am|currently|now)\s+(?:now\s+)?in\s+([A-Z][\w]+)", re.IGNORECASE),
    # EN: "I moved to Berlin", "arrived in Berlin", "relocated to Berlin"
    re.compile(
        r"\b(?:moved to|relocated to|arrived in|arrived at|traveled to|travelled to)\s+([A-Z][\w]+)",
        re.IGNORECASE,
    ),
    # EN: "my location is Berlin"
    re.compile(r"\bmy location is\s+([A-Z][\w]+)", re.IGNORECASE),
)


def get_last_locations() -> list[str]:
    return list(_last_locations)


def clear_last_location() -> None:
    global _last_locations
    _last_locations = []


def set_user_location(city: str) -> None:
    global _user_location
    _user_location = city or None


def _detect_language(text: str) -> str:
    if any(c in _TURKISH_CHARS for c in text):
        return "tr"
    words = set(text.lower().split())
    if words & _TURKISH_WORDS:
        return "tr"
    return "en"


def get_current_language() -> str:
    return _current_language


# ---- Intent Router ----

_WEATHER_ONLY_TR = frozenset([
    "hava", "sıcaklık", "sicaklik", "nem", "yağmur", "yagmur",
    "rüzgar", "ruzgar", "fırtına", "firtina", "kar", "sis",
    "tahmin", "derece", "celsius", "uv", "güneş", "gunes",
])
_WEATHER_ONLY_EN = frozenset([
    "weather", "temperature", "humidity", "rain", "raining",
    "wind", "storm", "snow", "fog", "forecast", "degrees",
    "celsius", "fahrenheit", "uv", "sunny", "cloudy",
])
_ACTIVITY_TRIGGERS = frozenset([
    # TR
    "müze", "muze", "kafe", "park", "restoran", "spor", "aktivite",
    "öneri", "oneri", "öner", "oner", "nereye", "ne yapabilirim", "gez", "git", "yap",
    "plaj", "sinema", "galeri", "kütüphane", "kutuphane", "manzara",
    "etkinlik", "etkinlikleri", "gezi", "yürüyüş", "yuruyus", "piknik",
    # EN
    "museum", "cafe", "restaurant", "activity", "activities", "suggest", "recommend",
    "where", "what can", "beach", "cinema", "gallery", "library", "viewpoint",
    "walk", "hike", "picnic",
])
_FOLLOWUP_TR = frozenset(["orada", "başka", "baska", "daha", "peki", "diğer", "diger"])
_FOLLOWUP_EN = frozenset(["there", "else", "another", "other", "more", "instead"])

# Sınıflandırıcıda yok sayılacak yaygın kelimeler (yanlış şehir tespitini önler)
_COMMON_STOPWORDS = frozenset([
    "hava", "nasıl", "bugün", "yarın", "şimdi", "sıcaklık", "nem",
    "the", "weather", "today", "what", "how", "is", "like", "for",
    "in", "at", "bir", "ve", "de", "da", "mi", "mu", "var", "yok",
])


def _classify_intent(
    text: str, lang: str, has_history: bool
) -> Literal["weather_only", "activity", "follow_up", "other"]:
    """Kural tabanlı intent sınıflandırıcı — ek LLM çağrısı yoktur."""
    lower = text.lower()
    tokens = set(lower.split())
    followup_kw = _FOLLOWUP_TR if lang == "tr" else _FOLLOWUP_EN
    weather_kw = _WEATHER_ONLY_TR if lang == "tr" else _WEATHER_ONLY_EN

    if has_history and (tokens & followup_kw):
        return "follow_up"
    if any(kw in lower for kw in _ACTIVITY_TRIGGERS):
        return "activity"
    # "hava" tek başına weather_only sayılır; ama "açık hava" + eylem varsa activity
    if tokens & weather_kw:
        if "açık hava" in lower or "outdoor" in lower:
            return "activity"
        return "weather_only"
    return "other"


def _extract_city_from_message(text: str) -> Optional[str]:
    """Mesajdan büyük harfle başlayan şehir adayı çıkar (heuristic).

    Türkçe ekleri (Londra'daki, İzmir'de) ayıklar → temiz şehir adı döner.
    """
    for word in text.split():
        clean = word.strip("?.,!:;").strip()
        # Kesme işaretinden sonrasını (ek) at: "Londra'daki" → "Londra"
        clean = re.split(r"['’]", clean)[0]
        if clean and len(clean) > 1 and clean[0].isupper() and clean.lower() not in _COMMON_STOPWORDS:
            return clean
    return None


def _detect_location_update(text: str) -> Optional[str]:
    """Mesaj bir konum bildirimi içeriyorsa yeni şehri döner, yoksa None."""
    for pattern in _LOC_UPDATE_PATTERNS:
        m = pattern.search(text)
        if m:
            city = m.group(1).strip()
            if city and city.lower() not in _COMMON_STOPWORDS:
                return city
    return None


def _location_update_reply(city: str) -> Optional[str]:
    """Yeni konum için kısa onay + güncel hava durumu özeti üretir.

    Hava durumu alınamazsa None döner (normal akışa düşülür).
    """
    try:
        w = get_weather(city, lang=_current_language)
    except (ValueError, ConnectionError):
        return None
    try:
        uv = get_uv_index(city, lang=_current_language)
    except Exception:
        uv = None
    summary = format_weather_summary(w, uv=uv, lang=_current_language)
    if _current_language == "en":
        intro = f"📍 Got it — you're now in **{city}**. Here's the current weather:\n\n"
    else:
        intro = f"📍 Anlaşıldı, şu an **{city}** konumundasın. Güncel hava durumu:\n\n"
    return intro + summary


def _handle_weather_only(text: str, messages: list[dict]) -> Optional[str]:
    """Doğrudan hava durumu sorgusunu ReAct'ı atlatarak yanıtlar.

    Şehir bulunamazsa None döner ve ReAct'a düşülür.
    """
    # Mesajda açıkça şehir varsa onu kullan; yoksa kullanıcı konumu, sonra map
    city: Optional[str] = _extract_city_from_message(text)
    if not city:
        city = _user_location or (_last_locations[0] if _last_locations else None)
    if not city:
        # Geçmişteki kullanıcı mesajlarında şehir ara
        for m in reversed(messages[:-1]):
            if m.get("role") == "user":
                city = _extract_city_from_message(m.get("content", ""))
                if city:
                    break
    if not city:
        return None

    try:
        w = get_weather(city, lang=_current_language)
        try:
            uv = get_uv_index(city, lang=_current_language)
        except Exception:
            uv = None
        return format_weather_summary(w, uv=uv, lang=_current_language)
    except (ValueError, ConnectionError):
        return None


# ---- LangChain tool tanımları ----

@tool
def current_weather_tool(city: str) -> str:
    """Returns the current weather for the given city, including UV index and sunset time."""
    try:
        w = get_weather(city, lang=_current_language)
        try:
            uv = get_uv_index(city, lang=_current_language)
        except Exception:
            uv = None
        return format_weather_summary(w, uv=uv, lang=_current_language)
    except (ValueError, ConnectionError) as e:
        return f"Hata: {e}"


@tool
def forecast_tool(city: str) -> str:
    """Returns the 3-day weather forecast for the given city."""
    try:
        return get_forecast(city, days=3, lang=_current_language)
    except (ValueError, ConnectionError) as e:
        return f"Hata: {e}"


@tool
def comfort_tool(temperature: float, humidity: int, wind_speed: float) -> str:
    """Analyzes outdoor activity comfort based on temperature, humidity, and wind speed."""
    return calculate_comfort_index(temperature, humidity, wind_speed)


@tool
def venue_search_tool(city: str, category: str, radius_km: int = 5) -> str:
    """Finds real venues near a city (Google Places or OpenStreetMap).
    category: müze/museum, park, kafe/cafe, restoran/restaurant, spor salonu/gym,
    manzara/viewpoint, kütüphane/library, sanat galerisi/art gallery,
    alışveriş/shopping mall, plaj/beach, sinema/cinema."""
    try:
        venues = find_venues(city, category, radius_km=radius_km)
        return format_venues_for_llm(venues, category, city, lang=_current_language)
    except (ValueError, ConnectionError) as e:
        return f"Hata: {e}"


@tool
def uv_tool(city: str) -> str:
    """Returns the current UV index and sun protection advice for the given city."""
    try:
        uv = get_uv_index(city, lang=_current_language)
        if _current_language == "en":
            return f"UV Index: {uv['uv_index']} ({uv['uv_level_en']}) — {uv['uv_advice_en']}"
        return f"UV İndeksi: {uv['uv_index']} ({uv['uv_level_tr']}) — {uv['uv_advice_tr']}"
    except Exception as e:
        return f"UV verisi alınamadı: {e}"


# ---- ReAct worker ----

_RECOMMENDATION_TOOLS = {"current_weather_tool", "venue_search_tool"}

_chat_worker = create_react_agent(
    react_llm,
    tools=[current_weather_tool, forecast_tool, comfort_tool, venue_search_tool, uv_tool],
)


# ---- Yardımcılar ----

def _gradio_to_lc_messages(messages: list[dict], username: Optional[str] = None) -> list:
    global _current_language

    # Dil tespiti: ilk kullanıcı mesajından
    for m in messages:
        if m.get("role") == "user" and (m.get("content") or "").strip():
            _current_language = _detect_language(m["content"])
            break

    base_prompt = get_prompt("chat", _current_language)
    memory_block = format_memory_block(load_memory(username), _current_language)
    system_content = base_prompt + ("\n\n" + memory_block if memory_block else "")
    lc: list = [SystemMessage(content=system_content)]
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            lc.append(HumanMessage(content=content))
        elif role == "assistant":
            lc.append(AIMessage(content=content))
    return lc


def _turn_produced_recommendation(new_messages: list) -> bool:
    for m in new_messages:
        if isinstance(m, AIMessage):
            for call in getattr(m, "tool_calls", None) or []:
                name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
                if name in _RECOMMENDATION_TOOLS:
                    return True
        elif isinstance(m, ToolMessage):
            if getattr(m, "name", "") in _RECOMMENDATION_TOOLS:
                return True
    return False


_CITY_TOOLS = frozenset(
    {"venue_search_tool", "current_weather_tool", "forecast_tool", "uv_tool"}
)


def _focus_city_from_tools(new_messages: list) -> Optional[str]:
    """Bu turda çağrılan araçların 'city' argümanından ele alınan şehri döner.

    Kullanıcının sorduğu ya da asistanın önerdiği yer buradan gelir; sol
    panelin hangi şehre güncelleneceğini belirlemek için en güvenilir sinyal.
    """
    city: Optional[str] = None
    for m in new_messages:
        if not isinstance(m, AIMessage):
            continue
        for call in getattr(m, "tool_calls", None) or []:
            name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
            if name in _CITY_TOOLS:
                args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
                value = (args or {}).get("city")
                if value and value.strip():
                    city = value.strip()  # son çağrılan şehir geçerli olsun
    return city


def _last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return (m.get("content") or "").strip()
    return ""


def _supervise_chat_turn(
    worker_text: str, new_messages: list, original_messages: list[dict]
) -> str:
    tool_outputs: list[str] = []
    for m in new_messages:
        if isinstance(m, ToolMessage):
            tool_outputs.append(f"[{m.name}]\n{m.content}")

    user_block = _last_user_text(original_messages) or "(kullanıcı mesajı yok)"
    context_block = "\n\n".join(tool_outputs) or "yok"

    raw = evaluator_llm.invoke(
        [
            SystemMessage(content=get_prompt("supervisor", _current_language)),
            HumanMessage(
                content=(
                    f"Kullanıcı son mesajı:\n{user_block}\n\n"
                    f"Worker'ın bu turda topladığı veriler:\n{context_block}\n\n"
                    f"Değerlendirilecek öneri:\n{worker_text}"
                )
            ),
        ]
    ).content

    evaluation = _parse_supervisor(raw)
    if evaluation.get("approved"):
        return worker_text

    corrected = (evaluation.get("corrected") or "").strip()
    if corrected and corrected.lower() != "öneri uygundur.":
        return corrected
    return worker_text


def _stream_chunks(text: str, chunk_size: int = 6, delay_s: float = 0.012) -> Iterator[str]:
    if not text:
        yield ""
        return
    buf = ""
    for i in range(0, len(text), chunk_size):
        buf += text[i: i + chunk_size]
        yield buf
        time.sleep(delay_s)
    if buf != text:
        yield text


# ---- Itinerary Agent (chat için) ----

def _generate_itinerary_for_chat(
    recommendation: str,
    new_messages: list,
) -> Optional[str]:
    """Öneri metninden günlük zaman planı üretir.

    Tool çıktılarını (hava, venue) toplar ve itinerary_llm'e iletir.
    Hata durumunda None döner — öneri yine de gösterilir.
    """
    sections: list[str] = []
    for m in new_messages:
        if isinstance(m, ToolMessage) and m.content:
            sections.append(f"[{m.name}]\n{m.content}")

    if not sections:
        return None

    if _current_language == "tr":
        sections.append(f"AKTİVİTE ÖNERİLERİ:\n{recommendation}")
        human = "\n\n".join(sections) + "\n\nLütfen günlük zaman planı oluştur."
    else:
        sections.append(f"ACTIVITY SUGGESTIONS:\n{recommendation}")
        human = "\n\n".join(sections) + "\n\nPlease create a day itinerary."

    try:
        raw = itinerary_llm.invoke([
            SystemMessage(content=get_prompt("itinerary", _current_language)),
            HumanMessage(content=human),
        ]).content
        return raw.strip() or None
    except Exception:
        return None


# ---- Public API ----

def chat_skywise(messages: list[dict], username: Optional[str] = None) -> Iterator[str]:
    """Sohbet tabanlı SkyWise asistanı.

    Girdi: Gradio Chatbot(type="messages") formatı —
        [{"role": "user"|"assistant", "content": str}, ...]
    Çıktı: kümülatif metin parçaları (streaming) — son chunk tam yanıttır.
    """
    # Dil tespiti + LangChain mesajlarına dönüşüm (bu _current_language'ı günceller)
    lc_messages = _gradio_to_lc_messages(messages, username=username)
    n_original = len(lc_messages)

    # Intent sınıflandırma (dil güncel olduktan sonra)
    last_user = _last_user_text(messages)
    has_history = any(m.get("role") == "assistant" for m in messages)
    intent = _classify_intent(last_user, _current_language, has_history)

    # Konum güncellemesi tespiti → sol paneldeki hava durumunu anında yenile.
    # get_weather() çağrısı _LAST_WEATHER'ı set eder; UI bunu okuyup paneli günceller.
    global _user_location
    updated_city = _detect_location_update(last_user)
    if updated_city:
        try:
            get_weather(updated_city, lang=_current_language)
            _user_location = updated_city
        except (ValueError, ConnectionError):
            updated_city = None

    # Yalnızca konum bildirimi (başka istek yok) → kısa onay + hava özeti
    if updated_city and intent == "other":
        reply = _location_update_reply(updated_city)
        if reply is not None:
            yield from _stream_chunks(reply)
            return

    # weather_only fast-path: ReAct'ı atla
    if intent == "weather_only":
        result = _handle_weather_only(last_user, messages)
        if result is not None:
            yield from _stream_chunks(result)
            return

    # Standart ReAct yolu
    result = _chat_worker.invoke({"messages": lc_messages})
    all_messages = result.get("messages", [])
    new_messages = all_messages[n_original:]

    final_ai = all_messages[-1] if all_messages else None
    worker_text = (
        final_ai.content if isinstance(final_ai, AIMessage) and final_ai.content else ""
    )

    if not worker_text:
        worker_text = "Üzgünüm, şu an cevap üretemedim. Tekrar dener misin?"

    if _turn_produced_recommendation(new_messages):
        try:
            final_text = _supervise_chat_turn(worker_text, new_messages, messages)
        except Exception:
            final_text = worker_text

        # Itinerary agent: öneri üretilen turlarda günlük plan ekle
        try:
            itinerary = _generate_itinerary_for_chat(final_text, new_messages)
            if itinerary:
                sep = "\n\n---\n\n"
                final_text = final_text + sep + itinerary
        except Exception:
            pass

        # Hafıza güncelleme: arka planda çalıştır, ana akışı bloke etme
        focus_city = _focus_city_from_tools(new_messages) or _user_location
        full_messages = messages + [{"role": "assistant", "content": final_text}]
        threading.Thread(
            target=extract_and_update,
            args=(full_messages, focus_city, _current_language, username),
            daemon=True,
        ).start()
    else:
        final_text = worker_text

    # LOC etiketleri: tüm yer isimlerini çıkar, etiketleri metinden temizle
    global _last_locations
    _last_locations = [m.strip() for m in _LOC_TAG_RE.findall(final_text)]
    final_text = _LOC_TAG_RE.sub("", final_text).strip()

    # Sol panel güvencesi: bu turda hava durumu zaten çekildiyse (current_weather_tool)
    # panel doğru şehirde. Çekilmediyse, ele alınan şehri belirle ve havasını çek:
    #   1) bu turda araca verilen şehir (sorulan/önerilen yer)
    #   2) mesajda açıkça geçen şehir
    #   3) hiçbiri yoksa kullanıcının kendi konumu (yer belirtmediyse)
    if get_last_weather() is None:
        focus_city = (
            _focus_city_from_tools(new_messages)
            or _extract_city_from_message(last_user)
            or _user_location
        )
        if focus_city:
            try:
                get_weather(focus_city, lang=_current_language)
            except (ValueError, ConnectionError):
                pass

    yield from _stream_chunks(final_text)


_GENEL_ONERILER = [
    "Bulunduğum yerde bugün hava nasıl?",
    "Yakınımda ne yapabilirim?",
    "What's the weather like near me today?",
    "Recommend something to do nearby",
]


def generate_location_suggestions(city: str, country: str, weather: dict) -> list[str]:
    try:
        lang_instruction = "Türkçe yaz." if country == "TR" else "Write in English."
        sys_msg = (
            f"You are generating example prompts that a USER would type to a weather-based activity assistant. "
            f"Generate exactly 4 short prompts written from the USER's perspective (first person), "
            f"as if the user is asking the AI for recommendations or information. "
            f"City: {city}. Current weather: {weather.get('temperature', '?')}°C, {weather.get('condition', '')}. "
            f"{lang_instruction} "
            f"Each prompt must be max 60 characters, sound natural, and be city/weather specific. "
            f"Examples of the correct style: 'Bugün İstanbul'da ne yapabilirim?', 'Kâğıthane'de akşam aktiviteleri öner'. "
            f"Output only the 4 prompts, one per line, no numbering, no bullet points."
        )
        response = react_llm.invoke(
            [SystemMessage(content=sys_msg), HumanMessage(content="Generate suggestions.")],
            config={"max_tokens": 250},
        )
        lines = [l.strip().strip('"').strip("'") for l in (response.content or "").split("\n") if l.strip()]
        suggestions = [l for l in lines if l][:4]
        if len(suggestions) < 4:
            return _GENEL_ONERILER
        return suggestions
    except Exception:
        return _GENEL_ONERILER


def generate_next_suggestion(history: list[dict]) -> tuple[str, str]:
    """Konuşma bağlamına göre (placeholder_hint, full_suggestion) döndürür.

    Hata durumunda ("", "") döner; uygulama etkilenmez.
    """
    try:
        lang = _current_language
        recent = [m for m in history if not m.get("content", "").startswith('<div class="typing')]
        tail = recent[-4:] if len(recent) >= 4 else recent
        if not tail:
            return "", ""

        convo_lines = []
        for m in tail:
            role = "Kullanıcı" if m["role"] == "user" else "Asistan"
            text = (m.get("content") or "")[:300]
            convo_lines.append(f"{role}: {text}")
        convo_text = "\n".join(convo_lines)

        if lang == "tr":
            sys_msg = (
                "Aşağıdaki konuşmaya bakarak, kullanıcının bir hava durumu aktivite asistanına "
                "yazacağı TAM OLARAK BİR follow-up mesaj üret. "
                "Mesaj kullanıcı bakış açısından olmalı (örn: 'Yakınımda kafe öner', 'Yarın hava nasıl olacak?'). "
                "AI'ın kullanıcıya sorduğu sorular değil, kullanıcının AI'a yazdığı prompt tarzında olmalı. "
                "Sadece mesajı yaz, başka hiçbir şey ekleme. Maksimum 80 karakter. Türkçe yaz."
            )
        else:
            sys_msg = (
                "Given the conversation below, generate EXACTLY ONE follow-up message "
                "that the USER would type to a weather-based activity assistant. "
                "Write it from the user's perspective (e.g. 'Recommend a cafe nearby', 'What about tomorrow?'). "
                "Not a question the AI asks, but a prompt the user sends. "
                "Output only the message, nothing else. Maximum 80 characters. Write in English."
            )

        response = react_llm.invoke(
            [SystemMessage(content=sys_msg), HumanMessage(content=convo_text)],
            config={"max_tokens": 80},
        )
        suggestion = (response.content or "").strip().strip('"').strip("'")
        if not suggestion:
            return "", ""
        hint = suggestion[:55] + (" ↹" if len(suggestion) <= 55 else "… ↹")
        return hint, suggestion
    except Exception:
        return "", ""


def _fallback_title(text: str) -> str:
    """LLM başlık üretemezse ilk mesajdan kısa bir başlık türetir."""
    clean = " ".join((text or "").split())
    if not clean:
        return "Yeni Sohbet"
    return clean[:40].rstrip() + ("…" if len(clean) > 40 else "")


def generate_session_title(first_user_msg: str, lang: str = "tr") -> str:
    """İlk kullanıcı mesajından 3-5 kelimelik kısa bir session başlığı üretir.

    Hata durumunda mesajın ilk ~40 karakterine düşer.
    """
    msg = (first_user_msg or "").strip()
    if not msg:
        return "Yeni Sohbet"
    try:
        if lang == "tr":
            sys_content = (
                "Aşağıdaki kullanıcı mesajı için 3-5 kelimelik kısa, açıklayıcı bir "
                "başlık üret (tırnak, noktalama ve emoji olmadan). Sadece başlığı yaz."
            )
        else:
            sys_content = (
                "Generate a short 3-5 word descriptive title for the user message below "
                "(no quotes, punctuation, or emoji). Output only the title."
            )
        raw = evaluator_llm.invoke(
            [SystemMessage(content=sys_content), HumanMessage(content=msg[:400])],
            config={"max_tokens": 20},
        ).content
        title = " ".join((raw or "").split()).strip().strip('"').strip("'")
        if not title:
            return _fallback_title(msg)
        return title[:60]
    except Exception:
        return _fallback_title(msg)
