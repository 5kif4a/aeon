"""Build the Russian Jung agent corpus from Man and His Symbols (2016)."""

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

SOURCE = "К. Г. Юнг и соавторы, «Человек и его символы» (5-е изд., 2016)"
SECTION_STARTS = {
    14: ("1. К вопросу о подсознании", "Карл Густав Юнг"),
    105: ("2. Древние мифы и современный человек", "Джозеф Л. Хендерсон"),
    162: ("3. Процесс индивидуации", "Мария-Луиза фон Франц"),
    238: ("4. Символы в изобразительном искусстве", "Аниэла Яффе"),
    290: (
        "5. Индивидуальная символика: случай из психоаналитической практики",
        "Иоланда Якоби",
    ),
    334: ("Заключение. Наука и подсознание", "Аниэла Яффе"),
}
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")


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
    chunk_size: int = 1100,
    overlap_size: int = 180,
) -> dict:
    reader = PdfReader(input_path)
    chunks = []
    section, author = SECTION_STARTS[14]
    for page_number in range(14, 346):
        section, author = SECTION_STARTS.get(page_number, (section, author))
        text = clean_text(reader.pages[page_number - 1].extract_text() or "")
        for chunk_number, chunk in enumerate(split_chunks(text, chunk_size, overlap_size), start=1):
            chunks.append(
                {
                    "id": f"jung-p{page_number:03d}-c{chunk_number:02d}",
                    "source": SOURCE,
                    "page": page_number,
                    "chapter": f"{section} — {author}",
                    "text": chunk,
                }
            )

    payload = {
        "version": 1,
        "agent": "jung",
        "source": SOURCE,
        "language": "ru",
        "page_count": len(reader.pages),
        "indexed_pages": {"start": 14, "end": 345},
        "sections": [
            {"page": page, "title": title, "author": section_author}
            for page, (title, section_author) in SECTION_STARTS.items()
        ],
        "chunks": chunks,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/rag/jung.json"))
    parser.add_argument("--chunk-size", type=int, default=1100)
    parser.add_argument("--overlap-size", type=int, default=180)
    args = parser.parse_args()
    payload = build_corpus(args.input, args.output, args.chunk_size, args.overlap_size)
    print(f"Indexed {len(payload['chunks'])} chunks from Man and His Symbols")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
