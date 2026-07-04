# RAG: знания из трудов личностей

Цель: ответы агентов (Аврелий, Макиавелли, Юнг) опираются на реальные фрагменты их книг,
а не только на знания LLM. Релевантные цитаты подмешиваются в промпт при каждом ответе.

## Архитектура

```
[тексты книг] → чанки → Gemini embeddings → Postgres (pgvector)
                                                    ↑
вопрос юзера → embedding вопроса → top-k похожих чанков → блок контекста в промпте
```

Стек: pgvector в существующем Postgres + `gemini-embedding-001` через существующий
httpx-клиент. Без отдельной векторной БД (Qdrant/Chroma — лишний сервис ради ~2–3 тыс.
чанков) и без LangChain/LlamaIndex (весь RAG — ~150 строк поверх текущего кода).

## Источники текстов

| Агент | Книга | Где взять | Статус прав |
|---|---|---|---|
| aurelius | Meditations | [gutenberg.org/ebooks/2680.txt.utf-8](https://www.gutenberg.org/ebooks/2680.txt.utf-8) (415 kB, plain text) | Public domain |
| machiavelli | The Prince (пер. Marriott) | [gutenberg.org/ebooks/1232.txt.utf-8](https://www.gutenberg.org/ebooks/1232.txt.utf-8) (301 kB, plain text) | Public domain |
| jung | — | Конспект-корпус (см. ниже) | Полных свободных текстов практически нет |

Русские версии: на az.lib.ru есть дореволюционные переводы («Наедине с собой»
пер. Роговина 1914 и др.) — public domain; современные переводы (Гаспаров,
Муравьёва) защищены, их не брать.

**Юнг**: умер в 1961, оригиналы ещё под копирайтом в EU до ~2032, переводы — дольше.
Практичный путь — конспект-корпус: структурированные заметки по концепциям
(тень, архетипы, индивидуация, анима/анимус, коллективное бессознательное,
синхронистичность...) своими словами, по одному md-файлу или разделу на концепцию,
с указанием работы-источника в заголовке. Для RAG это даже лучше сплошного текста:
чанки получаются самодостаточными.

**Формат и хранение**: `backend/data/corpus/<agent_id>/*.md`. Gutenberg-тексты
конвертировать в markdown: срезать шапку/подвал (`*** START/END OF THE PROJECT
GUTENBERG EBOOK ***`), проставить заголовки `# THE FOURTH BOOK` → chunker берёт из них
метаданные `source`. Plain text → md — это один разовый прогон скриптом или руками.

Решить до индексации: язык корпуса. Эмбеддинги мультиязычные — русский вопрос найдёт
английский чанк, но цитата в ответе будет на английском. Варианты: (а) только русский
корпус (основная аудитория), (б) оба языка с фильтром по языку юзера — вдвое больше
работы, зато цитаты всегда на языке ответа.

## Шаги реализации

### 1. Инфраструктура
- [ ] `docker-compose.yml`: образ `postgres:16-alpine` → `pgvector/pgvector:pg16`
      (на Railway managed Postgres pgvector обычно уже доступен).
- [ ] Зависимость `pgvector` (пакет `pgvector` для SQLAlchemy) в `backend/pyproject.toml`.

### 2. Схема БД
- [ ] Alembic-миграция: `CREATE EXTENSION IF NOT EXISTS vector` + таблица:

```python
op.create_table(
    "knowledge_chunks",
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("agent_id", sa.String, nullable=False, index=True),  # aurelius | machiavelli | jung
    sa.Column("source", sa.String),      # "Meditations, Book IV"
    sa.Column("content", sa.Text),
    sa.Column("embedding", Vector(768)),
)
```

- [ ] Модель `KnowledgeChunk` в `backend/app/db/models.py`.
- [ ] HNSW-индекс по embedding — опционально, при таком объёме не обязателен.

### 3. Клиент эмбеддингов
- [ ] Метод `embed(text, task_type)` в `backend/app/clients/gemini.py`:
      endpoint `models/gemini-embedding-001:embedContent`, тот же API base.
      `taskType: RETRIEVAL_DOCUMENT` при индексации, `RETRIEVAL_QUERY` при поиске.

```json
POST /v1beta/models/gemini-embedding-001:embedContent
{
  "content": {"parts": [{"text": "..."}]},
  "taskType": "RETRIEVAL_DOCUMENT",
  "outputDimensionality": 768
}
```

- [ ] `outputDimensionality: 768` обязательно (нативная размерность модели — 3072,
      768 — matryoshka-усечение, качества хватает, векторы в 4 раза меньше).
      Усечённые векторы нормализовать (`v / ||v||`) перед записью — для
      cosine_distance не критично, но оставляет свободу перейти на inner product.
- [ ] Для индексации использовать `batchEmbedContents` (до 100 текстов за запрос) —
      весь корпус (~150k токенов, ~2–3 тыс. чанков) эмбеддится за десятки запросов,
      стоимость — центы.
- [ ] Заодно: убрать API-ключ из query string (`_build_url`), передавать заголовком
      `x-goog-api-key` — сейчас ключ светится в URL и может попасть в логи.

### 4. Индексация (`backend/scripts/ingest_books.py`)
- [ ] CLI параметризованный под новых личностей:
      `ingest_books.py --agent seneca --file letters.md --source "Письма к Луцилию"`
      (новая личность = запись в AGENTS + одна команда, без миграций).
- [ ] Чанки ~800–1200 символов, перекрытие ~150, резать по абзацам/главам
      (у «Размышлений» естественные короткие фрагменты — можно по ним).
- [ ] Метаданные: `agent_id`, `source` (книга + глава — из md-заголовков).
- [ ] Запуск разовый; повторный запуск — очистка чанков агента и переиндексация.

### 5. Retrieval в `backend/app/services/agent_chat.py`
- [ ] Перед построением промпта:

```python
async def retrieve_context(agent_id: str, query: str, k: int = 4) -> list[Row]:
    query_emb = await gemini.embed(query, task_type="RETRIEVAL_QUERY")
    rows = await session.execute(
        select(KnowledgeChunk.content, KnowledgeChunk.source)
        .where(KnowledgeChunk.agent_id == agent_id)
        .order_by(KnowledgeChunk.embedding.cosine_distance(query_emb))
        .limit(k)
    )
    return rows.all()
```

- [ ] **Порог похожести** (например, cosine distance < 0.45): на «как дела» релевантных
      фрагментов нет — случайные цитаты в промпте только вредят. Ниже порога — блок
      контекста не добавляем вовсе.

### 6. Промпт
- [ ] Отдельный блок в user-промпте + инструкция в системном:

```
Relevant excerpts from your own writings:
[Meditations, Book IV] "..."
[Meditations, Book VII] "..."

Ground your answer in these excerpts when relevant; you may
paraphrase or quote them, but do not fabricate quotations.
```

### 7. Тесты
- [ ] Юнит на чанкер (границы, перекрытие).
- [ ] Тест retrieve_context с мокнутым embed: фильтр по agent_id, порог, limit.
- [ ] Тест, что при отсутствии релевантных чанков блок контекста не попадает в промпт.

## Потом (опционально)
- Кэш эмбеддинга вопроса (Redis уже есть).
- Гибридный поиск: полнотекстовый Postgres как второй сигнал.
- Источник цитаты в UI мини-аппа («— Размышления, кн. VII»).
