"""
Evaluation harness for the CPP Campus Knowledge Agent.

Sprint 1: Skeleton only — loads golden cases and validates their structure.
Sprint 2: Sends each query to the live API, compares status and citations.

Usage:
    python scripts/eval/run_eval.py [--api-url URL]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

GOLDEN_CASES_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "eval" / "golden_cases.json"
)

VALID_STATUSES = {"answered", "not_found", "error"}
VALID_CATEGORIES = {"factual", "follow-up", "out-of-scope", "adversarial"}


@dataclass(frozen=True)
class EvalCase:
    """A single golden evaluation case."""

    id: str
    category: str
    query: str
    expected_status: str
    must_cite_url_pattern: Optional[str]
    notes: str
    depends_on: Optional[str] = None


@dataclass(frozen=True)
class EvalResult:
    """Result of evaluating a single case against the API."""

    case_id: str
    passed: bool
    expected_status: str
    actual_status: Optional[str]
    citation_check: Optional[bool]
    error: Optional[str]


def load_golden_cases(path: Path) -> list[EvalCase]:
    """Load and validate golden evaluation cases from JSON."""
    if not path.exists():
        logger.error("Golden cases file not found: %s", path)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        raw_cases = json.load(f)

    cases: list[EvalCase] = []
    for raw in raw_cases:
        case = EvalCase(
            id=raw["id"],
            category=raw["category"],
            query=raw["query"],
            expected_status=raw["expected_status"],
            must_cite_url_pattern=raw.get("must_cite_url_pattern"),
            notes=raw.get("notes", ""),
            depends_on=raw.get("depends_on"),
        )

        if case.category not in VALID_CATEGORIES:
            logger.warning("Case %s has unknown category: %s", case.id, case.category)

        if case.expected_status not in VALID_STATUSES:
            logger.warning(
                "Case %s has unknown expected_status: %s",
                case.id,
                case.expected_status,
            )

        cases.append(case)

    return cases


def run_case(
    case: EvalCase,
    api_url: str,
    conversation_id: Optional[str] = None,
) -> EvalResult:
    """
    Run a single eval case against the API.

    Sprint 1: Returns a placeholder result (API not yet available).
    Sprint 2: Will send the query and compare response status + citations.
    """
    _ = api_url, conversation_id
    logger.info("  [SKIP] %s — API not yet available (Sprint 1 skeleton)", case.id)

    return EvalResult(
        case_id=case.id,
        passed=False,
        expected_status=case.expected_status,
        actual_status=None,
        citation_check=None,
        error="Sprint 1 skeleton — no API call made",
    )


def print_summary(results: list[EvalResult]) -> None:
    """Print a summary table of eval results."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    logger.info("")
    logger.info("=== Evaluation Summary ===")
    logger.info("Total:  %d", total)
    logger.info("Passed: %d", passed)
    logger.info("Failed: %d", failed)
    logger.info("")

    for result in results:
        status_icon = "PASS" if result.passed else "FAIL"
        logger.info(
            "  [%s] %s — expected=%s actual=%s%s",
            status_icon,
            result.case_id,
            result.expected_status,
            result.actual_status or "N/A",
            f" error={result.error}" if result.error else "",
        )


def main() -> None:
    """Entry point for the eval harness."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description="Run eval harness against golden cases")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL of the chat API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=GOLDEN_CASES_PATH,
        help="Path to golden cases JSON file",
    )
    args = parser.parse_args()

    logger.info("Loading golden cases from %s", args.cases)
    cases = load_golden_cases(args.cases)
    logger.info("Loaded %d cases", len(cases))
    logger.info("")

    by_category: dict[str, list[EvalCase]] = {}
    for case in cases:
        by_category.setdefault(case.category, []).append(case)

    for category, category_cases in by_category.items():
        logger.info("[%s] %d cases", category, len(category_cases))

    logger.info("")
    logger.info("Running evaluation against %s ...", args.api_url)

    results: list[EvalResult] = []
    conversation_id: Optional[str] = None

    for case in cases:
        result = run_case(case, args.api_url, conversation_id)
        results.append(result)

    print_summary(results)

    if any(not r.passed for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
