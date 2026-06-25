"""Anonim kullanıcı hafızası — Upstash Redis'te anon_id bazlı, LLM destekli tercih çıkarımı.

Giriş/kullanıcı kavramı yoktur; her şey tarayıcıdaki localStorage anon_id ile çalışır.
anon_id sağlanmadıysa tüm hafıza işlemleri no-op olarak davranır; cache (hava/mekan)
her durumda çalışmaya devam eder. Anon hafıza session'larla aynı TTL ile tutulur ve her
yazımda yenilenir.
"""

from __future__ import annotations

import json
import threading
from datetime import date
from typing import Optional

from dotenv import load_dotenv

# .env'i import sırasında yükle — Redis env'leri başka bir modülün önce import
# edilmesine bağlı kalmadan her zaman mevcut olsun.
load_dotenv()

MAX_CONVERSATIONS = 10

# Anonim hafıza için TTL (saniye). Her yazımda yenilenir (sessions ile aynı).
ANON_TTL = 86400  # 24 saat

_lock = threading.Lock()
_cache: dict[str, dict] = {}  # {anon_id: memory_data}


def _memory_key(anon_id: Optional[str]) -> Optional[str]:
    return f"skywise:anon:{anon_id}" if anon_id else None


def _get_redis():
    import os
    url = os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        return None
    try:
        from upstash_redis import Redis
        return Redis(url=url, token=token)
    except Exception:
        return None


def load_memory(anon_id: Optional[str] = None) -> dict:
    """Anonim hafızayı yükler. anon_id yoksa boş dict döner."""
    key = _memory_key(anon_id)
    if not key:
        return {}

    with _lock:
        if anon_id in _cache:
            return dict(_cache[anon_id])

    r = _get_redis()
    if r:
        try:
            raw = r.get(key)
            if raw:
                data = json.loads(raw) if isinstance(raw, str) else raw
                with _lock:
                    _cache[anon_id] = data
                return dict(data)
        except Exception:
            pass

    return {}


def save_memory(anon_id: Optional[str], data: dict) -> None:
    """Anonim hafızayı kaydeder. anon_id yoksa no-op. TTL her yazımda yenilenir."""
    key = _memory_key(anon_id)
    if not key:
        return

    with _lock:
        _cache[anon_id] = dict(data)

    r = _get_redis()
    if r:
        try:
            r.set(key, json.dumps(data, ensure_ascii=False), ex=ANON_TTL)
        except Exception:
            pass


def format_memory_block(memory: dict, lang: str = "tr") -> str:
    """Hafızayı sistem promptuna eklenecek metin bloğuna dönüştürür."""
    if not memory:
        return ""

    prefs = memory.get("preferences", {})
    liked = prefs.get("liked", [])
    disliked = prefs.get("disliked", [])
    notes = prefs.get("notes", "")
    cities = memory.get("favorite_cities", [])
    conversations = memory.get("conversations", [])

    if not liked and not disliked and not notes and not cities and not conversations:
        return ""

    parts = []
    if lang == "tr":
        parts.append("## Kullanıcı Hafızası")
        if liked:
            parts.append(f"Sevdiği aktiviteler: {', '.join(liked)}")
        if disliked:
            parts.append(f"Sevmediği aktiviteler: {', '.join(disliked)}")
        if notes:
            parts.append(f"Notlar: {notes}")
        if cities:
            parts.append(f"Ziyaret ettiği şehirler: {', '.join(cities[:5])}")
        if conversations:
            parts.append("Son konuşmalar:")
            for c in conversations[-3:]:
                city_str = f" ({c['city']})" if c.get("city") else ""
                parts.append(f"  - {c.get('date', '')}{city_str}: {c.get('summary', '')}")
        parts.append(
            "Bu bilgileri önerilerinde kullan. Kayıtlı tercih kategorilerine göre öne "
            "çıkardığını belirtebilirsin (örn. 'Önceki beğenilerine göre [kategori] ağırlıklı "
            "önerdim'). Ancak geçmiş konuşma içeriğine ('geçen sefer şöyle demiştin') atıf yapma."
        )
    else:
        parts.append("## User Memory")
        if liked:
            parts.append(f"Liked activities: {', '.join(liked)}")
        if disliked:
            parts.append(f"Disliked activities: {', '.join(disliked)}")
        if notes:
            parts.append(f"Notes: {notes}")
        if cities:
            parts.append(f"Cities visited: {', '.join(cities[:5])}")
        if conversations:
            parts.append("Recent conversations:")
            for c in conversations[-3:]:
                city_str = f" ({c['city']})" if c.get("city") else ""
                parts.append(f"  - {c.get('date', '')}{city_str}: {c.get('summary', '')}")
        parts.append(
            "Use this to personalize suggestions. You may state that you prioritized based on "
            "saved preference categories (e.g. 'Based on your preferences, I focused on [category]'). "
            "But do not reference past conversation content ('last time you said...')."
        )

    return "\n".join(parts)


