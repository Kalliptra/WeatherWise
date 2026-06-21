"""Redis-backed cache (Upstash) — aynı gün TTL, in-memory L1.

Env vars gerekli:
  UPSTASH_REDIS_REST_URL
  UPSTASH_REDIS_REST_TOKEN

Her ikisi de yoksa sadece in-memory çalışır (HF dışı geliştirme için).
SKYWISE_NO_CACHE=1 ile tamamen devre dışı bırakılabilir.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime
from typing import Any, Callable

CACHE_DISABLED = os.getenv("SKYWISE_NO_CACHE") == "1"

_lock = threading.Lock()
_store: dict[str, dict] = {}  # L1 in-memory cache
_redis = None
_redis_init = False


def _get_redis():
    global _redis, _redis_init
    if _redis_init:
        return _redis
    _redis_init = True
    url = os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if url and token:
        try:
            from upstash_redis import Redis
            _redis = Redis(url=url, token=token)
        except Exception:
            _redis = None
    return _redis


def _today() -> str:
    return date.today().isoformat()


def _seconds_until_midnight() -> int:
    now = datetime.now()
    midnight = datetime(now.year, now.month, now.day, 23, 59, 59)
    return max(int((midnight - now).total_seconds()), 1)


def get_or_fetch(key: tuple[str, ...], fetch_fn: Callable[[], Any], ttl_same_day: bool = True) -> Any:
    """Cache'den döner; yoksa fetch_fn() çağırır, sonucu kaydeder."""
    if CACHE_DISABLED:
        return fetch_fn()

    cache_key = "|".join(key)
    today = _today()

    # L1: in-memory
    with _lock:
        entry = _store.get(cache_key)
        if entry and (not ttl_same_day or entry.get("date") == today):
            return entry["data"]

    # L2: Redis
    r = _get_redis()
    if r:
        try:
            raw = r.get(cache_key)
            if raw:
                entry = json.loads(raw) if isinstance(raw, str) else raw
                if not ttl_same_day or entry.get("date") == today:
                    with _lock:
                        _store[cache_key] = entry
                    return entry["data"]
        except Exception:
            pass

    data = fetch_fn()
    entry = {"date": today, "data": data}

    with _lock:
        _store[cache_key] = entry

    if r:
        try:
            ttl = _seconds_until_midnight() if ttl_same_day else 86400
            r.set(cache_key, json.dumps(entry, ensure_ascii=False), ex=ttl)
        except Exception:
            pass

    return data


def clear_cache() -> None:
    global _store
    with _lock:
        _store = {}
