"""Aktivite önerisini takvime aktarma — bağımlılıksız .ics (iCalendar) üretimi.

Sohbet akışı yapısal bir itinerary üretmediğinden, asistanın görünür öneri metninden
LLM ile (hafıza modülündeki JSON-çıkarım kalıbı) zamanlı etkinlikler çıkarılır ve
standart bir VCALENDAR metnine çevrilir. Üretilen .ics dosyası Google/Apple/Outlook
takvimlerinin tümü tarafından içe aktarılabilir.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from typing import Optional


def _escape(text: str) -> str:
    """iCalendar metin kaçışı (RFC 5545): ters bölü, virgül, noktalı virgül, yeni satır."""
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


def _parse_hhmm(s) -> Optional[tuple[int, int]]:
    """'HH:MM' → (saat, dakika); geçersizse None."""
    if not isinstance(s, str):
        return None
    parts = s.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if 0 <= h <= 23 and 0 <= m <= 59:
        return h, m
    return None


def extract_events(assistant_text: str, lang: str = "tr") -> list[dict]:
    """Asistanın öneri metninden zamanlı etkinlik listesi çıkarır (LLM-JSON).

    Döner: [{"title", "start", "end", "location", "day_offset"}, ...].
    Hata/anahtarsız durumda boş liste döner (çağıran tarafta uyarı gösterilir).
    """
    text = (assistant_text or "").strip()
    if not text:
        return []
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from core.llms import evaluator_llm

        if lang == "en":
            sys_content = (
                "Extract a short calendar plan from the activity suggestion below. "
                "Return ONLY this JSON:\n"
                '{"events": [{"title": "...", "start": "HH:MM", "end": "HH:MM", '
                '"location": "...", "day_offset": 0}, ...]}\n'
                "Rules: 1 to 4 events. Each needs a concrete title and 24h start/end times. "
                "If the text gives a best time/hour, use it; otherwise assign a sensible time. "
                "location = venue/place name if mentioned, else empty string. "
                "day_offset = 0 for today, 1 for tomorrow, etc. (only if the text clearly targets a "
                "future day, else 0). Output only JSON, nothing else."
            )
        else:
            sys_content = (
                "Aşağıdaki aktivite önerisinden kısa bir takvim planı çıkar. "
                "Yalnızca şu JSON'u döndür:\n"
                '{"events": [{"title": "...", "start": "HH:MM", "end": "HH:MM", '
                '"location": "...", "day_offset": 0}, ...]}\n'
                "Kurallar: 1–4 etkinlik. Her birinde somut başlık ve 24 saatlik başlangıç/bitiş "
                "saati olsun. Metinde en uygun saat/aralık verildiyse onu kullan; yoksa mantıklı bir "
                "saat ata. location = belirtilmişse mekan adı, yoksa boş string. day_offset = bugün için "
                "0, yarın için 1 vb. (yalnızca metin açıkça ileri bir günü hedefliyorsa, aksi halde 0). "
                "Yalnızca JSON döndür, başka hiçbir şey yazma."
            )

        raw = evaluator_llm.invoke([
            SystemMessage(content=sys_content),
            HumanMessage(content=text[:2000]),
        ]).content.strip()

        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            return []
        parsed = json.loads(raw[start:end])
        events = parsed.get("events", [])
        return [e for e in events if isinstance(e, dict) and (e.get("title") or "").strip()][:4]
    except Exception:
        return []


def build_ics(events: list[dict], base_date_iso: Optional[str] = None) -> str:
    """Etkinlik listesini standart bir VCALENDAR (.ics) metnine çevirir.

    Saatler 'kayan' yerel saat olarak yazılır (TZID yok) — kişisel takvim içe aktarımında
    cihazın yerel saatine göre yorumlanır. Geçersiz/zamansız etkinlikler atlanır.
    """
    base = date.fromisoformat(base_date_iso) if base_date_iso else date.today()
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SkyWise//Activity Planner//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    count = 0
    for ev in events:
        start = _parse_hhmm(ev.get("start"))
        if not start:
            continue
        end = _parse_hhmm(ev.get("end"))
        try:
            offset = int(ev.get("day_offset", 0) or 0)
        except (TypeError, ValueError):
            offset = 0
        offset = max(0, min(offset, 14))

        day = base + timedelta(days=offset)
        start_dt = datetime(day.year, day.month, day.day, start[0], start[1])
        if end:
            end_dt = datetime(day.year, day.month, day.day, end[0], end[1])
            if end_dt <= start_dt:
                end_dt = start_dt + timedelta(minutes=90)
        else:
            end_dt = start_dt + timedelta(minutes=90)

        title = _escape(str(ev.get("title", "")).strip())
        location = _escape(str(ev.get("location", "")).strip())

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4().hex}@skywise",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{title}",
        ]
        if location:
            lines.append(f"LOCATION:{location}")
        lines.append("DESCRIPTION:" + _escape("SkyWise — hava durumuna göre aktivite planı"))
        lines.append("END:VEVENT")
        count += 1

    lines.append("END:VCALENDAR")
    if count == 0:
        return ""
    # RFC 5545 satır sonu CRLF
    return "\r\n".join(lines) + "\r\n"
