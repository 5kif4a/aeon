"""Build the English Jung RAG corpus from the 1964 illustrated edition."""

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

SOURCE = "C. G. Jung and collaborators, Man and His Symbols (Aldus Books, 1964)"
SECTIONS = (
    (13, 91, "1. Approaching the Unconscious", "Carl G. Jung"),
    (94, 143, "2. Ancient Myths and Modern Man", "Joseph L. Henderson"),
    (145, 210, "3. The Process of Individuation", "M.-L. von Franz"),
    (213, 252, "4. Symbolism in the Visual Arts", "Aniela Jaffe"),
    (255, 284, "5. Symbols in an Individual Analysis", "Jolande Jacobi"),
    (285, 291, "Conclusion: Science and the Unconscious", "M.-L. von Franz"),
)
SENTENCE_RE = re.compile(r"(?<=[.!?\u2026])\s+")
COLUMN_SPLIT = 62


def extract_columns(page) -> list[str]:
    """Recover reading order from the fixed-width two-column text layer."""
    layout = page.extract_text(extraction_mode="layout") or ""
    left: list[str] = []
    right: list[str] = []
    for raw_line in layout.splitlines():
        line = raw_line.rstrip().ljust(COLUMN_SPLIT)
        left.append(line[:COLUMN_SPLIT].strip())
        right.append(line[COLUMN_SPLIT:].strip())

    return [clean_text("\n".join(lines)) for lines in (left, right)]


def clean_text(text: str) -> str:
    text = text.replace("\u00ad", "").replace("\u00a0", " ").replace("\ufffd", "'")
    text = text.replace("\\v", "w").replace("^v", "w")
    text = re.sub(r"\bAv(?=[a-z])", "W", text)
    text = re.sub(r"otv\b", "ow", text)
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    text = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", text)
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
    chunk_size: int = 1100,
    overlap_size: int = 180,
) -> dict:
    reader = PdfReader(input_path)
    chunks = []
    for start, end, section, author in SECTIONS:
        for page_number in range(start, end + 1):
            columns = extract_columns(reader.pages[page_number - 1])
            chunk_number = 0
            for column in columns:
                for chunk in split_chunks(column, chunk_size, overlap_size):
                    chunk_number += 1
                    chunks.append(
                        {
                            "id": f"jung-en-p{page_number:03d}-c{chunk_number:02d}",
                            "source": SOURCE,
                            "page": page_number,
                            "chapter": f"{section} - {author}",
                            "text": chunk,
                        }
                    )

    payload = {
        "version": 1,
        "agent": "jung",
        "source": SOURCE,
        "language": "en",
        "page_count": len(reader.pages),
        "indexed_pages": [
            {"start": start, "end": end, "section": section, "author": author}
            for start, end, section, author in SECTIONS
        ],
        "chunks": chunks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/rag/jung.en.json"))
    parser.add_argument("--chunk-size", type=int, default=1100)
    parser.add_argument("--overlap-size", type=int, default=180)
    args = parser.parse_args()
    payload = build_corpus(args.input, args.output, args.chunk_size, args.overlap_size)
    print(f"Indexed {len(payload['chunks'])} chunks from the English Man and His Symbols")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
