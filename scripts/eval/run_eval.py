"""Live evaluation harness for the CPP Campus Knowledge Agent.

Usage:
    python3 scripts/eval/run_eval.py
    python3 scripts/eval/run_eval.py --suite stress
    python3 scripts/eval/run_eval.py --cases data/eval/golden_set.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_EVAL_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "eval"
CURATED_CASES_PATH = DEFAULT_EVAL_DIR / "golden_set.json"
STRESS_CASES_PATH = DEFAULT_EVAL_DIR / "stress_guardrails.json"

VALID_STATUSES = {"answered", "not_found", "error"}
VALID_CATEGORIES = {
    "factual",
    "follow-up",
    "refusal",
    "messy",
    "adversarial",
    "support",
}
ROUTE_LABELS = {
    "caps": "Counseling and Psychological Services",
    "student_health": "Student Health Services",
    "university_police": "University Police",
    "care_center": "Care Center",
}


@dataclass(frozen=True)
class EvalCase:
    """A single evaluation case."""

    id: str
    category: str
    turns: list[str]
    expected_status: str
    expected_answer_contains: list[str]
    expected_sources_contain: list[str]
    notes: str
    expected_route: str | None = None


@dataclass(frozen=True)
class EvalResult:
    """Outcome of evaluating one case."""

    case_id: str
    passed: bool
    expected_status: str
    actual_status: str | None
    failed_checks: list[str] = field(default_factory=list)
    error: str | None = None


def resolve_case_paths(eval_dir: Path, suite: str) -> list[Path]:
    """Resolve case files for a named suite."""
    if suite == "curated":
        return [
            CURATED_CASES_PATH
            if eval_dir == DEFAULT_EVAL_DIR
            else eval_dir / "golden_set.json"
        ]
    if suite == "stress":
        return [
            STRESS_CASES_PATH
            if eval_dir == DEFAULT_EVAL_DIR
            else eval_dir / "stress_guardrails.json"
        ]
    if suite == "all":
        return [
            CURATED_CASES_PATH
            if eval_dir == DEFAULT_EVAL_DIR
            else eval_dir / "golden_set.json",
            STRESS_CASES_PATH
            if eval_dir == DEFAULT_EVAL_DIR
            else eval_dir / "stress_guardrails.json",
        ]
    raise ValueError(f"Unknown suite: {suite}")


def load_eval_cases(path: Path) -> list[EvalCase]:
    """Load and validate a case file."""
    if not path.exists():
        raise FileNotFoundError(f"Case file not found: {path}")

    with open(path, encoding="utf-8") as f:
        raw_cases = json.load(f)

    if not isinstance(raw_cases, list):
        raise ValueError(f"Case file must contain a list: {path}")

    cases: list[EvalCase] = []
    for raw in raw_cases:
        turns = raw.get("turns")
        if not isinstance(turns, list) or not turns or not all(
            isinstance(turn, str) and turn.strip() for turn in turns
        ):
            raise ValueError(
                f"Case {raw.get('id', '<missing>')} has invalid turns in {path}"
            )

        category = raw["category"]
        expected_status = raw["expected_status"]
        expected_route = raw.get("expected_route")

        if category not in VALID_CATEGORIES:
            raise ValueError(
                f"Case {raw.get('id', '<missing>')} has invalid category: {category}"
            )
        if expected_status not in VALID_STATUSES:
            raise ValueError(
                "Case "
                f"{raw.get('id', '<missing>')} has invalid status: "
                f"{expected_status}"
            )
        if expected_route is not None and expected_route not in ROUTE_LABELS:
            raise ValueError(
                f"Case {raw.get('id', '<missing>')} has invalid route: {expected_route}"
            )

        cases.append(
            EvalCase(
                id=raw["id"],
                category=category,
                turns=turns,
                expected_status=expected_status,
                expected_answer_contains=_normalize_string_list(
                    raw.get("expected_answer_contains", [])
                ),
                expected_sources_contain=_normalize_string_list(
                    raw.get("expected_sources_contain", [])
                ),
                notes=raw.get("notes", ""),
                expected_route=expected_route,
            )
        )

    return cases


def run_case(
    case: EvalCase,
    api_url: str,
    client: Any | None = None,
    timeout: float = 20.0,
) -> EvalResult:
    """Run a single case by posting each turn to the live API."""
    own_client = client is None
    http_client = client or httpx.Client()
    conversation_id: str | None = None
    final_payload: dict[str, Any] | None = None
    is_multi_turn = len(case.turns) > 1
    extra_failed_checks: list[str] = []

    try:
        for turn_idx, turn in enumerate(case.turns):
            payload: dict[str, Any] = {"message": turn}
            if conversation_id is not None:
                payload["conversation_id"] = conversation_id

            response = http_client.post(
                f"{api_url.rstrip('/')}/chat",
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()

            final_payload = response.json()
            returned_id = final_payload.get("conversation_id")

            if is_multi_turn:
                if turn_idx == 0 and not returned_id:
                    extra_failed_checks.append("missing_conversation_id")
                elif (
                    turn_idx > 0
                    and conversation_id is not None
                    and returned_id != conversation_id
                    and "unstable_conversation_id" not in extra_failed_checks
                ):
                    extra_failed_checks.append("unstable_conversation_id")

            conversation_id = returned_id

        if final_payload is None:
            return EvalResult(
                case_id=case.id,
                passed=False,
                expected_status=case.expected_status,
                actual_status=None,
                failed_checks=["no_response"],
                error="No response payload received from the API",
            )

        result = _evaluate_response(case, final_payload)
        if extra_failed_checks:
            return EvalResult(
                case_id=case.id,
                passed=False,
                expected_status=result.expected_status,
                actual_status=result.actual_status,
                failed_checks=result.failed_checks + extra_failed_checks,
            )
        return result
    except Exception as exc:
        return EvalResult(
            case_id=case.id,
            passed=False,
            expected_status=case.expected_status,
            actual_status=None,
            failed_checks=["transport_error"],
            error=str(exc),
        )
    finally:
        if own_client:
            http_client.close()


def print_summary(results: list[EvalResult]) -> None:
    """Print a concise pass/fail summary table."""
    total = len(results)
    passed = sum(1 for result in results if result.passed)

    logger.info("")
    logger.info("=== Evaluation Summary ===")
    logger.info("Passed: %d / %d", passed, total)
    logger.info("")

    for result in results:
        status_icon = "PASS" if result.passed else "FAIL"
        details = ""
        if result.failed_checks:
            details = f" checks={','.join(result.failed_checks)}"
        if result.error:
            details += f" error={result.error}"
        logger.info(
            "[%s] %s expected=%s actual=%s%s",
            status_icon,
            result.case_id,
            result.expected_status,
            result.actual_status or "N/A",
            details,
        )


def main() -> None:
    """Entry point for the eval harness."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description="Run live eval harness")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL of the chat API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=None,
        help="Optional path to a specific case file",
    )
    parser.add_argument(
        "--suite",
        choices=("curated", "stress", "all"),
        default="curated",
        help="Named suite to run when --cases is omitted",
    )
    args = parser.parse_args()

    try:
        case_paths = (
            [args.cases]
            if args.cases is not None
            else resolve_case_paths(DEFAULT_EVAL_DIR, args.suite)
        )
        cases = _load_case_files(case_paths)
    except Exception as exc:
        logger.error("Failed to load eval cases: %s", exc)
        sys.exit(1)

    logger.info("Loaded %d cases", len(cases))
    _log_category_counts(cases)
    logger.info("")
    logger.info("Running evaluation against %s ...", args.api_url)

    results = [run_case(case, args.api_url) for case in cases]
    print_summary(results)

    if any(not result.passed for result in results):
        sys.exit(1)


