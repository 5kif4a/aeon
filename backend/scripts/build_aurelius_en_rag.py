"""Build the English Marcus Aurelius RAG corpus from the Casaubon edition."""

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

SOURCE = "Marcus Aurelius, Meditations (Meric Casaubon translation, 2013 edition)"
BOOK_STARTS = {
    12: "Book I",
    19: "Book II",
    23: "Book III",
    29: "Book IV",
    38: "Book V",
    47: "Book VI",
    57: "Book VII",
    66: "Book VIII",
    77: "Book IX",
    86: "Book X",
    96: "Book XI",
    104: "Book XII",
}
SENTENCE_RE = re.compile(r"(?<=[.!?\u2026])\s+")
PAGE_NUMBER_RE = re.compile(r"^Page \d+ of 128$")


def clean_text(text: str) -> str:
    kept_lines = []
    normalized = text.replace("\u00ad", "").replace("\u00a0", " ").replace("\ufffd", "'")
    for line in normalized.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("MEDITATIONS OF MARCUS AURELIUS"):
            continue
        if line.startswith("Marcus Aurelius' Meditations - tr. Casaubon"):
            continue
        if PAGE_NUMBER_RE.fullmatch(line):
            continue
        kept_lines.append(line)
    text = "\n".join(kept_lines)
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def split_chunks(text: str, chunk_size: int, overlap_size: int) -> list[str]:
    sentences = [part.strip() for part in SENTENCE_RE.split(text) if part.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for sentence in sentences:
        if current and current_size + len(sentence) + 1 > chunk_size:
            chunks.append(" ".join(current))
            overlap: list[str] = []
            overlap_length = 0
            for previous in reversed(current):
                if overlap_length >= overlap_size:
                    break
                overlap.insert(0, previous)
                overlap_length += len(previous) + 1
            current = overlap
            current_size = overlap_length
        current.append(sentence)
        current_size += len(sentence) + 1
    if current:
        chunks.append(" ".join(current))
    return [chunk for chunk in chunks if len(chunk) >= 120]


def build_corpus(
    input_path: Path,
    output_path: Path,
    chunk_size: int = 1000,
    overlap_size: int = 160,
) -> dict:
    reader = PdfReader(input_path)
    chunks = []
    current_book = BOOK_STARTS[12]
    for page_number in range(12, 110):
        current_book = BOOK_STARTS.get(page_number, current_book)
        text = clean_text(reader.pages[page_number - 1].extract_text() or "")
        for chunk_number, chunk in enumerate(split_chunks(text, chunk_size, overlap_size), start=1):
            chunks.append(
                {
                    "id": f"aurelius-en-p{page_number:03d}-c{chunk_number:02d}",
                    "source": SOURCE,
                    "page": page_number,
                    "chapter": current_book,
                    "text": chunk,
                }
            )

    payload = {
        "version": 1,
        "agent": "aurelius",
        "source": SOURCE,
        "language": "en",
        "page_count": len(reader.pages),
        "indexed_pages": {"start": 12, "end": 109},
        "chunks": chunks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/rag/aurelius.en.json"))
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--overlap-size", type=int, default=160)
    args = parser.parse_args()
    payload = build_corpus(args.input, args.output, args.chunk_size, args.overlap_size)
    print(f"Indexed {len(payload['chunks'])} chunks from the English Meditations")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
