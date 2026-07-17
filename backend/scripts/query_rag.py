"""Inspect local RAG retrieval without calling the language model."""

import argparse
import sys

from app.services.rag import retrieve


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument(
        "--agent", choices=("aurelius", "jung", "machiavelli"), default="machiavelli"
    )
    parser.add_argument("--language", choices=("ru", "en"), default="ru")
    parser.add_argument("--top-k", type=int, default=4)
    args = parser.parse_args()

    hits = retrieve(args.agent, args.question, args.top_k, language=args.language)
    if not hits:
        raise SystemExit("No matches. Check RAG_ENABLED and RAG_DATA_DIR.")
    for position, hit in enumerate(hits, start=1):
        print(
            f"#{position} score={hit.score:.3f} page={hit.chunk.page} chapter={hit.chunk.chapter}"
        )
        print(hit.chunk.text)
        print()


if __name__ == "__main__":
    main()
