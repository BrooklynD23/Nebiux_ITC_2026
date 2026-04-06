# Dataset Setup

The raw corpus (`itc2026_ai_corpus/`) is **not tracked in git** because it contains 8,000+ markdown files (~100 MB). Each contributor must set it up locally.

## Quick Setup

1. Download the corpus archive from the shared team drive (or the competition-provided source).
2. Extract it so the directory structure looks like this:

```
dataset/
  itc2026_ai_corpus/
    _aboutcpp.md
    _academic-programs.md
    ...           (8,043 .md files)
    index.json
  README.md       (this file)
```

3. Verify the file count:

```bash
ls dataset/itc2026_ai_corpus/*.md | wc -l
# Expected: 8043
```

4. Run the preprocessing pipeline to generate the cleaned outputs:

```bash
python scripts/preprocess/run_pipeline.py
```

This produces `data/cleaned/`, `data/metadata.json`, and `data/filter_report.json` (also gitignored since they are regeneratable).

## Important

- **Do NOT commit `dataset/itc2026_ai_corpus/`** — it is in `.gitignore`.
- **Do NOT rename or restructure** the corpus directory — the preprocessing pipeline expects this exact path.
- The `data/cleaned/` output directory is also gitignored. Each contributor regenerates it locally after setting up the raw corpus.

## Sharing the Corpus

Options for distributing the archive to contributors:
- Google Drive / OneDrive shared folder (recommended)
- Git LFS (if the team prefers keeping it in the repo workflow)
- Direct zip transfer

Whichever method you use, ensure `dataset/itc2026_ai_corpus/index.json` is present — it is used by the citation normalizer.
