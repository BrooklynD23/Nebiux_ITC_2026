"""Orchestrate the full preprocessing pipeline.

Reads raw corpus files, strips boilerplate, applies filters, and writes:
- data/cleaned/  -- cleaned markdown files (one per surviving source)
- data/metadata.json  -- array of metadata objects
- data/filter_report.json  -- excluded files with reasons and counts

This script is idempotent: re-running it will overwrite previous outputs.

Usage:
    python scripts/preprocess/run_pipeline.py
    python scripts/preprocess/run_pipeline.py --corpus-dir path/to/corpus
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path so we can import sibling modules
# when invoked as `python scripts/preprocess/run_pipeline.py`
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.preprocess.extract_metadata import PageMetadata, extract_metadata
from scripts.preprocess.filter_corpus import DiscardReason, FilterResult, filter_page
from scripts.preprocess.strip_boilerplate import StrippedResult, strip_boilerplate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_CORPUS_DIR = Path("dataset/itc2026_ai_corpus")
DEFAULT_OUTPUT_DIR = Path("data")
DEFAULT_CLEANED_DIR = DEFAULT_OUTPUT_DIR / "cleaned"
METADATA_FILE = DEFAULT_OUTPUT_DIR / "metadata.json"
FILTER_REPORT_FILE = DEFAULT_OUTPUT_DIR / "filter_report.json"


# ---------------------------------------------------------------------------
# Data classes for pipeline results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExcludedFile:
    """Record of a file excluded during filtering."""

    file: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {"file": self.file, "reason": self.reason}


@dataclass(frozen=True)
class FilterReport:
    """Summary report of the filtering step."""

    total_source_files: int
    kept: int
    excluded: int
    excluded_files: tuple[ExcludedFile, ...]
    reason_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_source_files": self.total_source_files,
            "kept": self.kept,
            "excluded": self.excluded,
            "excluded_files": [ef.to_dict() for ef in self.excluded_files],
            "reason_counts": dict(self.reason_counts),
        }


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _load_index(corpus_dir: Path) -> dict[str, str]:
    """Load the URL-to-filename mapping from index.json."""
    index_path = corpus_dir / "index.json"
    if not index_path.is_file():
        logger.warning("index.json not found at %s — URLs will be empty", index_path)
        return {}

    raw = json.loads(index_path.read_text(encoding="utf-8"))

    # index.json maps URL -> filename
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        # If it's a list of {url, file} objects, convert
        result: dict[str, str] = {}
        for item in raw:
            if isinstance(item, dict) and "url" in item and "file" in item:
                result[item["url"]] = item["file"]
        return result

    logger.warning("Unexpected index.json structure: %s", type(raw).__name__)
    return {}


def run_pipeline(
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> FilterReport:
    """Run the full preprocessing pipeline.

    Parameters
    ----------
    corpus_dir:
        Path to the raw corpus directory containing .md files and index.json.
    output_dir:
        Path to the output directory. Will contain cleaned/ subdirectory,
        metadata.json, and filter_report.json.

    Returns
    -------
    FilterReport:
        Summary of what was kept and excluded.
    """
    cleaned_dir = output_dir / "cleaned"

    # Ensure output directories exist (idempotent)
    if cleaned_dir.is_dir():
        shutil.rmtree(cleaned_dir)
    cleaned_dir.mkdir(parents=True, exist_ok=True)

    # Discover source files
    md_files = sorted(corpus_dir.glob("*.md"))
    total = len(md_files)

    if total == 0:
        logger.error("No .md files found in %s", corpus_dir)
        return FilterReport(
            total_source_files=0,
            kept=0,
            excluded=0,
            excluded_files=(),
            reason_counts={},
        )

    logger.info("Found %d source files in %s", total, corpus_dir)

    # Load URL index
    url_map = _load_index(corpus_dir)

    # Process each file
    metadata_list: list[dict[str, Any]] = []
    excluded_files: list[ExcludedFile] = []
    reason_counter: Counter[str] = Counter()

    for i, md_path in enumerate(md_files, 1):
        filename = md_path.name
        raw_content = md_path.read_text(encoding="utf-8", errors="replace")

        # Step 1: Strip boilerplate
        stripped = strip_boilerplate(raw_content)

        # Step 2: Apply filters
        result = filter_page(raw_content, stripped.content)

        if not result.keep:
            assert result.reason is not None
            excluded_files.append(
                ExcludedFile(file=filename, reason=result.reason.value)
            )
            reason_counter[result.reason.value] += 1
            continue

        # Step 3: Write cleaned file
        out_path = cleaned_dir / filename
        out_path.write_text(stripped.content, encoding="utf-8")

        # Step 4: Extract metadata
        meta = extract_metadata(filename, stripped.content, url_map)
        metadata_list.append(meta.to_dict())

        if i % 500 == 0:
            logger.info("Processed %d / %d files...", i, total)

    # Write metadata.json
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata_list, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Build and write filter report
    kept = total - len(excluded_files)
    report = FilterReport(
        total_source_files=total,
        kept=kept,
        excluded=len(excluded_files),
        excluded_files=tuple(excluded_files),
        reason_counts=dict(reason_counter),
    )

    report_path = output_dir / "filter_report.json"
    report_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info(
        "Pipeline complete: %d kept, %d excluded out of %d total",
        kept,
        len(excluded_files),
        total,
    )

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Preprocess CPP corpus: strip boilerplate, filter, extract metadata"
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=DEFAULT_CORPUS_DIR,
        help="Path to raw corpus directory (default: dataset/itc2026_ai_corpus)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Path to output directory (default: data)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if not args.corpus_dir.is_dir():
        logger.error(
            "Corpus directory not found: %s\n"
            "See dataset/README.md for setup instructions.",
            args.corpus_dir,
        )
        return 1

    start = time.monotonic()
    report = run_pipeline(args.corpus_dir, args.output_dir)
    elapsed = time.monotonic() - start

    print(f"\n{'='*60}")
    print(f"Preprocessing complete in {elapsed:.1f}s")
    print(f"  Total source files: {report.total_source_files}")
    print(f"  Kept:               {report.kept}")
    print(f"  Excluded:           {report.excluded}")
    if report.reason_counts:
        print(f"  Reasons:")
        for reason, count in sorted(
            report.reason_counts.items(), key=lambda x: -x[1]
        ):
            print(f"    {reason}: {count}")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
