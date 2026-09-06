"""Extract a PDF into the local JSON chunk format used by app.services.rag."""

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

CHAPTER_RE = re.compile(r"^(ГЛАВА\s+[IVXLCDM]+\.?[^\n]*)", re.IGNORECASE)
BOOK_RE = re.compile(r"^Книга\s+(первая|вторая|третья|четвертая|четвёртая|пятая)\b", re.IGNORECASE)
BOOK_NUMERALS = {
    "первая": "I",
    "вторая": "II",
    "третья": "III",
    "четвертая": "IV",
    "четвёртая": "IV",
    "пятая": "V",
}
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")


def clean_page_text(text: str) -> str:
    text = text.replace("\u00ad", "").replace("\u00a0", " ")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def book_from_page(raw_text: str, current: str) -> str:
    """Track "Книга первая/вторая/..." headings in multi-book works such as the Discourses."""
    for line in raw_text.splitlines():
        match = BOOK_RE.match(re.sub(r"\s+", " ", line).strip())
        if match:
            return f"Книга {BOOK_NUMERALS[match.group(1).lower()]}"
    return current


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


def parse_work(value: str) -> tuple[str, int, int | None]:
    """`--work "Title:start[:end]"`; pages are 1-based and inclusive."""
    parts = value.rsplit(":", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise argparse.ArgumentTypeError(f"expected 'Title:start[:end]', got {value!r}")
    if len(parts) == 3 and parts[2].isdigit():
        return parts[0], int(parts[1]), int(parts[2])
    if len(parts) == 3:
        return f"{parts[0]}:{parts[1]}", int(parts[2]), None
    return parts[0], int(parts[1]), None


def ingest(
    input_path: Path,
    output_path: Path,
    works: list[tuple[str, int, int | None]],
    chunk_size: int,
    overlap_size: int,
) -> dict:
    """Index one PDF holding one or several works, each with its own page range and source label."""
    reader = PdfReader(input_path)
    chunks = []
    for source, start_page, end_page in works:
        current_chapter = "Посвящение"
        current_book = ""
        last_page = min(end_page or len(reader.pages), len(reader.pages))
        for page_number in range(start_page, last_page + 1):
            raw_text = reader.pages[page_number - 1].extract_text() or ""
            book = book_from_page(raw_text, current_book)
            if book != current_book:
                current_book, current_chapter = book, "Вступление"
            current_chapter = chapter_from_page(raw_text, current_chapter)
            chapter = f"{current_book}, {current_chapter}" if current_book else current_chapter
            text = clean_page_text(raw_text)
            for chunk_number, chunk in enumerate(
                split_chunks(text, chunk_size, overlap_size), start=1
            ):
                chunks.append(
                    {
                        "id": f"machiavelli-p{page_number:03d}-c{chunk_number:02d}",
                        "source": source,
                        "page": page_number,
                        "chapter": chapter,
                        "text": chunk,
                    }
                )

    payload = {
        "version": 1,
        "agent": "machiavelli",
        "source": "; ".join(source for source, _, _ in works),
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
    parser.add_argument(
        "--work",
        action="append",
        type=parse_work,
        default=None,
        help="'Title:start[:end]' for a PDF holding several works; repeatable. "
        "Overrides --source/--start-page.",
    )
    parser.add_argument("--chunk-size", type=int, default=1400)
    parser.add_argument("--overlap-size", type=int, default=220)
    args = parser.parse_args()
    works = args.work or [(args.source, args.start_page, None)]
    payload = ingest(args.input, args.output, works, args.chunk_size, args.overlap_size)
    print(f"Indexed {len(payload['chunks'])} chunks from {payload['page_count']} pages")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
