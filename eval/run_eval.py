"""SkyWise eval CLI.

Usage:
  python -m eval.run_eval
  python -m eval.run_eval --ids S01,S07,S24
  python -m eval.run_eval --no-mock
  python -m eval.run_eval --out eval/report.md
  python -m eval.run_eval --judge-model gpt-4o-mini
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

import weather_tool  # noqa: E402
from agent import run_skywise_traced  # noqa: E402
from eval.metrics import (  # noqa: E402
    aggregate,
    coherence_score,
    evaluate_constraints,
    passed,
    personalization_score,
    render_markdown_report,
)
from eval.mock_weather import MockWeatherProvider  # noqa: E402

load_dotenv()


def load_scenarios(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_mock_provider(scenarios: list[dict]) -> MockWeatherProvider:
    overrides: dict[str, dict] = {}
    for s in scenarios:
        if s.get("weather_override"):
            overrides[s["city"]] = s["weather_override"]
    return MockWeatherProvider(overrides)


def run_one(scenario: dict, judge_llm) -> dict:
    city = scenario["city"]
    prefs = scenario.get("preferences", "")
    constraints = scenario.get("expected_constraints", [])

    error: str | None = None
    agent_exception: Exception | None = None
    final_state: dict = {}
    recommendation = ""

    try:
        final_state = run_skywise_traced(city, prefs)
        recommendation = final_state.get("recommendation", "") or ""
    except Exception as ex:
        agent_exception = ex
        error = f"{type(ex).__name__}: {ex}"

    safety_score, details = evaluate_constraints(
        recommendation, constraints, agent_exception
    )

    if agent_exception is not None or not recommendation:
        pers = 0
        coh = 0
    else:
        try:
            pers = personalization_score(recommendation, prefs, judge_llm)
        except Exception as ex:
            pers = 3
            error = (error or "") + f" | personalization judge error: {ex}"
        try:
            coh = coherence_score(
                recommendation, final_state.get("weather_summary", ""), judge_llm
            )
        except Exception as ex:
            coh = 3
            error = (error or "") + f" | coherence judge error: {ex}"

    iterations = final_state.get("iteration", 0)

    is_pass = passed(safety_score, pers, coh) if recommendation else (
        # Invalid-city scenarios pass purely on safety constraint.
        safety_score >= 1.0 and any(
            c["type"] == "must_handle_invalid_city_gracefully" for c in constraints
        )
    )

    return {
        "id": scenario["id"],
        "city": city,
        "preferences": prefs,
        "tags": scenario.get("tags", []),
        "recommendation": recommendation,
        "iterations": iterations,
        "safety_score": safety_score,
        "personalization": pers,
        "coherence": coh,
        "passed": is_pass,
        "constraint_details": details,
        "error": error,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="SkyWise eval runner")
    parser.add_argument("--scenarios", default=str(REPO_ROOT / "eval" / "scenarios.json"))
    parser.add_argument("--ids", default="", help="virgülle ayrık alt küme, örn. S01,S07")
    parser.add_argument("--no-mock", action="store_true", help="gerçek OWM API'yi kullan")
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "report.md"))
    parser.add_argument("--judge-model", default="gpt-4o-mini")
    args = parser.parse_args()

    scenarios = load_scenarios(args.scenarios)

    if args.ids:
        wanted = {s.strip() for s in args.ids.split(",") if s.strip()}
        scenarios = [s for s in scenarios if s["id"] in wanted]

    use_mock = not args.no_mock
    if use_mock:
        provider = build_mock_provider(scenarios)
        weather_tool.set_weather_provider(provider)

    judge_llm = ChatOpenAI(
        model=args.judge_model,
        temperature=0.0,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    per_scenario: list[dict] = []
    for s in scenarios:
        try:
            rec = run_one(s, judge_llm)
        except Exception:
            traceback.print_exc()
            rec = {
                "id": s["id"], "city": s["city"], "preferences": s.get("preferences", ""),
                "tags": s.get("tags", []), "recommendation": "", "iterations": 0,
                "safety_score": 0.0, "personalization": 0, "coherence": 0,
                "passed": False, "constraint_details": [],
                "error": "unhandled error in run_one",
            }
        print(
            f"[{rec['id']}] {rec['city']:<14} "
            f"safety={rec['safety_score']:.2f} pers={rec['personalization']} "
            f"coh={rec['coherence']} iter={rec['iterations']} "
            f"{'OK' if rec['passed'] else 'FAIL'}"
        )
        per_scenario.append(rec)

    agg = aggregate(per_scenario)
    render_markdown_report(
        per_scenario, agg, out_path=args.out, mocked=use_mock,
    )

    print()
    print("=== AGGREGATE ===")
    for k, v in agg.items():
        print(f"  {k}: {v}")
    print(f"\nReport saved to: {args.out}")


if __name__ == "__main__":
    main()
