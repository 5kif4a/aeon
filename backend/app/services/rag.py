"""Small local BM25 retrieval layer for agent book corpora."""

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings

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


_index_cache: dict[Path, tuple[int, RagIndex]] = {}


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


def plan_has_rag_access(plan: str, allow_basic: bool = False) -> bool:
    return allow_basic or plan.strip().lower() not in {"", "basic", "free"}


def retrieve(
    agent_id: str,
    query: str,
    top_k: int | None = None,
    language: str = "ru",
) -> list[RagHit]:
    settings = get_settings()
    if not settings.rag_enabled or agent_id not in {"aurelius", "jung", "machiavelli"}:
        return []
    locale_suffix = ".en" if language.strip().lower().startswith("en") else ""
    path = Path(settings.rag_data_dir) / f"{agent_id}{locale_suffix}.json"
    index = _load_index(path)
    return index.search(query, top_k or settings.rag_top_k) if index else []


def build_context(agent_id: str, query: str, plan: str, language: str = "ru") -> str:
    settings = get_settings()
    if not plan_has_rag_access(plan, settings.rag_allow_basic):
        return ""
    hits = retrieve(agent_id, query, language=language)
    if not hits:
        return ""
    sections = []
    for hit in hits:
        location = f"page {hit.chunk.page}"
        if hit.chunk.chapter:
            location += f", {hit.chunk.chapter}"
        sections.append(f"[{hit.chunk.source}; {location}]\n{hit.chunk.text}")
    return "\n\n".join(sections)
