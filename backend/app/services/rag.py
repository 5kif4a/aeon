"""Hybrid retrieval over agent book corpora: Gemini embeddings + BM25, fused with RRF.

Chunk texts and their embeddings live in the ``rag_chunks`` Postgres table (written by
``scripts/embed_rag.py``) and are loaded per (agent, language) into an in-memory numpy
matrix. The BM25 index is built from the same chunks, or from the local JSON corpus in
``RAG_DATA_DIR`` when it exists. If the query embedding fails, or the table has no rows for
a corpus, retrieval degrades to BM25 only; with no corpus at all it returns nothing and
logs a warning once.
"""

import asyncio
import json
import logging
import math
import re
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sqlalchemy import select

from app.clients import gemini
from app.core.config import get_settings
from app.db.models import RagChunkRecord
from app.db.session import SessionFactory

logger = logging.getLogger(__name__)

SUPPORTED_AGENTS = frozenset({"aurelius", "jung", "machiavelli"})
# Seconds an in-memory corpus stays valid before rag_chunks is re-read.
CORPUS_CACHE_TTL = 300.0
# Timeout for embedding the user's question; on expiry retrieval falls back to BM25.
QUERY_EMBED_TIMEOUT = 5.0
# Candidates taken from each signal before reciprocal rank fusion.
FUSION_CANDIDATES = 20
RRF_K = 60

