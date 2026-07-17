"""Build the Russian Marcus Aurelius RAG corpus from the 1985 edition."""

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

SOURCE = (
    "\u041c\u0430\u0440\u043a \u0410\u0432\u0440\u0435\u043b\u0438\u0439, "
    "\u00ab\u0420\u0430\u0437\u043c\u044b\u0448\u043b\u0435\u043d\u0438\u044f\u00bb "
    "(\u0438\u0437\u0434. \u00ab\u041d\u0430\u0443\u043a\u0430\u00bb, 1985)"
)
BOOK_STARTS = {
    7: "\u041a\u043d\u0438\u0433\u0430 I",
    11: "\u041a\u043d\u0438\u0433\u0430 II",
    15: "\u041a\u043d\u0438\u0433\u0430 III",
    19: "\u041a\u043d\u0438\u0433\u0430 IV",
    25: "\u041a\u043d\u0438\u0433\u0430 V",
    31: "\u041a\u043d\u0438\u0433\u0430 VI",
    47: "\u041a\u043d\u0438\u0433\u0430 VII",
    53: "\u041a\u043d\u0438\u0433\u0430 VIII",
    59: "\u041a\u043d\u0438\u0433\u0430 IX",
    65: "\u041a\u043d\u0438\u0433\u0430 X",
    73: "\u041a\u043d\u0438\u0433\u0430 XI",
    77: "\u041a\u043d\u0438\u0433\u0430 XII",
}
EXCLUDED_PAGES = set(range(35, 43))
SENTENCE_RE = re.compile(r"(?<=[.!?\u2026])\s+")


def clean_text(text: str) -> str:
    text = text.replace("\u00ad", "").replace("\u00a0", " ")
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
    current_book = BOOK_STARTS[7]
    for page_number in range(7, 83):
        if page_number in EXCLUDED_PAGES:
            continue
        current_book = BOOK_STARTS.get(page_number, current_book)
        text = clean_text(reader.pages[page_number - 1].extract_text() or "")
        for chunk_number, chunk in enumerate(split_chunks(text, chunk_size, overlap_size), start=1):
            chunks.append(
                {
                    "id": f"aurelius-p{page_number:03d}-c{chunk_number:02d}",
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
        "language": "ru",
        "page_count": len(reader.pages),
        "indexed_pages": {"start": 7, "end": 82, "excluded": sorted(EXCLUDED_PAGES)},
        "chunks": chunks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/rag/aurelius.json"))
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--overlap-size", type=int, default=160)
    args = parser.parse_args()
    payload = build_corpus(args.input, args.output, args.chunk_size, args.overlap_size)
    print(f"Indexed {len(payload['chunks'])} chunks from Marcus Aurelius's Meditations")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
