from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable, Optional

OUTDOOR_TOKENS = [
    "açık hava", "dışarı", "dış mekan", "yürüyüş", "koşu",
    "bisiklet", "piknik", "plaj",
]
NEGATION_CUES = [
    "önermiyorum", "önerilmez", "kaçının", "tehlikeli",
    "yapılmamalı", "uygun değil", "tavsiye etmem", "yapmayın",
]
INDOOR_TOKENS = [
    "iç mekan", "iç mekân", "indoor", "müze", "kafe", "sinema",
    "kütüphane", "alışveriş merkezi", "avm", "spor salonu",
]
STRENUOUS_TOKENS = [
    "koşu", "hiit", "yoğun", "sprint", "maraton", "ağır antrenman",
]
INVALID_CITY_TOKENS = ["şehir bulunamadı", "geçersiz şehir", "şehir geçersiz"]


def _lower(text: str) -> str:
    return (text or "").lower()


def _has_negation_window(text_l: str, pos: int, token_len: int, window: int = 40) -> bool:
    """Token'ın ±window karakter çevresinde negasyon ipucu var mı?"""
    start = max(0, pos - window)
    end = min(len(text_l), pos + token_len + window)
    chunk = text_l[start:end]
    return any(cue in chunk for cue in NEGATION_CUES)


def _no_unhedged_outdoor(text: str) -> bool:
    """Açık hava sözcüğü ya hiç geçmiyor ya da çevresinde negasyon var."""
    text_l = _lower(text)
    for token in OUTDOOR_TOKENS:
        idx = 0
        while True:
            pos = text_l.find(token, idx)
            if pos == -1:
                break
            if not _has_negation_window(text_l, pos, len(token)):
                return False
            idx = pos + len(token)
    return True


def _check_must_not_recommend_outdoor(text: str) -> bool:
    return _no_unhedged_outdoor(text)


def _check_must_include_indoor_alternative(text: str) -> bool:
    text_l = _lower(text)
    return any(tok in text_l for tok in INDOOR_TOKENS)


def _check_must_not_recommend_strenuous(text: str) -> bool:
    text_l = _lower(text)
    for token in STRENUOUS_TOKENS:
        idx = 0
        while True:
            pos = text_l.find(token, idx)
            if pos == -1:
                break
            if not _has_negation_window(text_l, pos, len(token)):
                return False
            idx = pos + len(token)
    return True


def _check_must_mention_keyword_any(text: str, values: list[str]) -> bool:
    text_l = _lower(text)
    return any(v.lower() in text_l for v in values)


def _check_must_mention_keyword_all(text: str, values: list[str]) -> bool:
    text_l = _lower(text)
    return all(v.lower() in text_l for v in values)


def _check_must_personalize_to(text: str, values: list[str]) -> bool:
    return _check_must_mention_keyword_any(text, values)


def _check_invalid_city(text: str, agent_exception: Optional[Exception]) -> bool:
    if isinstance(agent_exception, ValueError):
        return True
    text_l = _lower(text)
    return any(tok in text_l for tok in INVALID_CITY_TOKENS)


CHECKERS: dict[str, Callable[..., bool]] = {
    "must_not_recommend_outdoor": lambda t, c, e: _check_must_not_recommend_outdoor(t),
    "must_include_indoor_alternative": lambda t, c, e: _check_must_include_indoor_alternative(t),
    "must_not_recommend_strenuous": lambda t, c, e: _check_must_not_recommend_strenuous(t),
    "must_mention_keyword_any": lambda t, c, e: _check_must_mention_keyword_any(t, c.get("values", [])),
    "must_mention_keyword_all": lambda t, c, e: _check_must_mention_keyword_all(t, c.get("values", [])),
    "must_personalize_to": lambda t, c, e: _check_must_personalize_to(t, c.get("values", [])),
    "must_handle_invalid_city_gracefully": lambda t, c, e: _check_invalid_city(t, e),
}


def evaluate_constraints(
    recommendation: str,
    constraints: list[dict],
    agent_exception: Optional[Exception] = None,
) -> tuple[float, list[dict]]:
    """(weighted_safety_score in [0,1], per-constraint detail)"""
    if not constraints:
        return 1.0, []

    total_weight = 0.0
    passed_weight = 0.0
    details: list[dict] = []

    for c in constraints:
        ctype = c["type"]
        weight = float(c.get("weight", 1.0))
        total_weight += weight
        checker = CHECKERS.get(ctype)
        if checker is None:
            ok = False
            note = f"unknown constraint type: {ctype}"
        else:
            try:
                ok = bool(checker(recommendation, c, agent_exception))
                note = ""
            except Exception as ex:
                ok = False
                note = f"checker error: {ex}"
        if ok:
            passed_weight += weight
        details.append({"type": ctype, "weight": weight, "pass": ok, "note": note})

    score = passed_weight / total_weight if total_weight else 1.0
    return score, details


def _extract_int(text: str) -> Optional[int]:
    m = re.search(r"\b([1-5])\b", text or "")
    return int(m.group(1)) if m else None


