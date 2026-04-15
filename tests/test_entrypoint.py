"""Tests for the hosted backend entrypoint artifact checks."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _write_executable(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o755)


def test_entrypoint_rebuilds_indexes_when_chroma_collection_is_missing(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = tmp_path / "data"
    cleaned_dir = data_dir / "cleaned"
    whoosh_dir = data_dir / "indexes" / "whoosh"
    chroma_dir = data_dir / "indexes" / "chroma"
    corpus_dir = tmp_path / "corpus"
    bin_dir = tmp_path / "bin"
    log_path = tmp_path / "calls.log"

    cleaned_dir.mkdir(parents=True)
    whoosh_dir.mkdir(parents=True)
    chroma_dir.mkdir(parents=True)
    corpus_dir.mkdir(parents=True)
    bin_dir.mkdir(parents=True)

    (cleaned_dir / "page.md").write_text("# Title\n\nbody", encoding="utf-8")
    (data_dir / "chunks.jsonl").write_text("{}", encoding="utf-8")
    (whoosh_dir / "MAIN.toc").write_text("", encoding="utf-8")

    _write_executable(
        bin_dir / "python",
        """#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_PYTHON_LOG"
if [ "$1" = "scripts/build_index.py" ]; then
  exit 0
fi
if [ "$1" = "-c" ]; then
  exit 1
fi
exit 0
""",
    )
    _write_executable(
        bin_dir / "uvicorn",
        """#!/bin/sh
printf 'uvicorn %s\\n' "$*" >> "$FAKE_PYTHON_LOG"
exit 0
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "RAW_CORPUS_DIR": str(corpus_dir),
            "DATA_DIR": str(data_dir),
            "FAKE_PYTHON_LOG": str(log_path),
        }
    )

    subprocess.run(
        ["sh", "docker/entrypoint.sh"],
        cwd=repo_root,
        env=env,
        check=True,
    )

    calls = log_path.read_text(encoding="utf-8")
    assert "scripts/build_index.py" in calls
