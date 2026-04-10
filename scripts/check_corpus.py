"""Verify that the raw corpus is installed correctly."""

import argparse
import json
import os
import sys
from pathlib import Path

EXPECTED_MIN_FILES = 8000


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that the raw corpus is installed correctly."
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path(os.environ.get("RAW_CORPUS_DIR", "dataset/itc2026_ai_corpus")),
        help="Path to the raw corpus directory.",
    )
    args = parser.parse_args()

    corpus_dir = args.corpus_dir
    index_file = corpus_dir / "index.json"
    errors: list[str] = []

    if not corpus_dir.is_dir():
        print(f"FAIL: {corpus_dir} does not exist.")
        print("See dataset/README.md for setup instructions.")
        return 1

    md_files = list(corpus_dir.glob("*.md"))
    count = len(md_files)

    if count < EXPECTED_MIN_FILES:
        errors.append(f"Expected >= {EXPECTED_MIN_FILES} .md files, found {count}")

    if not index_file.is_file():
        errors.append(f"Missing {index_file}")
    else:
        try:
            data = json.loads(index_file.read_text(encoding="utf-8"))
            if not isinstance(data, (list, dict)):
                errors.append("index.json is not a list or dict")
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            errors.append(f"index.json is not valid JSON: {e}")

    if errors:
        print("FAIL: Corpus check found issues:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"OK: {count} .md files found, index.json valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
