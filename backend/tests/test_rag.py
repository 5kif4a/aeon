import json
import logging
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from app.clients import gemini
from app.db.models import User
from app.services import agent_chat, rag
from app.services.rag import RagChunk, RagHit, RagIndex, VectorIndex


@pytest.fixture(autouse=True)
def _isolated_rag(monkeypatch):
    """Keep tests DB-free: no rag_chunks rows, no Gemini, fresh caches."""

    async def no_rows(agent_id: str, language: str) -> list[tuple[RagChunk, bytes]]:
        return []

    async def no_embedding(text: str, **kwargs) -> list[float]:
        raise AssertionError("embed_query must not be called")

    monkeypatch.setattr(rag, "_load_embedded_chunks", no_rows)
    monkeypatch.setattr(gemini, "embed_query", no_embedding)
    rag.invalidate_cache()
    yield
    rag.invalidate_cache()


def _settings(tmp_path: Path, **overrides) -> SimpleNamespace:
    values = {
        "rag_enabled": True,
        "rag_data_dir": str(tmp_path),
        "rag_top_k": 4,
        "rag_allow_basic": True,
        "rag_embedding_dim": 4,
    }
    values.update(overrides)
    values.setdefault("rag_semantic_weight", 1.0)
    return SimpleNamespace(**values)


PRINCE = "\u041d\u0438\u043a\u043a\u043e\u043b\u043e \u041c\u0430\u043a\u0438\u0430\u0432\u0435\u043b\u043b\u0438, \u00ab\u0413\u043e\u0441\u0443\u0434\u0430\u0440\u044c\u00bb"
AURELIUS = "\u041c\u0430\u0440\u043a \u0410\u0432\u0440\u0435\u043b\u0438\u0439, \u00ab\u0420\u0430\u0437\u043c\u044b\u0448\u043b\u0435\u043d\u0438\u044f\u00bb"
JUNG = "\u041a. \u0413. \u042e\u043d\u0433 \u0438 \u0441\u043e\u0430\u0432\u0442\u043e\u0440\u044b, \u00ab\u0427\u0435\u043b\u043e\u0432\u0435\u043a \u0438 \u0435\u0433\u043e \u0441\u0438\u043c\u0432\u043e\u043b\u044b\u00bb"


def _chunk(chunk_id: str, page: int, chapter: str, text: str) -> RagChunk:
    return RagChunk(
        chunk_id=chunk_id,
        source=PRINCE,
        page=page,
        chapter=chapter,
        text=text,
    )


def test_bm25_retrieval_handles_russian_inflections():
    index = RagIndex(
        [
            _chunk(
                "army",
                52,
                "\u0413\u041b\u0410\u0412\u0410 XII. \u041e \u043d\u0430\u0435\u043c\u043d\u044b\u0445 \u0432\u043e\u0439\u0441\u043a\u0430\u0445",
                "\u041d\u0430\u0435\u043c\u043d\u044b\u0435 \u0432\u043e\u0439\u0441\u043a\u0430 \u0431\u0435\u0441\u043f\u043e\u043b\u0435\u0437\u043d\u044b \u0438 \u043e\u043f\u0430\u0441\u043d\u044b, \u043f\u043e\u0442\u043e\u043c\u0443 \u0447\u0442\u043e \u043e\u043d\u0438 \u043d\u0435\u0441\u043e\u0433\u043b\u0430\u0441\u043d\u044b \u0438 \u043d\u0435\u0432\u0435\u0440\u043d\u044b.",
            ),
            _chunk(
                "reputation",
                83,
                "\u0413\u041b\u0410\u0412\u0410 XXI. \u041e \u0445\u043e\u0440\u043e\u0448\u0435\u0439 \u0440\u0435\u043f\u0443\u0442\u0430\u0446\u0438\u0438",
                "\u0413\u043e\u0441\u0443\u0434\u0430\u0440\u044c \u0434\u043e\u043b\u0436\u0435\u043d \u043f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u0442\u044c \u0441\u0435\u0431\u044f \u043f\u043e\u043a\u0440\u043e\u0432\u0438\u0442\u0435\u043b\u0435\u043c \u0442\u0430\u043b\u0430\u043d\u0442\u043e\u0432 \u0438 \u0440\u0435\u043c\u0435\u0441\u0435\u043b.",
            ),
        ]
    )

    hits = index.search(
        "\u041f\u043e\u0447\u0435\u043c\u0443 \u043d\u0430\u0435\u043c\u043d\u0430\u044f \u0430\u0440\u043c\u0438\u044f \u0438 \u043d\u0430\u0435\u043c\u043d\u044b\u0435 \u0432\u043e\u0439\u0441\u043a\u0430 \u043e\u043f\u0430\u0441\u043d\u044b?",
        top_k=1,
    )

    assert hits[0].chunk.chunk_id == "army"
    assert hits[0].score > 0