WORD_RE = re.compile(r"[a-z\u0400-\u04ff0-9]+", re.IGNORECASE)
STOP_WORDS = set(
    (
        "\u0430 \u0431\u0435\u0437 \u0431\u044b \u0432 \u0432\u043e \u0434\u043b\u044f \u0434\u043e \u0435\u0433\u043e \u0435\u0435 \u0438 \u0438\u043b\u0438 \u043a\u0430\u043a \u043a \u043b\u0438 \u043d\u0430 \u043d\u0435 \u043d\u043e \u043e \u043e\u0431 \u043e\u0442 \u043f\u043e \u043f\u0440\u0438 \u0441 \u0441\u043e \u0442\u043e \u0443 \u0447\u0442\u043e \u044d\u0442\u043e "
        "the a an and or of to in is are how what why"
        " who whom whose which when where do does did be been being for from by with as at it its"
    ).split()
)
RU_SUFFIXES = tuple(
    sorted(
        {
            "\u0438\u044f\u043c\u0438",
            "\u044f\u043c\u0438",
            "\u0430\u043c\u0438",
            "\u0435\u0433\u043e",
            "\u043e\u0433\u043e",
            "\u0435\u043c\u0443",
            "\u043e\u043c\u0443",
            "\u0438\u043c\u0438",
            "\u044b\u043c\u0438",
            "\u0438\u0439",
            "\u044b\u0439",
            "\u043e\u0439",
            "\u0430\u044f",
            "\u044f\u044f",
            "\u043e\u0435",
            "\u0435\u0435",
            "\u0438\u0435",
            "\u044b\u0435",
            "\u0443\u044e",
            "\u044e\u044e",
            "\u0430\u043c",
            "\u044f\u043c",
            "\u0430\u0445",
            "\u044f\u0445",
            "\u043e\u0432",
            "\u0435\u0432",
            "\u0435\u0439",
            "\u043e\u043c",
            "\u0435\u043c",
            "\u044b",
            "\u0438",
            "\u0430",
            "\u044f",
            "\u0443",
            "\u044e",
            "\u0435",
            "\u043e",
        },
        key=len,
        reverse=True,
    )
)
QUERY_STOP_STEMS = {
    "\u0433\u043e\u0441\u0443\u0434\u0430\u0440",
    "\u043f\u0440\u0430\u0432\u0438\u0442\u0435\u043b",
    "\u043d\u0443\u0436\u043d",
    "\u043a\u043e\u0433\u0434",
    "\u043f\u043e\u0447\u0435\u043c",
    "\u043b\u0443\u0447\u0448\u0435",
    "\u0431\u044b\u0442\u044c",
    "machiavelli",
    "prince",
    "chapter",
    "book",
    "should",
    "would",
}
QUERY_EXPANSIONS = {
    "\u043b\u0438\u0441": {"\u043b\u0438\u0441\u0438\u0446"},
    "\u043b\u0438\u0441\u0438\u0446": {"\u043b\u0438\u0441"},
    "\u0444\u043e\u0440\u0442\u0443\u043d": {"\u0441\u0443\u0434\u044c\u0431"},
    "\u0441\u0443\u0434\u044c\u0431": {"\u0444\u043e\u0440\u0442\u0443\u043d"},
    "\u043f\u0440\u043e\u0442\u0438\u0432\u043e\u0441\u0442\u043e\u044f\u0442\u044c": {
        "\u0441\u043e\u043f\u0440\u043e\u0442\u0438\u0432\u043b"
    },
    "people": {"multitude", "pleb"},
    "multitude": {"people", "pleb"},
    "freedom": {"liberti", "free"},
    "liberti": {"freedom", "free"},
    "religion": {"faith", "oath"},
    "fortune": {"luck", "chance"},
    "mercenari": {"auxiliari", "hire"},
}
QUERY_CONCEPTS = (
    (
        {"настоящ", "прошл", "будущ", "нынешн"},
        {"настоящ", "мгновенн", "прожит", "неявственн"},
    ),
    (
        {"убежищ", "уедин", "спокойн"},
        {"уединен", "душ", "покойн", "берег", "гор"},
    ),
    (
        {"постел", "вставать", "просыпаться"},
        {"рассвет", "вставать", "постел", "рожден", "человеческ"},
    ),
    (
        {"обижаться", "оскорбил", "задел"},
        {"обижает", "бранит", "зацепят", "вред", "представлен"},
    ),
    (
        {"впечатлен", "впечатлени", "воображен", "воображени"},
        {
            "представлен",
            "первоначальн",
            "сообщаетс",
            "сверх",
            "разум",
            "впечатлени",
        },
    ),
    (
        {"оценк", "факт", "произошл"},
        {"представлен", "признан", "сужден", "мнен", "сообщаетс"},
    ),
    (
        {"проступок", "проступк", "чуж", "чужим"},
        {"проступок", "чуж", "оставить", "ведущ"},
    ),
    (
        {"гнев", "ошибающ", "сердиться"},
        {"гнев", "негодован", "ошиб", "кротост", "благожелательност"},
    ),
    (
        {"желан", "отвращен", "зависит"},
        {"стремлен", "избеган", "желан", "влечен", "выбор"},
    ),
    (
        {"недолжн", "неправд", "правил"},
        {"надлежит", "правд", "говор", "делай", "устремлен"},
    ),
    (
        {"знак", "обозначен"},
        {"знак", "обозначен", "дополнительн", "неопределенн", "неизвестн"},
    ),
    (
        {"компенсирует", "компенсац", "односторонн"},
        {"компенсаторн", "компенсирующ", "равновес", "установк", "сознательн"},
    ),
    (
        {"сонник", "универсальн"},
        {"индивидуальн", "сновидец", "контекст", "толкован", "ассоциац"},
    ),
    (
        {"раскол", "разлад"},
        {"разлад", "исцелен", "целостност", "подсознательн", "примирен"},
    ),
    (
        {"перейти", "перейт", "переход", "трансцендентн"},
        {"трансцендентност", "переход", "посвящен", "порог", "преобразован"},
    ),
    (
        {"самост", "самость", "целостност", "целостность"},
        {"самост", "эго", "центр", "целостност", "индивидуац"},
    ),
    (
        {"последовательност", "последовательность", "сери"},
        {"ряд", "серия", "нескольк", "повторяютс", "сновиден", "индивидуац"},
    ),
    (
        {"признавать", "признать", "непризнанн"},
        {"тень", "проекц", "нежелательн", "черты", "личност"},
    ),
    (
        {"morning", "ungrateful", "rude", "selfish"},
        {"morning", "unthankful", "railer", "crafty", "envious", "unsociable"},
    ),
    (
        {"death", "fear", "dying"},
        {"death", "nature", "natural", "dissolution", "child"},
    ),
    (
        {"retreat", "escape", "quiet"},
        {"retire", "soul", "quiet", "country", "seashore", "mountain", "inward"},
    ),
    (
        {"fame", "posthumous", "generation"},
        {"fame", "praise", "memory", "posterity", "forgotten", "vanity"},
    ),
    (
        {"impermanence", "decay", "transformation", "change"},
        {"change", "alteration", "mutation", "generation", "corruption"},
    ),
    (
        {"bed", "rise", "work"},
        {"morning", "unwilling", "rise", "work", "born", "labour"},
    ),
    (
        {"obstacle", "hindrance", "give"},
        {"hindrance", "operation", "furtherance", "purpose", "action"},
    ),
    (
        {"society", "social", "common"},
        {"common", "good", "sociable", "society", "public", "community"},
    ),
    (
        {"insult", "offense", "offence", "hurt"},
        {"offend", "offence", "hurt", "injury", "injurious", "conceit"},
    ),
    (
        {"impression", "imagination", "controll"},
        {"fancy", "imagination", "representation", "conceit", "mind"},
    ),
    (
        {"judg", "actually", "happened"},
        {"conceit", "opinion", "fancy", "thing", "itself"},
    ),
    (
        {"wrongdo", "wrong", "another"},
        {
            "offence",
            "offender",
            "himself",
            "ignorance",
            "injury",
            "sin",
            "trouble",
            "look",
        },
    ),
    (
        {"anger", "mistaken", "gently"},
        {"anger", "wrath", "gentleness", "ignorance", "correct", "offender"},
    ),
    (
        {"opinion", "praise", "blame"},
        {"praise", "opinion", "judgment", "fame", "reputation"},
    ),
    (
        {"falsely", "wrongly", "truth"},
        {
            "truth",
            "false",
            "speak",
            "speaking",
            "right",
            "just",
            "justice",
            "doing",
            "righteousness",
        },
    ),
)
REQUIRED_QUERY_CONCEPTS = (
    (
        {"found", "reform", "alone"},
        {"institution", "commonwealth", "reconstruct", "one", "man"},
    ),
    (
        {"corrupt", "people", "freedom"},
        {"corrupt", "people", "obtain", "freedom", "hard", "preserve"},
    ),
    (
        {"multitude", "leader"},
        {"multitude", "helpless", "head"},
    ),
    (
        {"republic", "return", "principle"},
        {"sect", "commonwealth", "last", "brought", "back", "beginn", "renew"},
    ),
    (
        {"change", "mode", "time"},
        {"enjoi", "constant", "fortune", "change", "time"},
    ),
)


