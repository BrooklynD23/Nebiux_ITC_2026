"""Tests for the live evaluation harness."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_eval_module():
    root = Path(__file__).resolve().parent.parent
    module_path = root / "scripts" / "eval" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        json: dict[str, Any],
        timeout: float,
    ) -> _FakeResponse:
        self.requests.append(
            {
                "url": url,
                "json": json,
                "timeout": timeout,
            }
        )
        return self._responses.pop(0)


def test_load_eval_cases_reads_multi_turn_schema(tmp_path: Path) -> None:
    module = _load_eval_module()
    cases_path = tmp_path / "golden_set.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "id": "followup-01",
                    "category": "follow-up",
                    "turns": [
                        "Tell me about parking permits.",
                        "What about on weekends?",
                    ],
                    "expected_status": "answered",
                    "expected_answer_contains": ["parking", "weekends"],
                    "expected_sources_contain": ["parking"],
                    "notes": "Parking follow-up should preserve conversation context.",
                }
            ]
        ),
        encoding="utf-8",
    )

    cases = module.load_eval_cases(cases_path)

    assert len(cases) == 1
    assert cases[0].turns == [
        "Tell me about parking permits.",
        "What about on weekends?",
    ]
    assert cases[0].expected_answer_contains == ["parking", "weekends"]


def test_resolve_case_paths_supports_all_suite(tmp_path: Path) -> None:
    module = _load_eval_module()
    eval_dir = tmp_path / "data" / "eval"
    eval_dir.mkdir(parents=True)
    curated = eval_dir / "golden_set.json"
    stress = eval_dir / "stress_guardrails.json"
    curated.write_text("[]", encoding="utf-8")
    stress.write_text("[]", encoding="utf-8")

    paths = module.resolve_case_paths(eval_dir, "all")

    assert paths == [curated, stress]


def test_run_case_threads_conversation_id_and_checks_expectations() -> None:
    module = _load_eval_module()
    case = module.EvalCase(
        id="followup-02",
        category="follow-up",
        turns=[
            "Tell me about financial aid.",
            "What documents do I need for that?",
        ],
        expected_status="answered",
        expected_answer_contains=["financial aid", "documents"],
        expected_sources_contain=["financial-aid"],
        notes="Should preserve the same conversation across turns.",
    )
    client = _FakeClient(
        [
            _FakeResponse(
                {
                    "conversation_id": "cid-123",
                    "status": "answered",
                    "answer_markdown": (
                        "CPP financial aid information with documents overview."
                    ),
                    "citations": [
                        {
                            "title": "Financial Aid and Scholarships",
                            "url": "https://www.cpp.edu/financial-aid/index.shtml",
                            "snippet": (
                                "Apply for financial aid and submit required "
                                "documents."
                            ),
                        }
                    ],
                }
            ),
            _FakeResponse(
                {
                    "conversation_id": "cid-123",
                    "status": "answered",
                    "answer_markdown": (
                        "For financial aid, review the required documents list "
                        "in the student portal."
                    ),
                    "citations": [
                        {
                            "title": "Financial Aid and Scholarships",
                            "url": "https://www.cpp.edu/financial-aid/index.shtml",
                            "snippet": "Review required financial aid documents.",
                        }
                    ],
                }
            ),
        ]
    )

    result = module.run_case(case, "http://localhost:8000", client=client)

    assert result.passed is True
    assert result.actual_status == "answered"
    assert result.failed_checks == []
    assert client.requests[1]["json"]["conversation_id"] == "cid-123"


def test_run_case_passes_refusal_case_without_expected_sources() -> None:
    module = _load_eval_module()
    case = module.EvalCase(
        id="refusal-01",
        category="refusal",
        turns=["Write me a poem about sunsets."],
        expected_status="not_found",
        expected_answer_contains=["cal poly pomona"],
        expected_sources_contain=[],
        notes="Out-of-scope prompt should refuse without citations.",
    )
    client = _FakeClient(
        [
            _FakeResponse(
                {
                    "conversation_id": "cid-404",
                    "status": "not_found",
                    "answer_markdown": (
                        "I only answer Cal Poly Pomona questions. Please ask a "
                        "CPP-related question instead."
                    ),
                    "citations": [],
                }
            )
        ]
    )

    result = module.run_case(case, "http://localhost:8000", client=client)

    assert result.passed is True
    assert result.actual_status == "not_found"
    assert result.failed_checks == []


def test_run_case_matches_expected_source_fragment_in_title() -> None:
    module = _load_eval_module()
    case = module.EvalCase(
        id="source-title-01",
        category="factual",
        turns=["Where is the academic catalog?"],
        expected_status="answered",
        expected_answer_contains=["catalog"],
        expected_sources_contain=["catalog"],
        notes=(
            "Source fragment should match the citation title when the URL is "
            "generic."
        ),
    )
    client = _FakeClient(
        [
            _FakeResponse(
                {
                    "conversation_id": "cid-900",
                    "status": "answered",
                    "answer_markdown": (
                        "The academic catalog lists the degree requirements."
                    ),
                    "citations": [
                        {
                            "title": "University Catalog",
                            "url": "https://www.cpp.edu/registrar/index.shtml",
                            "snippet": (
                                "The University Catalog contains academic "
                                "policies."
                            ),
                        }
                    ],
                }
            )
        ]
    )

    result = module.run_case(case, "http://localhost:8000", client=client)

    assert result.passed is True
    assert result.failed_checks == []