def _load_case_files(paths: list[Path]) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for path in paths:
        loaded = load_eval_cases(path)
        logger.info("Loaded %d cases from %s", len(loaded), path)
        cases.extend(loaded)
    return cases


def _evaluate_response(
    case: EvalCase,
    payload: dict[str, Any],
) -> EvalResult:
    actual_status = payload.get("status")
    answer_markdown = str(payload.get("answer_markdown", ""))
    citations = payload.get("citations") or []
    failed_checks: list[str] = []

    if actual_status != case.expected_status:
        failed_checks.append("status")

    if case.expected_status == "answered":
        if not answer_markdown.strip():
            failed_checks.append("missing_answer")
        if not citations:
            failed_checks.append("missing_citations")
    else:
        if citations:
            failed_checks.append("unexpected_citations")

    for expected_text in case.expected_answer_contains:
        if expected_text.lower() not in answer_markdown.lower():
            failed_checks.append(f"answer:{expected_text}")

    citation_urls = [
        str(citation.get("url", "")).lower()
        for citation in citations
        if isinstance(citation, dict)
    ]
    citation_titles = [
        str(citation.get("title", "")).lower()
        for citation in citations
        if isinstance(citation, dict)
    ]

    for source_fragment in case.expected_sources_contain:
        fragment = source_fragment.lower()
        if not any(
            fragment in candidate
            for candidate in citation_urls + citation_titles + [
                str(citation.get("snippet", "")).lower()
                for citation in citations
                if isinstance(citation, dict)
            ]
        ):
            failed_checks.append(f"source:{source_fragment}")

    if case.expected_route is not None:
        route_label = ROUTE_LABELS[case.expected_route].lower()
        if route_label not in answer_markdown.lower() and not any(
            route_label in title for title in citation_titles
        ):
            failed_checks.append(f"route:{case.expected_route}")

    return EvalResult(
        case_id=case.id,
        passed=not failed_checks,
        expected_status=case.expected_status,
        actual_status=actual_status,
        failed_checks=failed_checks,
    )


def _log_category_counts(cases: list[EvalCase]) -> None:
    by_category: dict[str, int] = {}
    for case in cases:
        by_category[case.category] = by_category.get(case.category, 0) + 1
    for category, count in sorted(by_category.items()):
        logger.info("[%s] %d cases", category, count)


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Expected a list of strings, got: {value!r}")
    return [item.strip() for item in value if item.strip()]


if __name__ == "__main__":
    main()
