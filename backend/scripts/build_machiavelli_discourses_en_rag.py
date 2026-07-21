"""Build the English Machiavelli RAG corpus from the 1883 Discourses."""

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

SOURCE = (
    "Niccolo Machiavelli, Discourses on the First Decade of Titus Livius "
    "(Ninian Hill Thomson trans., 1883)"
)
BOOK_RANGES = (
    (1, 25, 207),
    (2, 209, 347),
    (3, 349, 509),
)
CHAPTER_OVERRIDES = {
    (1, 72): "XI",
    (1, 177): "LII",
    (1, 180): "LIII",
    (2, 254): "XI",
    (2, 310): "XXIV",
    (2, 320): "XXV",
    (2, 328): "XXVIII",
    (3, 422): "XVI",
    (3, 426): "XVII",
    (3, 458): "XXIX",
    (3, 493): "XL",
    (3, 503): "XLVI",
    (3, 505): "XLVIII",
}
CHAPTER_RE = re.compile(
    r"\bChapter\s+([IVXLCDMivxlcdml]+)\s*(?:[.]\s*(?:[-\u2014]\s*)?|[-\u2014]\s*)",
    re.IGNORECASE,
)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
HEADER_RE = re.compile(
    r"(?:DISCOURSES\s+ON\s+THE\s+FIRST\s+DECADE|"
    r"(?:TITUS|T/ras|TJ?TUS)\s+LIVI(?:US|VS)|"
    r"^\s*(?:CH|OH|CB|CU)[.]\s*[IVXLCDMivxlcdm]+[.]?\])",
    re.IGNORECASE,
)


def normalize_roman(token: str) -> str:
    """Normalize the edition's common lowercase-l OCR error for Roman I."""
    return token.replace("l", "I").replace("i", "I").upper()


def clean_page_text(raw_text: str) -> str:
    lines = []
    for raw_line in raw_text.splitlines():
        line = raw_line.replace("\u00ad", "").replace("\u00a0", " ").strip()
        if not line or HEADER_RE.search(line):
            continue
        lines.append(line)

    text = "\n".join(lines)
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


def page_sections(text: str, book: int, current_chapter: str) -> list[tuple[str, str]]:
    matches = list(CHAPTER_RE.finditer(text))
    if not matches:
        return [(current_chapter, text)] if text else []

    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        prefix = text[: matches[0].start()].strip()
        if prefix:
            sections.append((current_chapter, prefix))

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        chapter = f"Book {book}, Chapter {normalize_roman(match.group(1))}"
        section = text[match.start() : end].strip()
        if section:
            sections.append((chapter, section))
    return sections


def overridden_page_sections(
    text: str, book: int, chapter_number: str, current_chapter: str
) -> list[tuple[str, str]]:
    marker = re.search(
        r"\bChapter\s+.{1,12}?(?:[.]\s*[-\u2014]|[-\u2014])",
        text,
        re.IGNORECASE,
    ) or re.search(r"\bChapter\b", text, re.IGNORECASE)
    chapter = f"Book {book}, Chapter {chapter_number}"
    if marker is None:
        return [(chapter, text)] if text else []

    sections = []
    prefix = text[: marker.start()].strip()
    if prefix:
        sections.append((current_chapter, prefix))
    sections.append((chapter, text[marker.start() :].strip()))
    return sections


def build_corpus(
    input_path: Path,
    output_path: Path,
    chunk_size: int = 1100,
    overlap_size: int = 180,
) -> dict:
    reader = PdfReader(input_path)
    chunks = []
    indexed_pages = []

    for book, start_page, end_page in BOOK_RANGES:
        current_chapter = f"Book {book}, Preface"
        indexed_pages.append({"book": book, "start": start_page, "end": end_page})
        for page_number in range(start_page, end_page + 1):
            text = clean_page_text(reader.pages[page_number - 1].extract_text() or "")
            override = CHAPTER_OVERRIDES.get((book, page_number))
            if override:
                sections = overridden_page_sections(text, book, override, current_chapter)
            else:
                sections = page_sections(text, book, current_chapter)
            chunk_number = 0
            for chapter, section in sections:
                current_chapter = chapter
                for chunk in split_chunks(section, chunk_size, overlap_size):
                    chunk_number += 1
                    chunks.append(
                        {
                            "id": (
                                f"machiavelli-discourses-en-b{book}-"
                                f"p{page_number:03d}-c{chunk_number:02d}"
                            ),
                            "source": SOURCE,
                            "page": page_number,
                            "chapter": chapter,
                            "text": chunk,
                        }
                    )

    payload = {
        "version": 1,
        "agent": "machiavelli",
        "work": "discourses",
        "source": SOURCE,
        "language": "en",
        "page_count": len(reader.pages),
        "indexed_pages": indexed_pages,
        "chunks": chunks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/rag/machiavelli.en.json"))
    parser.add_argument("--chunk-size", type=int, default=1100)
    parser.add_argument("--overlap-size", type=int, default=180)
    args = parser.parse_args()
    payload = build_corpus(args.input, args.output, args.chunk_size, args.overlap_size)
    print(f"Indexed {len(payload['chunks'])} chunks from Machiavelli's Discourses")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
