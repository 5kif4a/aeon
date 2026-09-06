"""Embed the local JSON RAG corpora with Gemini and upsert them into ``rag_chunks``.

Reads every ``<agent>.json`` / ``<agent>.en.json`` in RAG_DATA_DIR, embeds new or changed
chunks in batches (``gemini-embedding-001``, RETRIEVAL_DOCUMENT, RAG_EMBEDDING_DIM), and
upserts rows keyed by (agent_id, language, chunk_id). Chunks whose text is unchanged and
already embedded are skipped, so re-runs are cheap and idempotent. Chunks that disappeared
from the JSON file are deleted from the table.

Uses DATABASE_URL and GEMINI_API_KEY from settings, so it can be pointed at the production
database from a laptop:

    DATABASE_URL=postgresql+asyncpg://... uv run python -m scripts.embed_rag
    uv run python -m scripts.embed_rag --agent aurelius --language en --dry-run
    uv run python -m scripts.embed_rag --force      # after changing the model or dimension
"""

import argparse
import asyncio
import logging
import random
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.clients import gemini
from app.core.config import get_settings
from app.db.models import RagChunkRecord
from app.db.session import SessionFactory
from app.services import rag
from app.services.rag import SUPPORTED_AGENTS, RagChunk, RagIndex

logger = logging.getLogger("embed_rag")

BATCH_SIZE = gemini.EMBED_BATCH_LIMIT
MAX_ATTEMPTS = 6


@dataclass
class CorpusSummary:
    agent_id: str
    language: str
    total: int = 0
    embedded: int = 0
    unchanged: int = 0
    deleted: int = 0
    failed_batches: int = 0


def discover_corpora(
    data_dir: Path, agents: set[str], languages: set[str]
) -> list[tuple[str, str, Path]]:
    found: list[tuple[str, str, Path]] = []
    for agent_id in sorted(SUPPORTED_AGENTS):
        if agent_id not in agents:
            continue
        for language, suffix in (("ru", ""), ("en", ".en")):
            if language not in languages:
                continue
            path = data_dir / f"{agent_id}{suffix}.json"
            if path.is_file():
                found.append((agent_id, language, path))
    return found


async def _embed_with_retry(texts: list[str]) -> list[list[float]]:
    delay = 2.0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await gemini.embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")
        except gemini.GeminiError as exc:
            retryable = exc.status is None or exc.status == 429 or exc.status >= 500
            if not retryable or attempt == MAX_ATTEMPTS:
                raise
            logger.warning(
                "embedding batch failed (%s); retry %d/%d in %.1fs",
                exc,
                attempt,
                MAX_ATTEMPTS,
                delay,
            )
        except Exception as exc:  # network errors, timeouts
            if attempt == MAX_ATTEMPTS:
                raise
            logger.warning(
                "embedding batch failed (%s); retry %d/%d in %.1fs",
                exc,
                attempt,
                MAX_ATTEMPTS,
                delay,
            )
        await asyncio.sleep(delay + random.uniform(0, 1))
        delay = min(delay * 2, 60)
    raise RuntimeError("unreachable")


async def _existing_rows(agent_id: str, language: str) -> dict[str, tuple[str, int]]:
    """chunk_id -> (text, embedding size) for rows already in the table."""
    async with SessionFactory() as session:
        result = await session.execute(
            select(RagChunkRecord.chunk_id, RagChunkRecord.text, RagChunkRecord.embedding).where(
                RagChunkRecord.agent_id == agent_id, RagChunkRecord.language == language
            )
        )
        return {chunk_id: (text, len(blob or b"")) for chunk_id, text, blob in result.all()}


