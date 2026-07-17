"""Evaluate a local RAG index against a checked-in golden dataset."""

import argparse
import json
from pathlib import Path

from app.services.rag import RagHit, RagIndex


def matches(hit: RagHit, expected: dict) -> bool:
    source = str(expected.get("source_contains", "")).lower()
    chapter = str(expected.get("chapter", ""))
    page_min = int(expected.get("page_min", 0))
    page_max = int(expected.get("page_max", 10**9))
    return (
        (not source or source in hit.chunk.source.lower())
        and (not chapter or chapter == hit.chunk.chapter)
        and page_min <= hit.chunk.page <= page_max
    )


def evaluate(index: RagIndex, dataset: dict, top_k: int = 5) -> dict:
    rows = []
    reciprocal_rank = 0.0
    hit_at_1 = 0
    hit_at_3 = 0
    for case in dataset["cases"]:
        hits = index.search(case["question"], top_k=top_k)
        rank = None
        for position, hit in enumerate(hits, start=1):
            if any(matches(hit, expected) for expected in case["expected"]):
                rank = position
                break
        if rank:
            reciprocal_rank += 1 / rank
            hit_at_1 += rank == 1
            hit_at_3 += rank <= 3
        rows.append({"id": case["id"], "question": case["question"], "rank": rank, "hits": hits})

    count = len(rows)
    return {
        "count": count,
        "hit_at_1": hit_at_1 / count if count else 0.0,
        "hit_at_3": hit_at_3 / count if count else 0.0,
        "mrr": reciprocal_rank / count if count else 0.0,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--index", type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    index_path = args.index or Path("data/rag") / f"{dataset['agent']}.json"
    result = evaluate(RagIndex.from_file(index_path), dataset, top_k=args.top_k)

    print(
        f"cases={result['count']} hit@1={result['hit_at_1']:.1%} "
        f"hit@3={result['hit_at_3']:.1%} mrr={result['mrr']:.3f}"
    )
    for row in result["rows"]:
        if row["rank"] == 1:
            continue
        print(f"\n{row['id']}: expected rank={row['rank'] or 'MISS'}")
        print(row["question"])
        for position, hit in enumerate(row["hits"][:3], start=1):
            print(
                f"  {position}. {hit.chunk.source} | {hit.chunk.chapter} | "
                f"PDF p.{hit.chunk.page} | score={hit.score:.3f}"
            )


if __name__ == "__main__":
    main()
