# RAG: знания из трудов личностей

Цель: ответы агентов (Аврелий, Макиавелли, Юнг) опираются на реальные фрагменты их книг,
а не только на знания LLM. Релевантные фрагменты подмешиваются в промпт при каждом ответе
пользователей с планом Trial/Pro (гейт — `AccessGrant.generation_plan`, см. `AGENTS.md`).

## Реализованная архитектура

```
[PDF книг] → scripts/build_*_rag.py → data/rag/<agent>[.en].json (чанки ~1000 символов)
                                              │
                          scripts/embed_rag.py (Gemini gemini-embedding-001, 768d)
                                              ↓
                                   Postgres: таблица rag_chunks
                                              ↓ (lazy load, кэш 5 мин в процессе)
вопрос → embedding вопроса ─→ cosine top-20 ─┐
                                              ├→ reciprocal rank fusion → top-k → блок в промпте
вопрос → BM25 по тем же чанкам ─→ top-20 ────┘
```

Код: `backend/app/services/rag.py` (поиск), `backend/app/clients/gemini.py`
(`embed_texts`, `embed_query`), `backend/scripts/embed_rag.py` (индексация),
модель `RagChunkRecord` в `backend/app/db/models.py`, миграция `20260908_rag_chunks`.

### Хранение: Postgres без pgvector

Таблица `rag_chunks`: `id, agent_id, language (ru|en), chunk_id, source, chapter, page, text,
embedding, created_at`, уникальный ключ `(agent_id, language, chunk_id)`. `embedding` —
`BYTEA`: L2-нормализованный вектор, упакованный как little-endian float32
(`RAG_EMBEDDING_DIM * 4` байт). Читается одним `np.frombuffer`.

Почему не pgvector:

- Корпуса маленькие — единицы тысяч чанков на (агент, язык). Полный скан матрицы
  `(n, 768)` в numpy занимает доли миллисекунды; индекс HNSW/IVF не нужен.
- Не требуется расширение в managed Postgres на Railway и отдельный образ в docker-compose;
  миграция — обычная таблица, `downgrade` тривиален.
- Один экземпляр бэкенда (см. правила про уведомления в `AGENTS.md`), поэтому кэш в памяти
  процесса с TTL 5 минут достаточен: после `embed_rag.py` новые векторы подхватываются без
  редеплоя. `rag.invalidate_cache()` сбрасывает кэш явно.
- Файлы `data/rag/*.json` не попадают в образ (gitignore, Dockerfile их не копирует), а
  Railway без volume. Таблица в БД решает проблему «в проде RAG молча не работает».

### Эмбеддинги

`gemini-embedding-001` через тот же REST API, что и генерация
(`models/gemini-embedding-001:embedContent` для вопроса, `:batchEmbedContents` до 100 текстов
за запрос для чанков). `outputDimensionality: 768` (matryoshka-усечение; нативные 3072 не
нужны — векторы в 4 раза меньше при сопоставимом качестве). `taskType`:
`RETRIEVAL_DOCUMENT` для чанков (текст = источник + глава + чанк), `RETRIEVAL_QUERY` для
вопроса. Усечённые векторы нормализуются перед записью и при загрузке, поэтому cosine =
скалярное произведение. Модель и размерность — `RAG_EMBEDDING_MODEL` / `RAG_EMBEDDING_DIM`;
смена любого из них требует `embed_rag.py --force`, строки другой размерности игнорируются
с предупреждением в логе.

### Гибридный поиск

1. Эмбеддинг вопроса (таймаут 5 с) → cosine top-20 по матрице корпуса.
2. BM25 (свой, с русским/английским стеммингом и расширением запросов концептами) → top-20.
   Индекс строится из JSON-файла, если он есть в `RAG_DATA_DIR`, иначе из тех же чанков БД.
3. Reciprocal rank fusion (`k = 60`) → `RAG_TOP_K` фрагментов. `RagHit.score` в этом случае —
   RRF-балл, а не cosine/BM25.

Деградация: не удалось получить эмбеддинг вопроса → только BM25; в `rag_chunks` нет строк →
BM25 по JSON-файлу; нет ни того ни другого → пустой контекст и одно предупреждение в лог на
корпус (раньше это было молча).

Многоязычность: русскому пользователю отдаётся русский корпус, английскому — `.en`, чтобы
цитата была на языке ответа; эмбеддинги мультиязычные, но кросс-языковой поиск намеренно не
используется.

### Индексация

```bash
cd backend
uv run python -m scripts.embed_rag --dry-run
DATABASE_URL="postgresql+asyncpg://…" uv run python -m scripts.embed_rag   # против прода
uv run python -m scripts.embed_rag --agent jung --language en
uv run python -m scripts.embed_rag --force
```

Скрипт идемпотентен: чанки с неизменившимся текстом и уже записанным вектором нужной длины
пропускаются, удалённые из JSON чанки удаляются из таблицы, 429/5xx повторяются с
экспоненциальной паузой, в конце печатается сводка по корпусам.

### Оценка

`scripts/evaluate_rag.py evals/<agent>_<lang>_golden.json` — BM25 по локальному файлу
(без сети и БД); `--hybrid` — прод-путь через `rag.retrieve` (нужны `DATABASE_URL` и
`GEMINI_API_KEY`). `scripts/query_rag.py` показывает найденные фрагменты,
`scripts/audit_rag_answers.py` прогоняет полные ответы агентов.

Тесты `tests/test_rag.py` работают без Postgres: загрузчик строк и `gemini.embed_query`
подменяются через `monkeypatch`.

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
синхронистичность...) своими словами, с указанием работы-источника. Для RAG это даже
лучше сплошного текста: чанки получаются самодостаточными.

Фактически проиндексированные издания перечислены в `README.md` (раздел «Agent book RAG»):
«Государь» и «Рассуждения о Ливии» (EN), «Размышления» (RU 1985, EN Casaubon),
«Человек и его символы» (RU 2016, EN).

## Потом (опционально)

- Порог релевантности: на «как дела» случайные цитаты только вредят; сейчас контекст
  добавляется всегда, когда есть хиты.
- Кэш эмбеддинга повторяющихся вопросов.
- Источник цитаты в UI мини-аппа («— Размышления, кн. VII»).
- Передавать API-ключ Gemini заголовком `x-goog-api-key` вместо query string.