async def _upsert(
    agent_id: str, language: str, chunks: list[RagChunk], vectors: list[list[float]]
) -> None:
    rows = [
        {
            "agent_id": agent_id,
            "language": language,
            "chunk_id": chunk.chunk_id,
            "source": chunk.source,
            "chapter": chunk.chapter,
            "page": chunk.page,
            "text": chunk.text,
            "embedding": rag.pack_embedding(vector),
        }
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    statement = insert(RagChunkRecord).values(rows)
    statement = statement.on_conflict_do_update(
        constraint="uq_rag_chunks_agent_lang_chunk",
        set_={
            "source": statement.excluded.source,
            "chapter": statement.excluded.chapter,
            "page": statement.excluded.page,
            "text": statement.excluded.text,
            "embedding": statement.excluded.embedding,
        },
    )
    async with SessionFactory() as session:
        await session.execute(statement)
        await session.commit()


async def _delete_stale(agent_id: str, language: str, stale: set[str]) -> None:
    if not stale:
        return
    async with SessionFactory() as session:
        await session.execute(
            delete(RagChunkRecord).where(
                RagChunkRecord.agent_id == agent_id,
                RagChunkRecord.language == language,
                RagChunkRecord.chunk_id.in_(stale),
            )
        )
        await session.commit()


async def embed_corpus(
    agent_id: str, language: str, path: Path, force: bool, dry_run: bool
) -> CorpusSummary:
    summary = CorpusSummary(agent_id=agent_id, language=language)
    chunks = RagIndex.from_file(path).chunks
    summary.total = len(chunks)
    expected_size = get_settings().rag_embedding_dim * 4
    existing = await _existing_rows(agent_id, language)

    pending: list[RagChunk] = []
    for chunk in chunks:
        current = existing.get(chunk.chunk_id)
        if not force and current and current[0] == chunk.text and current[1] == expected_size:
            summary.unchanged += 1
        else:
            pending.append(chunk)
    stale = set(existing) - {chunk.chunk_id for chunk in chunks}
    summary.deleted = len(stale)

    logger.info(
        "%s/%s: %d chunks in %s, %d to embed, %d unchanged, %d stale%s",
        agent_id,
        language,
        summary.total,
        path,
        len(pending),
        summary.unchanged,
        len(stale),
        " (dry run)" if dry_run else "",
    )
    if dry_run:
        return summary

    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start : start + BATCH_SIZE]
        texts = [f"{chunk.source}\n{chunk.chapter}\n{chunk.text}".strip() for chunk in batch]
        try:
            vectors = await _embed_with_retry(texts)
        except Exception:
            summary.failed_batches += 1
            logger.exception(
                "%s/%s: batch %d-%d failed permanently",
                agent_id,
                language,
                start,
                start + len(batch),
            )
            continue
        await _upsert(agent_id, language, batch, vectors)
        summary.embedded += len(batch)
        logger.info("%s/%s: embedded %d/%d", agent_id, language, summary.embedded, len(pending))

    await _delete_stale(agent_id, language, stale)
    return summary


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--data-dir", type=Path, default=Path(settings.rag_data_dir))
    parser.add_argument(
        "--agent",
        action="append",
        choices=sorted(SUPPORTED_AGENTS),
        help="limit to an agent (repeatable)",
    )
    parser.add_argument(
        "--language", action="append", choices=("ru", "en"), help="limit to a language (repeatable)"
    )
    parser.add_argument(
        "--force", action="store_true", help="re-embed every chunk, even unchanged ones"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without calling Gemini or writing",
    )
    args = parser.parse_args()

    if not settings.gemini_api_key and not args.dry_run:
        raise SystemExit("GEMINI_API_KEY is not set")
    corpora = discover_corpora(
        args.data_dir, set(args.agent or SUPPORTED_AGENTS), set(args.language or ("ru", "en"))
    )
    if not corpora:
        raise SystemExit(
            f"No corpora found in {args.data_dir}; run the build_*_rag.py scripts first"
        )

    logger.info(
        "model=%s dim=%d database=%s",
        settings.rag_embedding_model,
        settings.rag_embedding_dim,
        settings.async_database_url.split("@")[-1],
    )
    summaries = [
        await embed_corpus(agent_id, language, path, force=args.force, dry_run=args.dry_run)
        for agent_id, language, path in corpora
    ]

    print("\nSummary")
    print(f"{'corpus':<16}{'total':>7}{'embedded':>10}{'unchanged':>11}{'deleted':>9}{'failed':>8}")
    for item in summaries:
        print(
            f"{item.agent_id + '/' + item.language:<16}{item.total:>7}{item.embedded:>10}"
            f"{item.unchanged:>11}{item.deleted:>9}{item.failed_batches:>8}"
        )
    if any(item.failed_batches for item in summaries):
        raise SystemExit("Some batches failed; re-run to embed the remaining chunks")


if __name__ == "__main__":
    asyncio.run(main())