def test_stoic_concept_expansion_handles_conversational_question():
    index = RagIndex(
        [
            RagChunk(
                chunk_id="impressions",
                source=AURELIUS,
                page=58,
                chapter="\u041a\u043d\u0438\u0433\u0430 VIII",
                text=(
                    "\u041d\u0435 \u0433\u043e\u0432\u043e\u0440\u0438 \u0441\u0435\u0431\u0435 \u043d\u0438\u0447\u0435\u0433\u043e \u0441\u0432\u0435\u0440\u0445 \u0442\u043e\u0433\u043e, \u0447\u0442\u043e \u0441\u043e\u043e\u0431\u0449\u0430\u044e\u0442 "
                    "\u043f\u0435\u0440\u0432\u043e\u043d\u0430\u0447\u0430\u043b\u044c\u043d\u044b\u0435 \u043f\u0440\u0435\u0434\u0441\u0442\u0430\u0432\u043b\u0435\u043d\u0438\u044f."
                ),
            ),
            RagChunk(
                chunk_id="distractor",
                source=AURELIUS,
                page=10,
                chapter="\u041a\u043d\u0438\u0433\u0430 I",
                text="\u0414\u043e\u0431\u0440\u044b\u0439 \u0445\u0430\u0440\u0430\u043a\u0442\u0435\u0440 \u0438 \u0437\u0430\u0431\u043e\u0442\u0430 \u043e \u0431\u043b\u0438\u0437\u043a\u0438\u0445.",
            ),
        ]
    )

    hits = index.search(
        "\u041a\u0430\u043a \u043d\u0435 \u043f\u043e\u0437\u0432\u043e\u043b\u0438\u0442\u044c \u043f\u0435\u0440\u0432\u043e\u043c\u0443 \u0432\u043f\u0435\u0447\u0430\u0442\u043b\u0435\u043d\u0438\u044e \u0443\u043f\u0440\u0430\u0432\u043b\u044f\u0442\u044c \u043c\u043e\u0438\u043c \u0440\u0430\u0437\u0443\u043c\u043e\u043c?",
        top_k=1,
    )

    assert hits[0].chunk.chunk_id == "impressions"


def test_discourses_concept_expansion_handles_conversational_leader_question():
    index = RagIndex(
        [
            _chunk(
                "multitude",
                186,
                "Book 1, Chapter XLIV",
                "The multitude is helpless without a head and needs spokesmen.",
            ),
            _chunk(
                "distractor",
                198,
                "Book 1, Chapter LVIII",
                "The people can judge public affairs with wisdom and constancy.",
            ),
        ]
    )

    hits = index.search(
        "Why is a crowd or multitude ineffective when it has no recognized leader?",
        top_k=1,
    )

    assert hits[0].chunk.chunk_id == "multitude"


