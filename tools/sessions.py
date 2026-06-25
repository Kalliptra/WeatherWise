"""Sohbet oturumları (session) — Upstash Redis'te kalıcı, anonim (anon_id) bazlı.

owner çözümü:
  - Anonim kullanıcı -> "anon:{anon_id}" (TTL var, geçici — 24 saat)

Giriş/kullanıcı kavramı yoktur; her şey tarayıcıdaki localStorage anon_id ile çalışır.
Redis yoksa modül içi bellek sözlüğüne düşer (yerel geliştirme). Hava/mekan cache'i
(tools/cache.py) bu modülden bağımsızdır ve session'lar arası paylaşılır.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

# .env'i import sırasında yükle — Redis env'leri başka bir modülün önce import
# edilmesine bağlı kalmadan her zaman mevcut olsun.
load_dotenv()

# Anonim session'lar için TTL (saniye). Her yazımda yenilenir.
ANON_TTL = 86400  # 24 saat

_lock = threading.Lock()
# Bellek fallback (Redis yoksa): {owner: {sid: data}}, {owner: [index_entry, ...]}
_mem: dict[str, dict[str, dict]] = {}
_mem_idx: dict[str, list[dict]] = {}


# ---- Anahtar / owner yardımcıları ----

def _owner(anon_id: Optional[str]) -> Optional[str]:
    """owner döndürür (anon:{anon_id}). Kimlik yoksa None."""
    if anon_id:
        return f"anon:{anon_id}"
    return None


def _idx_key(owner: str) -> str:
    return f"skywise:sess:idx:{owner}"


def _data_key(owner: str, sid: str) -> str:
    return f"skywise:sess:data:{owner}:{sid}"


def new_session_id() -> str:
    return uuid.uuid4().hex


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


# ---- Index okuma/yazma (düşük seviye) ----

def _read_index(owner: str, r) -> list[dict]:
    if r:
        try:
            raw = r.get(_idx_key(owner))
            if raw:
                data = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []
    with _lock:
        return [dict(e) for e in _mem_idx.get(owner, [])]


def _write_index(owner: str, index: list[dict], r) -> None:
    if r:
        try:
            r.set(_idx_key(owner), json.dumps(index, ensure_ascii=False), ex=ANON_TTL)
        except Exception:
            pass
        return
    with _lock:
        _mem_idx[owner] = [dict(e) for e in index]


def _sort_index(index: list[dict]) -> list[dict]:
    return sorted(index, key=lambda e: e.get("updated", ""), reverse=True)


# ---- Public API ----

def list_sessions(anon_id: Optional[str]) -> list[dict]:
    """Sidebar için session metadata listesi (updated'a göre yeniden eskiye)."""
    owner = _owner(anon_id)
    if not owner:
        return []
    r = _get_redis()
    return _sort_index(_read_index(owner, r))


def load_session(anon_id: Optional[str], sid: str) -> Optional[dict]:
    """Tam session verisini döndürür (messages + panel snapshot). Yoksa None."""
    owner = _owner(anon_id)
    if not owner or not sid:
        return None
    r = _get_redis()
    if r:
        try:
            raw = r.get(_data_key(owner, sid))
            if raw:
                return json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            pass
        return None
    with _lock:
        data = _mem.get(owner, {}).get(sid)
        return dict(data) if data else None


def save_session(
    anon_id: Optional[str],
    sid: str,
    *,
    messages: list[dict],
    panel: Optional[dict] = None,
    title: Optional[str] = None,
) -> None:
    """Session verisini yazar + index girişini (title/updated) günceller.

    Hem data hem index TTL ile yazılır (her yazımda yenilenir).
    """
    owner = _owner(anon_id)
    if not owner or not sid:
        return

    now = _now_iso()
    data = {
        "id": sid,
        "title": title or "",
        "messages": messages or [],
        "weather": (panel or {}).get("weather"),
        "venues": (panel or {}).get("venues") or [],
        "locations": (panel or {}).get("locations") or [],
        "focus_city": (panel or {}).get("focus_city") or "",
        "updated": now,
    }

    r = _get_redis()

    # data yaz
    if r:
        try:
            payload = json.dumps(data, ensure_ascii=False)
            r.set(_data_key(owner, sid), payload, ex=ANON_TTL)
        except Exception:
            pass
    else:
        with _lock:
            _mem.setdefault(owner, {})[sid] = dict(data)

    # index güncelle
    index = _read_index(owner, r)
    entry = next((e for e in index if e.get("id") == sid), None)
    if entry is None:
        entry = {"id": sid}
        index.append(entry)
    entry["title"] = data["title"]
    entry["updated"] = now
    _write_index(owner, index, r)


def delete_session(anon_id: Optional[str], sid: str) -> None:
    owner = _owner(anon_id)
    if not owner or not sid:
        return
    r = _get_redis()
    if r:
        try:
            r.delete(_data_key(owner, sid))
        except Exception:
            pass
    else:
        with _lock:
            _mem.get(owner, {}).pop(sid, None)

    index = [e for e in _read_index(owner, r) if e.get("id") != sid]
    _write_index(owner, index, r)


def rename_session(anon_id: Optional[str], sid: str, title: str) -> None:
    owner = _owner(anon_id)
    if not owner or not sid:
        return
    title = (title or "").strip()
    if not title:
        return
    r = _get_redis()

    # data başlığını güncelle
    data = load_session(anon_id, sid)
    if data:
        data["title"] = title
        if r:
            try:
                payload = json.dumps(data, ensure_ascii=False)
                r.set(_data_key(owner, sid), payload, ex=ANON_TTL)
            except Exception:
                pass
        else:
            with _lock:
                _mem.setdefault(owner, {})[sid] = dict(data)

    # index başlığını güncelle
    index = _read_index(owner, r)
    entry = next((e for e in index if e.get("id") == sid), None)
    if entry is not None:
        entry["title"] = title
        _write_index(owner, index, r)
