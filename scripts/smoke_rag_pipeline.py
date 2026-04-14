"""Smoke-test the cleaned-corpus RAG path end to end.

This script validates the local pipeline without requiring the Gemini API:
- checks that the raw corpus is present
- runs preprocessing into a chosen output directory
- builds the cleaned-corpus chunk manifest and Whoosh BM25 index
- runs a retrieval probe against the built index

Use ``--mode gemini`` to attempt a live ``POST /chat``-style call through the
Gemini-backed tool loop once network access is available.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.build_index import (  # noqa: E402
    build_chunk_manifest,
    build_whoosh_index,
    write_chunk_manifest,
    write_manifest,
)
from scripts.check_corpus import EXPECTED_MIN_FILES  # noqa: E402
from scripts.preprocess.run_pipeline import run_pipeline  # noqa: E402
from src.retrieval.whoosh_retriever import WhooshRetriever  # noqa: E402

logger = logging.getLogger(__name__)


def _check_corpus(corpus_dir: Path) -> None:
    if not corpus_dir.is_dir():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")

    md_count = len(list(corpus_dir.glob("*.md")))
    if md_count < EXPECTED_MIN_FILES:
        raise RuntimeError(
            f"Expected at least {EXPECTED_MIN_FILES} .md files, found {md_count}"
        )

    index_file = corpus_dir / "index.json"
    if not index_file.is_file():
        raise FileNotFoundError(f"Missing corpus index: {index_file}")


def _build_local_rag_artifacts(corpus_dir: Path, output_dir: Path) -> dict[str, Any]:
    report = run_pipeline(corpus_dir=corpus_dir, output_dir=output_dir)

    cleaned_dir = output_dir / "cleaned"
    metadata_path = output_dir / "metadata.json"
    chunks = build_chunk_manifest(cleaned_dir, metadata_path)
    chunk_manifest_path = output_dir / "chunks.jsonl"
    whoosh_dir = output_dir / "indexes" / "whoosh"

    write_chunk_manifest(chunks, chunk_manifest_path)
    build_whoosh_index(chunks, whoosh_dir)
    write_manifest(
        chunk_count=len(chunks),
        output_dir=output_dir,
        chunk_manifest_path=chunk_manifest_path,
        whoosh_dir=whoosh_dir,
    )

    return {
        "report": report,
        "chunk_count": len(chunks),
        "chunk_manifest_path": chunk_manifest_path,
        "whoosh_dir": whoosh_dir,
    }


async def _run_retrieval_probe(query: str) -> list[dict[str, Any]]:
    retriever = WhooshRetriever()
    results = await retriever.search_corpus(query, top_k=5)
    return [
        {
            "title": result.title,
            "url": result.url,
            "score": result.score,
            "snippet": result.snippet,
        }
        for result in results
    ]


async def _run_gemini_probe(query: str) -> dict[str, Any]:
    from src.agent.tool_loop import run_tool_loop

    response = await run_tool_loop(message=query, retriever=WhooshRetriever())
    return response.model_dump()


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the cleaned-corpus RAG path.")
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path(os.environ.get("RAW_CORPUS_DIR", "dataset/itc2026_ai_corpus")),
        help="Path to the raw corpus directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for generated artifacts. Defaults to a temp directory.",
    )
    parser.add_argument(
        "--query",
        default="What are the FAFSA deadlines at CPP?",
        help="Probe query to run against the built index.",
    )
    parser.add_argument(
        "--mode",
        choices=("local", "gemini"),
        default="local",
        help="Local only validates retrieval; gemini attempts the live tool loop.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    _check_corpus(args.corpus_dir)
    logger.info("Corpus check passed: %s", args.corpus_dir)

    if args.output_dir is None:
        with TemporaryDirectory(prefix="nebiux_itc_smoke_") as tmpdir:
            output_dir = Path(tmpdir)
            artifacts = _build_local_rag_artifacts(args.corpus_dir, output_dir)
            _print_artifact_summary(artifacts)
            os.environ["DATA_DIR"] = str(output_dir)
            _run_probe(args.mode, args.query)
    else:
        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        artifacts = _build_local_rag_artifacts(args.corpus_dir, output_dir)
        _print_artifact_summary(artifacts)
        os.environ["DATA_DIR"] = str(output_dir)
        _run_probe(args.mode, args.query)

    return 0


def _print_artifact_summary(artifacts: dict[str, Any]) -> None:
    report = artifacts["report"]
    logger.info(
        "Preprocessing complete: kept=%d excluded=%d chunks=%d",
        report.kept,
        report.excluded,
        artifacts["chunk_count"],
    )
    logger.info("Whoosh index: %s", artifacts["whoosh_dir"])
    logger.info("Chunk manifest: %s", artifacts["chunk_manifest_path"])


def _run_probe(mode: str, query: str) -> None:
    import asyncio

    if mode == "gemini":
        result = asyncio.run(_run_gemini_probe(query))
        logger.info("Gemini-backed /chat result:")
        logger.info("status=%s", result["status"])
        logger.info("citations=%d", len(result["citations"]))
        logger.info("answer=%s", result["answer_markdown"][:800])
        return

    results = asyncio.run(_run_retrieval_probe(query))
    logger.info("Retrieval probe for query: %r", query)
    logger.info("Top %d results:", len(results))
    for idx, result in enumerate(results, start=1):
        logger.info(
            "  %d. %s | score=%.4f | %s",
            idx,
            result["title"],
            result["score"],
            result["url"],
        )


if __name__ == "__main__":
    raise SystemExit(main())