async def test_retrieve_is_limited_to_supported_agents(monkeypatch, tmp_path: Path):
    payload = {
        "source": PRINCE,
        "chunks": [
            {
                "id": "fox",
                "page": 71,
                "chapter": "\u0413\u041b\u0410\u0412\u0410 XVIII",
                "text": "\u0413\u043e\u0441\u0443\u0434\u0430\u0440\u044c \u0434\u043e\u043b\u0436\u0435\u043d \u0441\u043e\u0435\u0434\u0438\u043d\u044f\u0442\u044c \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0430 \u043b\u044c\u0432\u0430 \u0438 \u043b\u0438\u0441\u0438\u0446\u044b.",
            }
        ],
    }
    (tmp_path / "machiavelli.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    aurelius_payload = {
        "source": AURELIUS,
        "chunks": [
            {
                "id": "present",
                "page": 17,
                "chapter": "\u041a\u043d\u0438\u0433\u0430 III",
                "text": "\u041a\u0430\u0436\u0434\u044b\u0439 \u0436\u0438\u0432\u0435\u0442 \u0442\u043e\u043b\u044c\u043a\u043e \u0432 \u043d\u0430\u0441\u0442\u043e\u044f\u0449\u0435\u043c.",
            }
        ],
    }
    (tmp_path / "aurelius.json").write_text(
        json.dumps(aurelius_payload, ensure_ascii=False), encoding="utf-8"
    )
    jung_payload = {
        "source": JUNG,
        "chunks": [
            {
                "id": "shadow",
                "page": 179,
                "chapter": "3. \u041f\u0440\u043e\u0446\u0435\u0441\u0441 \u0438\u043d\u0434\u0438\u0432\u0438\u0434\u0443\u0430\u0446\u0438\u0438 \u2014 \u041c\u0430\u0440\u0438\u044f-\u041b\u0443\u0438\u0437\u0430 \u0444\u043e\u043d \u0424\u0440\u0430\u043d\u0446",
                "text": "\u0422\u0435\u043d\u044c \u0441\u043e\u0434\u0435\u0440\u0436\u0438\u0442 \u043d\u0435\u043f\u0440\u0438\u0437\u043d\u0430\u043d\u043d\u044b\u0435 \u0447\u0435\u0440\u0442\u044b \u043b\u0438\u0447\u043d\u043e\u0441\u0442\u0438.",
            }
        ],
    }
    (tmp_path / "jung.json").write_text(
        json.dumps(jung_payload, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(rag, "get_settings", lambda: _settings(tmp_path))

    question = "\u041a\u043e\u0433\u0434\u0430 \u0431\u044b\u0442\u044c \u043b\u044c\u0432\u043e\u043c, \u0430 \u043a\u043e\u0433\u0434\u0430 \u043b\u0438\u0441\u043e\u0439?"
    assert await rag.retrieve("machiavelli", question)
    assert await rag.retrieve(
        "aurelius",
        "\u041a\u0430\u043a \u0436\u0438\u0442\u044c \u0432 \u043d\u0430\u0441\u0442\u043e\u044f\u0449\u0435\u043c?",
    )
    assert await rag.retrieve(
        "jung", "\u0427\u0442\u043e \u0442\u0430\u043a\u043e\u0435 \u0422\u0435\u043d\u044c?"
    )
    assert await rag.retrieve("unknown", question) == []


async def test_retrieve_selects_english_index_for_english_locale(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(rag, "get_settings", lambda: _settings(tmp_path))

    for suffix, chunk_id, text in (
        ("", "russian", "Живи настоящим мгновением."),
        (".en", "english", "Confine thyself to the present."),
    ):
        payload = {
            "source": AURELIUS,
            "chunks": [
                {
                    "id": chunk_id,
                    "page": 104,
                    "chapter": "Book XII",
                    "text": text,
                }
            ],
        }
        (tmp_path / f"aurelius{suffix}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    hits = await rag.retrieve("aurelius", "How should I focus on the present?", language="en")

    assert hits[0].chunk.chunk_id == "english"


async def test_retrieve_selects_english_jung_index(monkeypatch, tmp_path: Path):
    payload = {
        "source": "C. G. Jung, Man and His Symbols",
        "chunks": [
            {
                "id": "shadow-en",
                "page": 153,
                "chapter": "3. The Process of Individuation",
                "text": "The shadow represents unknown qualities of the ego.",
            }
        ],
    }
    (tmp_path / "jung.en.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(rag, "get_settings", lambda: _settings(tmp_path))

    hits = await rag.retrieve("jung", "What does the shadow represent?", language="en")

    assert hits[0].chunk.chunk_id == "shadow-en"


def test_rag_access_respects_plan():
    assert not rag.plan_has_rag_access("Basic")
    assert not rag.plan_has_rag_access("Free")
    assert rag.plan_has_rag_access("Trial")
    assert rag.plan_has_rag_access("Pro")
    assert rag.plan_has_rag_access("Basic", allow_basic=True)


def test_agent_prompt_marks_retrieved_text_as_reference():
    user = User(id=1, language="ru", plan="Pro")
    book_context = (
        "[\u0413\u043e\u0441\u0443\u0434\u0430\u0440\u044c; page 71, \u0413\u041b\u0410\u0412\u0410 XVIII]\n"
        "\u041b\u0435\u0432 \u0438 \u043b\u0438\u0441\u0438\u0446\u0430."
    )

    prompt = agent_chat._build_user_prompt(
        "machiavelli",
        "\u041a\u0430\u043a \u0432\u0435\u0441\u0442\u0438 \u043f\u0435\u0440\u0435\u0433\u043e\u0432\u043e\u0440\u044b?",
        user,
        [],
        "ru",
        book_context=book_context,
    )

    assert "Retrieved reference excerpts" in prompt
    assert book_context in prompt
    assert "Do not invent" in prompt


# --- Hybrid retrieval ------------------------------------------------------------


def _vector_rows(*items: tuple[str, str, list[float]]) -> list[tuple[RagChunk, bytes]]:
    return [
        (
            RagChunk(chunk_id=chunk_id, source=PRINCE, page=index, chapter="", text=text),
            rag.pack_embedding(vector),
        )
        for index, (chunk_id, text, vector) in enumerate(items, start=1)
    ]


def test_vector_index_ranks_by_cosine_similarity():
    chunks = [
        RagChunk(chunk_id="a", source=PRINCE, page=1, chapter="", text="a"),
        RagChunk(chunk_id="b", source=PRINCE, page=2, chapter="", text="b"),
        RagChunk(chunk_id="c", source=PRINCE, page=3, chapter="", text="c"),
    ]
    # Row norms differ on purpose: cosine must ignore magnitude.
    matrix = np.array([[10.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]], dtype=np.float32)
    index = VectorIndex(chunks, matrix)

    hits = index.search([0.0, 2.0, 0.0], top_k=2)

    assert [hit.chunk.chunk_id for hit in hits] == ["b", "c"]
    assert hits[0].score == pytest.approx(1.0)
    assert hits[1].score == pytest.approx(1 / np.sqrt(2))


def test_pack_embedding_roundtrip_is_normalized():
    blob = rag.pack_embedding([3.0, 4.0])

    assert len(blob) == 8
    assert rag.unpack_embedding(blob, 2) == pytest.approx([0.6, 0.8])
    assert rag.unpack_embedding(blob, 3) is None


def test_rrf_fusion_prefers_chunks_ranked_by_both_signals():
    def hit(chunk_id: str, score: float) -> RagHit:
        return RagHit(RagChunk(chunk_id, PRINCE, 1, "", chunk_id), score)

    semantic = [hit("s1", 0.9), hit("both", 0.8), hit("s3", 0.7)]
    lexical = [hit("l1", 12.0), hit("both", 11.0), hit("l3", 10.0)]

    fused = rag.rrf_fuse([semantic, lexical], top_k=3)

    assert fused[0].chunk.chunk_id == "both"
    assert fused[0].score == pytest.approx(2 / 62)
    assert {hit.chunk.chunk_id for hit in fused[1:]} == {"s1", "l1"}
    assert len(rag.rrf_fuse([semantic, lexical], top_k=10)) == 5


def test_rrf_fusion_weights_scale_one_ranking():
    def hit(chunk_id: str, score: float) -> RagHit:
        return RagHit(RagChunk(chunk_id, PRINCE, 1, "", chunk_id), score)

    semantic = [hit("s1", 0.9)]
    lexical = [hit("l1", 12.0)]

    fused = rag.rrf_fuse([semantic, lexical], top_k=2, weights=[0.5, 1.0])

    assert [hit.chunk.chunk_id for hit in fused] == ["l1", "s1"]
    assert fused[0].score == pytest.approx(1 / 61)
    assert fused[1].score == pytest.approx(0.5 / 61)


async def test_retrieve_fuses_embeddings_with_bm25(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(rag, "get_settings", lambda: _settings(tmp_path))
    rows = _vector_rows(
        ("semantic", "Fortune favours the bold and punishes the idle.", [1.0, 0.0, 0.0, 0.0]),
        ("lexical", "Mercenary soldiers are useless and dangerous.", [0.0, 1.0, 0.0, 0.0]),
        ("noise", "The weather in Florence was mild.", [0.0, 0.0, 1.0, 0.0]),
    )

    async def rows_from_db(agent_id: str, language: str):
        assert (agent_id, language) == ("machiavelli", "en")
        return rows

    async def embed(text: str, **kwargs) -> list[float]:
        return [1.0, 0.0, 0.0, 0.0]

    monkeypatch.setattr(rag, "_load_embedded_chunks", rows_from_db)
    monkeypatch.setattr(gemini, "embed_query", embed)

    hits = await rag.retrieve("machiavelli", "Why are mercenary soldiers dangerous?", 2, "en")

    assert {hit.chunk.chunk_id for hit in hits} == {"semantic", "lexical"}
    assert "noise" not in {hit.chunk.chunk_id for hit in hits}


async def test_retrieve_falls_back_to_bm25_when_embedding_fails(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(rag, "get_settings", lambda: _settings(tmp_path))
    rows = _vector_rows(
        ("semantic", "Fortune favours the bold.", [1.0, 0.0, 0.0, 0.0]),
        ("lexical", "Mercenary soldiers are useless and dangerous.", [0.0, 1.0, 0.0, 0.0]),
    )

    async def rows_from_db(agent_id: str, language: str):
        return rows

    async def embed(text: str, **kwargs) -> list[float]:
        raise gemini.GeminiError("boom", status=503)

    monkeypatch.setattr(rag, "_load_embedded_chunks", rows_from_db)
    monkeypatch.setattr(gemini, "embed_query", embed)

    hits = await rag.retrieve("machiavelli", "Why are mercenary soldiers dangerous?", 1, "en")

    assert [hit.chunk.chunk_id for hit in hits] == ["lexical"]


async def test_retrieve_uses_json_file_when_table_is_empty(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(rag, "get_settings", lambda: _settings(tmp_path))
    payload = {
        "source": PRINCE,
        "chunks": [{"id": "fox", "page": 71, "chapter": "XVIII", "text": "The lion and the fox."}],
    }
    (tmp_path / "machiavelli.en.json").write_text(json.dumps(payload), encoding="utf-8")

    hits = await rag.retrieve("machiavelli", "When should a prince be a fox?", language="en")

    assert [hit.chunk.chunk_id for hit in hits] == ["fox"]


async def test_retrieve_warns_once_when_corpus_is_missing(monkeypatch, tmp_path: Path, caplog):
    monkeypatch.setattr(rag, "get_settings", lambda: _settings(tmp_path))

    with caplog.at_level(logging.WARNING, logger="app.services.rag"):
        first = await rag.retrieve("jung", "What is the shadow?", language="en")
        second = await rag.retrieve("jung", "What is the anima?", language="en")

    assert first == [] and second == []
    warnings = [record for record in caplog.records if "is unavailable" in record.getMessage()]
    assert len(warnings) == 1
    assert "jung/en" in warnings[0].getMessage()


async def test_build_context_formats_hits(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(rag, "get_settings", lambda: _settings(tmp_path))
    payload = {
        "source": PRINCE,
        "chunks": [{"id": "fox", "page": 71, "chapter": "XVIII", "text": "The lion and the fox."}],
    }
    (tmp_path / "machiavelli.en.json").write_text(json.dumps(payload), encoding="utf-8")

    context = await rag.build_context("machiavelli", "lion and fox", "Pro", language="en")

    assert context == f"[{PRINCE}; page 71, XVIII]\nThe lion and the fox."
    monkeypatch.setattr(rag, "get_settings", lambda: _settings(tmp_path, rag_allow_basic=False))
    assert await rag.build_context("machiavelli", "lion and fox", "Free", language="en") == ""
    assert await rag.build_context("machiavelli", "lion and fox", "Pro", language="en") == context
