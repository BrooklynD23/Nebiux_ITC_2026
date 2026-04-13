"""Build retrieval artifacts from the cleaned corpus.

This script produces:
- ``data/chunks.jsonl``: heading-aware chunk manifest
- ``data/indexes/whoosh/``: persisted BM25 lexical index
- ``data/indexes/manifest.json``: build summary and artifact pointers

The Chroma/vector index path is intentionally reserved in the manifest but is
not populated by issue #18. The goal of this issue is to standardize artifact
layout and startup flow, not to finish the full hybrid retriever.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer
from whoosh import index
from whoosh.fields import ID, STORED, TEXT, Schema

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHROMA_COLLECTION = "cpp_corpus"
CHROMA_BATCH_SIZE = 256

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.settings import get_settings  # noqa: E402

logger = logging.getLogger(__name__)

MAX_CHUNK_CHARS = 1400


@dataclass(frozen=True)
class ChunkRecord:
    """Serialized retrieval chunk."""

    chunk_id: str
    source_file: str
    title: str
    url: str
    heading: str
    content: str
    snippet: str
    word_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source_file": self.source_file,
            "title": self.title,
            "url": self.url,
            "heading": self.heading,
            "content": self.content,
            "snippet": self.snippet,
            "word_count": self.word_count,
        }


def _collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _word_count(value: str) -> int:
    return len(_collapse_ws(value).split())


def _chunk_text(heading: str, text: str) -> list[str]:
    """Split a section into reasonably sized chunks by paragraph."""
    normalized = text.strip()
    if not normalized:
        return []

    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    if not paragraphs:
        return [normalized]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        paragraph_len = len(paragraph)
        projected_len = current_len + paragraph_len + (2 if current else 0)
        if current and projected_len > MAX_CHUNK_CHARS:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            current_len = paragraph_len
            continue

        current.append(paragraph)
        current_len = projected_len

    if current:
        chunks.append("\n\n".join(current))

    if heading:
        prefixed: list[str] = []
        for chunk in chunks:
            if chunk.startswith("#"):
                prefixed.append(chunk)
            else:
                prefixed.append(f"## {heading}\n\n{chunk}")
        return prefixed

    return chunks


def _split_into_sections(title: str, content: str) -> list[tuple[str, str]]:
    """Create heading-aware sections from a markdown document."""
    sections: list[tuple[str, str]] = []
    heading_stack: list[str] = []
    current_lines: list[str] = []

    def flush() -> None:
        body = "\n".join(current_lines).strip()
        if not body:
            return
        heading = " > ".join(part for part in heading_stack if part) or title
        sections.append((heading, body))

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            flush()
            level = len(stripped) - len(stripped.lstrip("#"))
            heading_text = stripped[level:].strip()
            heading_stack[:] = heading_stack[: max(level - 1, 0)]
            heading_stack.append(heading_text)
            current_lines = [line]
            continue

        if stripped or current_lines:
            current_lines.append(line)

    flush()
    return sections


def _load_metadata(metadata_path: Path) -> list[dict[str, Any]]:
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("metadata.json must be a list of objects")
    return [item for item in raw if isinstance(item, dict)]


def build_chunk_manifest(
    cleaned_dir: Path,
    metadata_path: Path,
) -> list[ChunkRecord]:
    """Build chunk records from cleaned markdown pages."""
    metadata_entries = _load_metadata(metadata_path)
    metadata_by_file = {
        str(item["source_file"]): item
        for item in metadata_entries
        if "source_file" in item
    }

    chunks: list[ChunkRecord] = []

    for md_path in sorted(cleaned_dir.glob("*.md")):
        metadata = metadata_by_file.get(md_path.name)
        if metadata is None:
            logger.warning("Skipping %s because metadata is missing", md_path.name)
            continue

        content = md_path.read_text(encoding="utf-8")
        title = str(metadata.get("title") or md_path.stem)
        url = str(metadata.get("url") or "")

        section_index = 0
        for heading, section_body in _split_into_sections(title, content):
            for chunk_index, chunk_body in enumerate(
                _chunk_text(heading, section_body), start=1
            ):
                chunk_id = f"{md_path.stem}-{section_index:03d}-{chunk_index:02d}"
                snippet = _collapse_ws(chunk_body)[:280]
                chunks.append(
                    ChunkRecord(
                        chunk_id=chunk_id,
                        source_file=md_path.name,
                        title=title,
                        url=url,
                        heading=heading,
                        content=chunk_body,
                        snippet=snippet,
                        word_count=_word_count(chunk_body),
                    )
                )
            section_index += 1

    return chunks


def write_chunk_manifest(chunks: list[ChunkRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk.to_dict(), ensure_ascii=False))
            handle.write("\n")


def build_whoosh_index(chunks: list[ChunkRecord], output_dir: Path) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    schema = Schema(
        chunk_id=ID(stored=True, unique=True),
        source_file=ID(stored=True),
        title=TEXT(stored=True),
        url=ID(stored=True),
        heading=TEXT(stored=True),
        snippet=STORED,
        content=TEXT(stored=True),
    )
    whoosh_index = index.create_in(output_dir, schema)
    writer = whoosh_index.writer()
    for chunk in chunks:
        writer.add_document(
            chunk_id=chunk.chunk_id,
            source_file=chunk.source_file,
            title=chunk.title,
            url=chunk.url,
            heading=chunk.heading,
            snippet=chunk.snippet,
            content=chunk.content,
        )
    writer.commit()


def build_chroma_index(chunks: list[ChunkRecord], chroma_dir: Path) -> None:
    """Embed chunks with sentence-transformers and persist into Chroma."""
    chroma_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading embedding model '%s'...", EMBEDDING_MODEL)
    model = SentenceTransformer(EMBEDDING_MODEL)

    client = chromadb.PersistentClient(path=str(chroma_dir))

    # Wipe and recreate so re-runs are idempotent
    try:
        client.delete_collection(CHROMA_COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(
        CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [c.chunk_id for c in chunks]
    documents = [c.content for c in chunks]
    metadatas = [
        {"title": c.title, "url": c.url, "snippet": c.snippet}
        for c in chunks
    ]

    logger.info("Embedding %d chunks in batches of %d...", len(chunks), CHROMA_BATCH_SIZE)
    for start in range(0, len(chunks), CHROMA_BATCH_SIZE):
        batch_ids = ids[start : start + CHROMA_BATCH_SIZE]
        batch_docs = documents[start : start + CHROMA_BATCH_SIZE]
        batch_meta = metadatas[start : start + CHROMA_BATCH_SIZE]
        embeddings = model.encode(batch_docs, show_progress_bar=False).tolist()
        collection.add(ids=batch_ids, documents=batch_docs, embeddings=embeddings, metadatas=batch_meta)
        logger.info("  Embedded %d / %d", min(start + CHROMA_BATCH_SIZE, len(chunks)), len(chunks))

    logger.info("Chroma index written to %s", chroma_dir)


def write_manifest(
    *,
    chunk_count: int,
    output_dir: Path,
    chunk_manifest_path: Path,
    whoosh_dir: Path,
) -> None:
    manifest = {
        "retrieval_strategy": "precomputed-bm25-with-reserved-vector-path",
        "chunk_count": chunk_count,
        "chunk_manifest": str(chunk_manifest_path),
        "whoosh_index_dir": str(whoosh_dir),
        "chroma_index_dir": str(output_dir / "indexes" / "chroma"),
    }
    manifest_path = output_dir / "indexes" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "indexes" / "chroma").mkdir(parents=True, exist_ok=True)


def main() -> int:
    settings = get_settings()

    parser = argparse.ArgumentParser(
        description="Build lexical retrieval artifacts from the cleaned corpus."
    )
    parser.add_argument(
        "--cleaned-dir",
        type=Path,
        default=settings.cleaned_dir,
        help="Path to the cleaned corpus directory.",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=settings.metadata_path,
        help="Path to metadata.json generated by preprocessing.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=settings.data_dir,
        help="Base output directory for chunks and indexes.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if not args.cleaned_dir.is_dir():
        logger.error("Cleaned corpus directory not found: %s", args.cleaned_dir)
        return 1

    if not args.metadata_path.is_file():
        logger.error("metadata.json not found: %s", args.metadata_path)
        return 1

    chunk_manifest_path = args.output_dir / "chunks.jsonl"
    whoosh_dir = args.output_dir / "indexes" / "whoosh"

    chroma_dir = args.output_dir / "indexes" / "chroma"

    chunks = build_chunk_manifest(args.cleaned_dir, args.metadata_path)
    write_chunk_manifest(chunks, chunk_manifest_path)
    build_whoosh_index(chunks, whoosh_dir)
    build_chroma_index(chunks, chroma_dir)
    write_manifest(
        chunk_count=len(chunks),
        output_dir=args.output_dir,
        chunk_manifest_path=chunk_manifest_path,
        whoosh_dir=whoosh_dir,
    )

    logger.info("Built %d chunks into %s", len(chunks), chunk_manifest_path)
    logger.info("Built BM25 index in %s", whoosh_dir)
    logger.info("Built semantic index in %s", chroma_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
