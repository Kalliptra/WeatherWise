"""Dosya bazlı JSON cache — aynı gün TTL, thread-safe."""

from __future__ import annotations

import json
import os
import threading
from datetime import date
from pathlib import Path
from typing import Any, Callable

CACHE_DISABLED = os.getenv("SKYWISE_NO_CACHE") == "1"

_CACHE_FILE = Path(__file__).parent.parent / "cache" / "skywise_cache.json"
_lock = threading.Lock()
_store: dict[str, dict] = {}


def _today() -> str:
    return date.today().isoformat()


def _load() -> None:
    global _store
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _CACHE_FILE.exists():
            _store = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        _store = {}


def _save() -> None:
    try:
        _CACHE_FILE.write_text(json.dumps(_store, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


_load()


def get_or_fetch(key: tuple[str, ...], fetch_fn: Callable[[], Any], ttl_same_day: bool = True) -> Any:
    """Cache'den döner; yoksa fetch_fn() çağırır, sonucu kaydeder."""
    if CACHE_DISABLED:
        return fetch_fn()

    cache_key = "|".join(key)
    today = _today()

    with _lock:
        entry = _store.get(cache_key)
        if entry and (not ttl_same_day or entry.get("date") == today):
            return entry["data"]

    data = fetch_fn()

    with _lock:
        _store[cache_key] = {"date": today, "data": data}
        _save()

    return data


def clear_cache() -> None:
    global _store
    with _lock:
        _store = {}
        _save()
