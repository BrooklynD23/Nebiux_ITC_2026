"""Tests for the retrieval artifact builder."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_index import (
    build_chunk_manifest,
    build_whoosh_index,
    write_chunk_manifest,
    write_manifest,
)


def test_build_index_writes_chunk_manifest_and_index(tmp_path: Path) -> None:
    cleaned_dir = tmp_path / "cleaned"
    cleaned_dir.mkdir()
    metadata_path = tmp_path / "metadata.json"
    output_dir = tmp_path / "data"

    (cleaned_dir / "admissions.md").write_text(
        """# Admissions

CPP admissions include first-year, transfer, and international pathways.

## Deadlines

Applications open in October and close in December for the fall term.

## Requirements

Students must complete the A-G pattern and submit required transcripts.
""",
        encoding="utf-8",
    )

    metadata_path.write_text(
        json.dumps(
            [
                {
                    "source_file": "admissions.md",
                    "cleaned_file": "admissions.md",
                    "title": "Admissions",
                    "url": "https://www.cpp.edu/admissions/index.shtml",
                    "word_count": 31,
                    "heading_count": 3,
                    "has_tables": False,
                    "quality_flags": ["has_headings"],
                }
            ]
        ),
        encoding="utf-8",
    )

    chunks = build_chunk_manifest(cleaned_dir, metadata_path)

    assert len(chunks) >= 2
    assert all(chunk.source_file == "admissions.md" for chunk in chunks)
    assert all(
        chunk.url == "https://www.cpp.edu/admissions/index.shtml" for chunk in chunks
    )

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
    manifest = json.loads(
        (output_dir / "indexes" / "manifest.json").read_text(encoding="utf-8")
    )

    assert chunk_manifest_path.is_file()
    assert whoosh_dir.is_dir()
    assert (output_dir / "indexes" / "manifest.json").is_file()
    assert manifest["retrieval_strategy"] == "precomputed-hybrid-bm25-chroma"