def get_activity_preferences(anon_id: Optional[str]) -> list[str]:
    """Anonim kullanıcının kayıtlı aktivite tercihlerini döner. anon_id yoksa boş liste."""
    return load_memory(anon_id).get("preferences", {}).get("liked", [])


def update_activity_preferences(
    anon_id: Optional[str], categories: list[str], replace: bool = False
) -> None:
    """Aktivite tercihlerini doğrudan günceller (LLM çıkarımı gereksiz).

    replace=True ise mevcut listeyi siler ve yenisiyle değiştirir.
    """
    if not anon_id:
        return
    memory = load_memory(anon_id)
    prefs = memory.setdefault("preferences", {"liked": [], "disliked": [], "notes": ""})
    if replace:
        prefs["liked"] = [c for c in categories if c]
    else:
        for cat in categories:
            if cat and cat not in prefs["liked"]:
                prefs["liked"].append(cat)
    save_memory(anon_id, memory)


def apply_feedback(
    anon_id: Optional[str], assistant_text: str, liked: bool, lang: str = "tr"
) -> None:
    """Bir öneri mesajına verilen 👍/👎 geri bildirimini hafızaya işler.

    assistant_text'ten ana aktivite kategorilerini LLM ile çıkarır:
    - liked=True  → kategoriler "liked"e taşınır, "disliked"ten çıkarılır.
    - liked=False → kategoriler "disliked"e taşınır, "liked"ten çıkarılır.

    anon_id yoksa no-op. Hata durumunda sessizce çıkar. Arka plan thread'inde çağrılmalı.
    """
    if not anon_id or not (assistant_text or "").strip():
        return

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from core.llms import evaluator_llm

        if lang == "en":
            sys_content = (
                "Extract the main activity categories from the assistant message below "
                "(e.g. running, museum, cafe, hiking, beach, sports). Return only this JSON:\n"
                '{"categories": ["category", ...]}\n'
                "Use short, general category names. Return at most 3. Nothing else."
            )
        else:
            sys_content = (
                "Aşağıdaki asistan mesajından ana aktivite kategorilerini çıkar "
                "(örn. koşu, müze, kafe, yürüyüş, plaj, spor). Yalnızca şu JSON'u döndür:\n"
                '{"categories": ["kategori", ...]}\n'
                "Kısa, genel kategori adları kullan. En fazla 3 tane. Başka hiçbir şey yazma."
            )

        raw = evaluator_llm.invoke([
            SystemMessage(content=sys_content),
            HumanMessage(content=assistant_text[:1500]),
        ]).content.strip()

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            return
        categories = [c for c in json.loads(raw[start:end]).get("categories", []) if c]
        if not categories:
            return

        memory = load_memory(anon_id)
        prefs = memory.setdefault("preferences", {"liked": [], "disliked": [], "notes": ""})
        prefs.setdefault("liked", [])
        prefs.setdefault("disliked", [])

        add_to, remove_from = ("liked", "disliked") if liked else ("disliked", "liked")
        for cat in categories:
            prefs[remove_from] = [c for c in prefs[remove_from] if c != cat]
            if cat not in prefs[add_to]:
                prefs[add_to].append(cat)

        memory["language"] = lang
        save_memory(anon_id, memory)

    except Exception:
        pass


