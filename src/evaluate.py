from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .answer import explain_call, law_number_from_label
from .settings import ROOT


EVAL_PATH = ROOT / "eval" / "scenarios.json"


def load_scenarios() -> list[dict[str, Any]]:
    return json.loads(EVAL_PATH.read_text())


def cited_laws(answer: dict[str, Any]) -> set[str]:
    laws: set[str] = set()
    for citation in answer.get("citations", []):
        law_number = law_number_from_label(citation.get("law", ""))
        if law_number:
            laws.add(law_number)
    return laws


def has_uncertainty(answer: dict[str, Any]) -> bool:
    return bool(answer.get("uncertainties"))


def score_scenario(scenario: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    expected = set(scenario["expected_laws"])
    actual = cited_laws(answer)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    uncertainty_ok = True
    if scenario.get("must_include_uncertainty"):
        uncertainty_ok = has_uncertainty(answer)

    passed = not missing and uncertainty_ok
    return {
        "id": scenario["id"],
        "passed": passed,
        "expected_laws": sorted(expected),
        "actual_laws": sorted(actual),
        "missing_laws": missing,
        "unexpected_laws": unexpected,
        "uncertainty_ok": uncertainty_ok,
        "confidence": answer.get("confidence"),
    }


def run_eval(limit: int | None = None) -> dict[str, Any]:
    scenarios = load_scenarios()
    if limit is not None:
        scenarios = scenarios[:limit]

    results = []
    for scenario in scenarios:
        answer = explain_call(scenario["incident"], scenario["call"])
        score = score_scenario(scenario, answer)
        score["answer"] = answer
        results.append(score)

    passed = sum(1 for result in results if result["passed"])
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }

