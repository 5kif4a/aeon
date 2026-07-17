"""Extract a PDF into the local JSON chunk format used by app.services.rag."""

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

CHAPTER_RE = re.compile(r"^(ГЛАВА\s+[IVXLCDM]+\.?[^\n]*)", re.IGNORECASE)
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")


def clean_page_text(text: str) -> str:
    text = text.replace("\u00ad", "").replace("\u00a0", " ")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def chapter_from_page(raw_text: str, current: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in raw_text.splitlines()]
    for index, line in enumerate(lines):
        match = CHAPTER_RE.match(line)
        if match:
            title_parts = [match.group(1)]
            for continuation in lines[index + 1 : index + 6]:
                words = continuation.split()
                starts_body = bool(words) and (
                    (len(words[0]) > 1 and words[0].isupper())
                    or (len(words) > 1 and words[0].isupper() and words[1].isupper())
                )
                if not continuation or starts_body:
                    break
                title_parts.append(continuation)
            return " ".join(title_parts)[:220]
    return current


def split_chunks(text: str, chunk_size: int, overlap_size: int) -> list[str]:
    sentences = [sentence.strip() for sentence in SENTENCE_RE.split(text) if sentence.strip()]
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


def ingest(
    input_path: Path,
    output_path: Path,
    source: str,
    start_page: int,
    chunk_size: int,
    overlap_size: int,
) -> dict:
    reader = PdfReader(input_path)
    chunks = []
    current_chapter = "Посвящение"
    for page_number, page in enumerate(reader.pages, start=1):
        if page_number < start_page:
            continue
        raw_text = page.extract_text() or ""
        current_chapter = chapter_from_page(raw_text, current_chapter)
        text = clean_page_text(raw_text)
        for chunk_number, chunk in enumerate(split_chunks(text, chunk_size, overlap_size), start=1):
            chunks.append(
                {
                    "id": f"machiavelli-p{page_number:03d}-c{chunk_number:02d}",
                    "source": source,
                    "page": page_number,
                    "chapter": current_chapter,
                    "text": chunk,
                }
            )

    payload = {
        "version": 1,
        "agent": "machiavelli",
        "source": source,
        "language": "ru",
        "page_count": len(reader.pages),
        "chunks": chunks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/rag/machiavelli.json"))
    parser.add_argument("--source", default="Никколо Макиавелли, «Государь»")
    parser.add_argument("--start-page", type=int, default=4)
    parser.add_argument("--chunk-size", type=int, default=1400)
    parser.add_argument("--overlap-size", type=int, default=220)
    args = parser.parse_args()
    payload = ingest(
        args.input,
        args.output,
        args.source,
        args.start_page,
        args.chunk_size,
        args.overlap_size,
    )
    print(f"Indexed {len(payload['chunks'])} chunks from {payload['page_count']} pages")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