def _level_from(count: int, prefs: dict) -> dict:
    """Geri bildirim sayısı + kategori çeşitliliğinden seviye sözlüğü üretir.

    `count` (açık 👍/👎 sayısı) anlık güncellenen birincil sinyaldir; kategori
    çeşitliliği (liked+disliked) tabanı yükseltir, böylece onboarding sonrası
    rozet 0'da kalmaz. Seviye 1-5, ilerleme 0-100 arasıdır.
    """
    liked = prefs.get("liked", []) if prefs else []
    disliked = prefs.get("disliked", []) if prefs else []
    diversity = len(liked) + len(disliked)
    score = max(count, diversity)
    level = min(5, 1 + score // 2) if score else 0
    pct = min(100, score * 20)
    return {
        "count": count,
        "level": level,
        "pct": pct,
        "liked": liked,
        "disliked": disliked,
    }


def record_feedback(anon_id: Optional[str], liked: bool) -> dict:
    """Açık 👍/👎 tıklamasını anlık (LLM beklemeden) sayaca işler ve güncel seviyeyi döner.

    Kategori çıkarımı `apply_feedback` ile arka planda ayrıca yapılır; bu fonksiyon
    yalnızca sayaçları artırıp rozetin hemen güncellenmesini sağlar. anon_id yoksa
    boş seviye döner.
    """
    if not anon_id:
        return _level_from(0, {})
    memory = load_memory(anon_id)
    memory["feedback_count"] = int(memory.get("feedback_count", 0)) + 1
    key = "liked_count" if liked else "disliked_count"
    memory[key] = int(memory.get(key, 0)) + 1
    save_memory(anon_id, memory)
    return _level_from(memory["feedback_count"], memory.get("preferences", {}))


def get_personalization_level(anon_id: Optional[str]) -> dict:
    """Kullanıcının güncel kişiselleştirme seviyesini döner. anon_id yoksa boş seviye."""
    memory = load_memory(anon_id) if anon_id else {}
    return _level_from(int(memory.get("feedback_count", 0)), memory.get("preferences", {}))


def extract_and_update(
    messages: list[dict],
    city: Optional[str],
    lang: str,
    anon_id: Optional[str] = None,
) -> None:
    """Konuşmadan tercih çıkar ve hafızayı güncelle. Arka planda thread olarak çalışır.

    anon_id yoksa erken çıkar.
    """
    if not anon_id:
        return

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from core.llms import evaluator_llm

        tail = messages[-6:] if len(messages) > 6 else messages
        convo = "\n".join(
            f"{'Kullanıcı' if m['role'] == 'user' else 'Asistan'}: {(m.get('content') or '')[:400]}"
            for m in tail
        )

        if lang == "tr":
            sys_content = (
                "Aşağıdaki konuşmayı analiz et ve yalnızca şu JSON'u döndür:\n"
                '{"liked": ["sevilen aktiviteler"], "disliked": ["sevilmeyen aktiviteler"], '
                '"notes": "önemli tercih notu veya boş string", "summary": "tek cümle konuşma özeti"}\n'
                "liked/disliked listelerini sadece açıkça belirtilen veya güçlü biçimde ima edilen "
                "tercihlerle doldur; belirsizse boş bırak. Başka hiçbir şey yazma."
            )
        else:
            sys_content = (
                "Analyze the conversation below and return only this JSON:\n"
                '{"liked": ["liked activities"], "disliked": ["disliked activities"], '
                '"notes": "important preference note or empty string", "summary": "one-sentence summary"}\n'
                "Only fill liked/disliked with explicitly stated or strongly implied preferences; "
                "leave empty if unclear. Return nothing else."
            )

        raw = evaluator_llm.invoke([
            SystemMessage(content=sys_content),
            HumanMessage(content=convo),
        ]).content.strip()

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            return
        extracted = json.loads(raw[start:end])

        memory = load_memory(anon_id)
        prefs = memory.setdefault("preferences", {"liked": [], "disliked": [], "notes": ""})

        for item in extracted.get("liked", []):
            if item and item not in prefs["liked"]:
                prefs["liked"].append(item)
        for item in extracted.get("disliked", []):
            if item and item not in prefs["disliked"]:
                prefs["disliked"].append(item)
        if extracted.get("notes"):
            prefs["notes"] = extracted["notes"]

        if city:
            cities = memory.setdefault("favorite_cities", [])
            if city not in cities:
                cities.insert(0, city)
            memory["favorite_cities"] = cities[:10]

        summary = extracted.get("summary", "")
        if summary:
            convos = memory.setdefault("conversations", [])
            convos.append({
                "date": date.today().isoformat(),
                "city": city or "",
                "summary": summary,
            })
            memory["conversations"] = convos[-MAX_CONVERSATIONS:]

        memory["language"] = lang
        save_memory(anon_id, memory)

    except Exception:
        pass