@dataclass(frozen=True)
class RagChunk:
    chunk_id: str
    source: str
    page: int
    chapter: str
    text: str


@dataclass(frozen=True)
class RagHit:
    chunk: RagChunk
    score: float


def _stem(word: str) -> str:
    word = word.lower().replace("\u0451", "\u0435")
    if word.isascii():
        return _stem_english(word)
    if not re.search(r"[\u0430-\u044f]", word) or len(word) <= 4:
        return word
    for suffix in RU_SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _stem_english(word: str) -> str:
    if not word.isascii() or not word.isalpha() or len(word) <= 3:
        return word
    if word.endswith("ities") and len(word) > 7:
        word = f"{word[:-5]}ity"
    elif word.endswith("ies") and len(word) > 5:
        word = f"{word[:-3]}y"
    elif word.endswith("sses"):
        word = word[:-2]
    elif word.endswith("s") and not word.endswith(("ss", "us")) and len(word) > 4:
        word = word[:-1]

    for suffix in ("ization", "ational", "fulness", "ousness", "iveness", "ingly", "edly"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            word = word[: -len(suffix)]
            break
    else:
        for suffix in ("ment", "ness", "able", "ible", "ity", "ous", "ing", "ed", "ly"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 4:
                word = word[: -len(suffix)]
                break
    if word.endswith("y") and len(word) > 4:
        word = f"{word[:-1]}i"
    return word


def tokenize(text: str) -> list[str]:
    return [
        _stem(word)
        for word in WORD_RE.findall(text.lower())
        if word not in STOP_WORDS and len(word) > 1
    ]


def _query_terms(query: str) -> Counter[str]:
    terms = [term for term in tokenize(query) if term not in QUERY_STOP_STEMS]
    expanded = list(terms)
    for term in terms:
        expanded.extend(QUERY_EXPANSIONS.get(term, ()))
    term_set = set(terms)
    for triggers, additions in QUERY_CONCEPTS:
        if term_set & triggers:
            expanded.extend(additions)
            expanded.extend(additions)
            expanded.extend(additions)
    for required, additions in REQUIRED_QUERY_CONCEPTS:
        if required <= term_set:
            expanded.extend(additions)
            expanded.extend(additions)
            expanded.extend(additions)
    return Counter(expanded)


class RagIndex:
    def __init__(self, chunks: list[RagChunk]):
        self.chunks = chunks
        self.term_counts = [
            Counter(tokenize(f"{chunk.source} {chunk.chapter} {chunk.chapter} {chunk.text}"))
            for chunk in chunks
        ]
        self.lengths = [sum(counts.values()) for counts in self.term_counts]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 1.0
        self.document_frequency: Counter[str] = Counter()
        for counts in self.term_counts:
            self.document_frequency.update(counts.keys())

    @classmethod
    def from_file(cls, path: Path) -> "RagIndex":
        payload = json.loads(path.read_text(encoding="utf-8"))
        chunks = [
            RagChunk(
                chunk_id=str(item["id"]),
                source=str(item.get("source") or payload.get("source") or "Unknown source"),
                page=int(item["page"]),
                chapter=str(item.get("chapter") or ""),
                text=str(item["text"]),
            )
            for item in payload.get("chunks", [])
            if item.get("text")
        ]
        return cls(chunks)

    def search(self, query: str, top_k: int = 4) -> list[RagHit]:
        query_terms = _query_terms(query)
        if not query_terms or not self.chunks:
            return []

        total = len(self.chunks)
        scores: list[tuple[float, int]] = []
        for index, counts in enumerate(self.term_counts):
            score = 0.0
            length = self.lengths[index] or 1
            for term, query_frequency in query_terms.items():
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                document_frequency = self.document_frequency[term]
                inverse_frequency = math.log(
                    1 + (total - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * length / self.average_length)
                score += inverse_frequency * (frequency * 2.5 / denominator) * query_frequency
            if score > 0:
                scores.append((score, index))

        scores.sort(key=lambda item: (-item[0], self.chunks[item[1]].page))
        return [RagHit(chunk=self.chunks[index], score=score) for score, index in scores[:top_k]]


# --- Vectors -----------------------------------------------------------------


def pack_embedding(values: Sequence[float]) -> bytes:
    """L2-normalize a vector and pack it as little-endian float32 for ``rag_chunks``."""
    return normalize(np.asarray(values, dtype=np.float32)).astype("<f4").tobytes()


def unpack_embedding(blob: bytes, dimension: int) -> np.ndarray | None:
    if len(blob) != dimension * 4:
        return None
    return np.frombuffer(blob, dtype="<f4").astype(np.float32)


def normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 else vector


class VectorIndex:
    """Cosine search over a normalized (n, dim) float32 matrix."""

    def __init__(self, chunks: list[RagChunk], matrix: np.ndarray):
        if len(chunks) != matrix.shape[0]:
            raise ValueError("chunks and matrix rows differ")
        self.chunks = chunks
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.matrix = (matrix / norms).astype(np.float32)

    def search(self, query_vector: Sequence[float], top_k: int = 4) -> list[RagHit]:
        if not self.chunks or top_k <= 0:
            return []
        query = normalize(np.asarray(query_vector, dtype=np.float32))
        if query.shape[0] != self.matrix.shape[1]:
            raise ValueError(
                f"query dimension {query.shape[0]} does not match index {self.matrix.shape[1]}"
            )
        scores = self.matrix @ query
        order = np.argsort(-scores, kind="stable")[:top_k]
        return [RagHit(chunk=self.chunks[int(i)], score=float(scores[i])) for i in order]


def rrf_fuse(
    rankings: Sequence[Sequence[RagHit]],
    top_k: int,
    k: int = RRF_K,
    weights: Sequence[float] | None = None,
) -> list[RagHit]:
    """Reciprocal rank fusion; the returned score is the fused (optionally weighted) RRF score."""
    fused: dict[str, float] = {}
    chunks: dict[str, RagChunk] = {}
    for index, ranking in enumerate(rankings):
        weight = weights[index] if weights and index < len(weights) else 1.0
        for rank, hit in enumerate(ranking, start=1):
            fused[hit.chunk.chunk_id] = fused.get(hit.chunk.chunk_id, 0.0) + weight / (k + rank)
            chunks.setdefault(hit.chunk.chunk_id, hit.chunk)
    ordered = sorted(fused.items(), key=lambda item: (-item[1], chunks[item[0]].page))
    return [RagHit(chunk=chunks[chunk_id], score=score) for chunk_id, score in ordered[:top_k]]


# --- Corpus loading and caches -------------------------------------------------


@dataclass
class Corpus:
    lexical: RagIndex | None
    vector: VectorIndex | None

    @property
    def empty(self) -> bool:
        return self.lexical is None and self.vector is None


_index_cache: dict[Path, tuple[int, RagIndex]] = {}
_corpus_cache: dict[tuple[str, str], tuple[float, Corpus]] = {}
_corpus_lock = asyncio.Lock()
_warned_corpora: set[tuple[str, str]] = set()


def invalidate_cache() -> None:
    """Drop every in-memory index; the next query reloads from disk and Postgres."""
    _index_cache.clear()
    _corpus_cache.clear()
    _warned_corpora.clear()


def normalize_language(language: str) -> str:
    return "en" if language.strip().lower().startswith("en") else "ru"


def corpus_path(agent_id: str, language: str) -> Path:
    suffix = ".en" if normalize_language(language) == "en" else ""
    return Path(get_settings().rag_data_dir) / f"{agent_id}{suffix}.json"


def _load_index(path: Path) -> RagIndex | None:
    try:
        modified = path.stat().st_mtime_ns
    except OSError:
        return None
    cached = _index_cache.get(path)
    if cached and cached[0] == modified:
        return cached[1]
    index = RagIndex.from_file(path)
    _index_cache[path] = (modified, index)
    return index


async def _load_embedded_chunks(agent_id: str, language: str) -> list[tuple[RagChunk, bytes]]:
    """Read one corpus from ``rag_chunks``. Tests monkeypatch this to stay DB-free."""
    async with SessionFactory() as session:
        result = await session.execute(
            select(RagChunkRecord)
            .where(RagChunkRecord.agent_id == agent_id, RagChunkRecord.language == language)
            .order_by(RagChunkRecord.page, RagChunkRecord.chunk_id)
        )
        rows = result.scalars().all()
    return [
        (
            RagChunk(
                chunk_id=row.chunk_id,
                source=row.source,
                page=row.page,
                chapter=row.chapter,
                text=row.text,
            ),
            row.embedding,
        )
        for row in rows
    ]


def _build_vector_index(
    agent_id: str, language: str, rows: list[tuple[RagChunk, bytes]]
) -> VectorIndex | None:
    dimension = get_settings().rag_embedding_dim
    chunks: list[RagChunk] = []
    vectors: list[np.ndarray] = []
    skipped = 0
    for chunk, blob in rows:
        vector = unpack_embedding(blob, dimension)
        if vector is None:
            skipped += 1
            continue
        chunks.append(chunk)
        vectors.append(vector)
    if skipped:
        logger.warning(
            "RAG corpus %s/%s: %d rows have an embedding size other than %d and were ignored; "
            "re-run scripts/embed_rag.py --force",
            agent_id,
            language,
            skipped,
            dimension,
        )
    if not chunks:
        return None
    return VectorIndex(chunks, np.vstack(vectors))


async def _load_corpus(agent_id: str, language: str) -> Corpus:
    lexical = _load_index(corpus_path(agent_id, language))
    vector: VectorIndex | None = None
    try:
        rows = await _load_embedded_chunks(agent_id, language)
    except Exception:
        logger.warning(
            "RAG corpus %s/%s: could not read rag_chunks; using BM25 only",
            agent_id,
            language,
            exc_info=True,
        )
        rows = []
    if rows:
        vector = _build_vector_index(agent_id, language, rows)
    if lexical is None and vector is not None:
        lexical = RagIndex(vector.chunks)
    corpus = Corpus(lexical=lexical, vector=vector)
    if corpus.empty and (agent_id, language) not in _warned_corpora:
        _warned_corpora.add((agent_id, language))
        logger.warning(
            "RAG corpus %s/%s is unavailable: no rows in rag_chunks and no file at %s; "
            "answers will not be grounded. Run scripts/embed_rag.py",
            agent_id,
            language,
            corpus_path(agent_id, language),
        )
    return corpus


async def get_corpus(agent_id: str, language: str) -> Corpus:
    key = (agent_id, normalize_language(language))
    now = time.monotonic()
    cached = _corpus_cache.get(key)
    if cached and cached[0] > now:
        return cached[1]
    async with _corpus_lock:
        cached = _corpus_cache.get(key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        corpus = await _load_corpus(*key)
        _corpus_cache[key] = (time.monotonic() + CORPUS_CACHE_TTL, corpus)
        return corpus


# --- Public API ------------------------------------------------------------------


def plan_has_rag_access(plan: str, allow_basic: bool = False) -> bool:
    return allow_basic or plan.strip().lower() not in {"", "basic", "free"}


async def _embed_query(query: str) -> list[float] | None:
    try:
        return await asyncio.wait_for(
            gemini.embed_query(query, timeout=QUERY_EMBED_TIMEOUT), QUERY_EMBED_TIMEOUT + 1
        )
    except Exception:
        logger.warning("RAG query embedding failed; falling back to BM25", exc_info=True)
        return None


async def retrieve(
    agent_id: str,
    query: str,
    top_k: int | None = None,
    language: str = "ru",
) -> list[RagHit]:
    settings = get_settings()
    if not settings.rag_enabled or agent_id not in SUPPORTED_AGENTS or not query.strip():
        return []
    limit = top_k or settings.rag_top_k
    corpus = await get_corpus(agent_id, language)
    if corpus.empty:
        return []

    candidates = max(FUSION_CANDIDATES, limit)
    lexical_hits = corpus.lexical.search(query, candidates) if corpus.lexical else []
    semantic_hits: list[RagHit] = []
    if corpus.vector is not None:
        vector = await _embed_query(query)
        if vector is not None:
            try:
                semantic_hits = corpus.vector.search(vector, candidates)
            except ValueError:
                logger.warning("RAG query embedding has an unexpected size", exc_info=True)

    if not semantic_hits:
        return lexical_hits[:limit]
    if not lexical_hits:
        return semantic_hits[:limit]
    return rrf_fuse(
        [semantic_hits, lexical_hits], limit, weights=[settings.rag_semantic_weight, 1.0]
    )


async def build_context(agent_id: str, query: str, plan: str, language: str = "ru") -> str:
    settings = get_settings()
    if not plan_has_rag_access(plan, settings.rag_allow_basic):
        return ""
    hits = await retrieve(agent_id, query, language=language)
    if not hits:
        return ""
    sections = []
    for hit in hits:
        location = f"page {hit.chunk.page}"
        if hit.chunk.chapter:
            location += f", {hit.chunk.chapter}"
        sections.append(f"[{hit.chunk.source}; {location}]\n{hit.chunk.text}")
    return "\n\n".join(sections)
