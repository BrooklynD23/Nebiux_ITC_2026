"""Verify that the raw corpus is installed correctly."""

import json
import sys
from pathlib import Path

CORPUS_DIR = Path("dataset/itc2026_ai_corpus")
EXPECTED_MIN_FILES = 8000
INDEX_FILE = CORPUS_DIR / "index.json"


def main() -> int:
    errors: list[str] = []

    if not CORPUS_DIR.is_dir():
        print(f"FAIL: {CORPUS_DIR} does not exist.")
        print("See dataset/README.md for setup instructions.")
        return 1

    md_files = list(CORPUS_DIR.glob("*.md"))
    count = len(md_files)

    if count < EXPECTED_MIN_FILES:
        errors.append(
            f"Expected >= {EXPECTED_MIN_FILES} .md files, found {count}"
        )

    if not INDEX_FILE.is_file():
        errors.append(f"Missing {INDEX_FILE}")
    else:
        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
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
