from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from .answer import explain_call, law_number_from_label
from .settings import EVAL_RUNS_DIR, ROOT


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


def model_slug(model: str) -> str:
    return (
        model.lower()
        .replace(":", "-")
        .replace("/", "-")
        .replace(".", "-")
        .replace("_", "-")
    )


def report_path(model: str, limit: int | None) -> Path:
    suffix = f"-first-{limit}" if limit is not None else ""
    return EVAL_RUNS_DIR / f"{model_slug(model)}{suffix}.json"


def write_report(report: dict[str, Any], model: str, limit: int | None) -> Path:
    EVAL_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = report_path(model, limit)
    output_path.write_text(json.dumps(report, indent=2))
    return output_path


def run_eval(
    limit: int | None = None,
    save: bool = False,
    model: str | None = None,
    progress: bool = False,
) -> dict[str, Any]:
    model = model or os.getenv("OLLAMA_MODEL", "qwen3.6:27b")
    scenarios = load_scenarios()
    if limit is not None:
        scenarios = scenarios[:limit]

    results = []
    report = {
        "model": model,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total": len(scenarios),
        "passed": 0,
        "failed": 0,
        "results": results,
    }

    for index, scenario in enumerate(scenarios, start=1):
        if progress:
            print(f"[{index}/{len(scenarios)}] {scenario['id']}", file=sys.stderr, flush=True)
        answer = explain_call(scenario["incident"], scenario["call"])
        score = score_scenario(scenario, answer)
        score["answer"] = answer
        results.append(score)
        report["passed"] = sum(1 for result in results if result["passed"])
        report["failed"] = len(results) - report["passed"]
        if save:
            output_path = write_report(report, model, limit)
            report["saved_to"] = str(output_path)

    report["total"] = len(results)
    if save:
        output_path = write_report(report, model, limit)
        report["saved_to"] = str(output_path)
    return report