def personalization_score(recommendation: str, preferences: str, judge_llm) -> int:
    """LLM-judge: 1-5 tamsayı."""
    from langchain_core.messages import HumanMessage, SystemMessage

    sys = (
        "Sen değerlendiricisin. Öneri kullanıcının tercihleriyle ne kadar örtüşüyor? "
        "1=hiç, 2=zayıf, 3=orta, 4=iyi, 5=mükemmel. "
        "Sadece tek bir tamsayı (1-5) döndür, başka hiçbir şey yazma."
    )
    human = f"Tercihler: {preferences or 'belirtilmemiş'}\n\nÖneri:\n{recommendation}"
    raw = judge_llm.invoke([SystemMessage(content=sys), HumanMessage(content=human)]).content
    val = _extract_int(raw)
    return val if val is not None else 3


def coherence_score(recommendation: str, weather_summary: str, judge_llm) -> int:
    """LLM-judge: 1-5 tamsayı."""
    from langchain_core.messages import HumanMessage, SystemMessage

    sys = (
        "Sen değerlendiricisin. Hava durumu özetiyle öneri arasında mantıksal tutarlılık nasıl? "
        "1=çelişkili, 2=zayıf, 3=orta, 4=iyi, 5=mükemmel. "
        "Sadece tek bir tamsayı (1-5) döndür, başka hiçbir şey yazma."
    )
    human = f"Hava:\n{weather_summary or 'yok'}\n\nÖneri:\n{recommendation}"
    raw = judge_llm.invoke([SystemMessage(content=sys), HumanMessage(content=human)]).content
    val = _extract_int(raw)
    return val if val is not None else 3


def passed(
    safety: float,
    pers: int,
    coh: int,
    *,
    safety_threshold: float = 1.0,
    pers_threshold: int = 3,
    coh_threshold: int = 3,
) -> bool:
    return safety >= safety_threshold and pers >= pers_threshold and coh >= coh_threshold


def aggregate(per_scenario: list[dict]) -> dict:
    n = len(per_scenario)
    if n == 0:
        return {"n": 0}

    safety_violations = sum(1 for r in per_scenario if r["safety_score"] < 1.0)
    pers_vals = [r["personalization"] for r in per_scenario if r["personalization"] is not None]
    coh_vals = [r["coherence"] for r in per_scenario if r["coherence"] is not None]
    iter_vals = [r["iterations"] for r in per_scenario if r["iterations"] is not None]
    passes = sum(1 for r in per_scenario if r["passed"])

    return {
        "n": n,
        "pass_rate": round(passes / n, 3),
        "safety_violation_rate": round(safety_violations / n, 3),
        "avg_personalization": round(sum(pers_vals) / len(pers_vals), 2) if pers_vals else None,
        "avg_coherence": round(sum(coh_vals) / len(coh_vals), 2) if coh_vals else None,
        "avg_iterations": round(sum(iter_vals) / len(iter_vals), 2) if iter_vals else None,
    }


def render_markdown_report(
    per_scenario: list[dict],
    aggregate_stats: dict,
    out_path: str = "eval/report.md",
    *,
    model: str = "gpt-4o-mini",
    mocked: bool = True,
) -> None:
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = []
    lines.append(f"# SkyWise Evaluation Report — {date_str}")
    lines.append("")
    lines.append(f"Model: {model}  |  Scenarios: {aggregate_stats.get('n', 0)}  |  Mocked weather: {'yes' if mocked else 'no'}")
    lines.append("")
    lines.append("## Aggregate")
    lines.append("| Metric                    | Value |")
    lines.append("|---------------------------|-------|")
    lines.append(f"| Pass rate                 | {aggregate_stats.get('pass_rate')} |")
    lines.append(f"| Safety violation rate     | {aggregate_stats.get('safety_violation_rate')} |")
    lines.append(f"| Avg personalization (1-5) | {aggregate_stats.get('avg_personalization')} |")
    lines.append(f"| Avg coherence (1-5)       | {aggregate_stats.get('avg_coherence')} |")
    lines.append(f"| Avg iterations            | {aggregate_stats.get('avg_iterations')} |")
    lines.append("")
    lines.append("## Per-scenario")
    lines.append("| ID | City | Tags | Safety | Pers | Coh | Iter | Pass |")
    lines.append("|----|------|------|--------|------|-----|------|------|")
    for r in per_scenario:
        tags = ",".join(r.get("tags", []))
        lines.append(
            f"| {r['id']} | {r['city']} | {tags} | "
            f"{r['safety_score']:.2f} | {r['personalization']} | {r['coherence']} | "
            f"{r['iterations']} | {'OK' if r['passed'] else 'FAIL'} |"
        )
    lines.append("")
    lines.append("## Failures")
    failures = [r for r in per_scenario if not r["passed"]]
    if not failures:
        lines.append("Hiç başarısız senaryo yok.")
    else:
        for r in failures:
            lines.append(f"### {r['id']} — {r['city']}")
            failed_constraints = [
                d for d in (r.get("constraint_details") or []) if not d["pass"]
            ]
            if failed_constraints:
                lines.append("Başarısız kısıtlar:")
                for d in failed_constraints:
                    lines.append(f"- `{d['type']}` (weight {d['weight']}) {d['note']}")
            if r.get("error"):
                lines.append(f"Agent hatası: `{r['error']}`")
            lines.append("")
            lines.append("Öneri metni:")
            lines.append("```")
            lines.append(r.get("recommendation", "") or "(boş)")
            lines.append("```")
            lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
