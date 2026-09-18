"""Morning and evening notification texts, ru/en, with a deterministic rotation.

The morning slot is declarative (a thought to read, no reply expected) and alternates the
advisors' own lines from `DAILY_NOTIFICATION_TEXTS` with unattributed aphorisms. The evening
slot is a question the user can answer in one word; that answer goes to the advisor who
asked. The rotation is indexed by days since signup, so a user never sees the same text twice
inside one cycle (the previous product picked at random and repeated itself).
"""

from app.i18n import (
    DAILY_NOTIFICATION_TEXTS,
    LIFE_WEEKLY_AGENT_NAMES,
    LIFE_WEEKLY_AGENT_ORDER,
    normalize_language,
)

# Unattributed morning lines. Kept unsigned on purpose: none of them is a sourced quotation,
# and a product whose argument is "answers from the books" must not invent attributions.
MORNING_PLAIN: dict[str, tuple[str, ...]] = {
    "en": (
        "A new day. Will it differ from yesterday?",
        "A new day has come. Make it count.",
        "A new day has come. Do not waste it.",
        "A new day. Remember: only you decide your fate.",
        "Falling down is an accident, staying down is a choice.",
        "Fight for the life you promised yourself.",
        "Don't give up on a future you haven't seen yet.",
        "Don't quit.",
        "Either you change, or everything repeats.",
        "A tree doesn't compete with the trees around it. It just grows.",
        "You can only win when your mind is stronger than your emotions.",
        "You get what you fight for, not what you wish for.",
        "You are the greatest project you will ever work on.",
        "Ambition without action becomes anxiety. Action without ambition becomes slavery.",
    ),
    "ru": (
        "Новый день. Будет ли он отличаться от вчерашнего?",
        "Новый день настал. Сделайте его значимым.",
        "Новый день настал. Не потратьте его впустую.",
        "Новый день. Помните: только Вы вправе решать свою судьбу.",
        "Упасть — случайность. Остаться лежать — выбор.",
        "Боритесь за жизнь, которую Вы себе обещали.",
        "Не отказывайтесь от будущего, которого Вы ещё не видели.",
        "Не сдавайтесь.",
        "Либо Вы меняетесь, либо всё повторяется.",
        "Дерево не соревнуется с деревьями вокруг. Оно просто растёт.",
        "Вы побеждаете только тогда, когда Ваш разум сильнее Ваших эмоций.",
        "Вы получаете то, за что боретесь, а не то, чего желаете.",
        "Вы — главный проект, над которым Вам предстоит работать.",
        "Амбиции без действия становятся тревогой. Действие без амбиций — рабством.",
    ),
}

# Evening questions: the proven return channel. Each one is answerable in a word.
EVENING_QUESTIONS: dict[str, tuple[str, ...]] = {
    "en": (
        "Did you spend this day, or use it?",
        "Did you live this day with dignity?",
        "Today — did you live, or merely exist?",
        "The day is gone and you are older. Are you better?",
        "How many people did you help today? And did you help yourself?",
        "What did you do today that mattered?",
        "Will this day stay in your memory?",
    ),
    "ru": (
        "Вы этот день потратили или использовали?",
        "Достойно ли Вы провели сегодняшний день?",
        "Вы сегодня жили или существовали?",
        "День прошёл, Вы стали старше. А стали ли лучше?",
        "Скольким людям Вы сегодня помогли? А главное — помогли ли себе?",
        "Что значимого Вы сделали за сегодняшний день?",
        "Останется ли этот день в Ваших воспоминаниях?",
    ),
}

# Product feedback, asked instead of the reflection every FEEDBACK_EVERY evenings.
FEEDBACK_QUESTIONS: dict[str, tuple[str, ...]] = {
    "en": (
        "What would you change in Aeon?",
        "What is missing from Aeon for you?",
    ),
    "ru": (
        "Что Вы хотели бы изменить в Aeon?",
        "Чего Вам не хватает в Aeon?",
    ),
}
FEEDBACK_EVERY = 21


def _attributed_lines(language: str) -> list[tuple[str, str]]:
    """The advisors' morning lines as (text, advisor name), advisors rotating day by day."""
    texts = DAILY_NOTIFICATION_TEXTS[language]
    names = LIFE_WEEKLY_AGENT_NAMES[language]
    depth = max(len(lines) for lines in texts.values())
    return [
        (texts[agent][index], names[agent])
        for index in range(depth)
        for agent in LIFE_WEEKLY_AGENT_ORDER
        if index < len(texts[agent])
    ]


def morning_catalog(language: str) -> list[tuple[str, str]]:
    """Signed and unsigned lines spread evenly through one cycle; author is "" when unsigned."""
    normalized = normalize_language(language)
    signed = _attributed_lines(normalized)
    plain = [(text, "") for text in MORNING_PLAIN[normalized]]
    # Sort both lists by their relative position so neither kind clusters at one end.
    keyed = [(index / len(signed), item) for index, item in enumerate(signed)]
    keyed += [((index + 0.5) / len(plain), item) for index, item in enumerate(plain)]
    return [item for _key, item in sorted(keyed, key=lambda pair: pair[0])]


def morning_content(language: str, sequence: int) -> tuple[str, str]:
    catalog = morning_catalog(language)
    return catalog[sequence % len(catalog)]


def evening_question(language: str, sequence: int) -> str:
    normalized = normalize_language(language)
    if sequence % FEEDBACK_EVERY == FEEDBACK_EVERY - 1:
        feedback = FEEDBACK_QUESTIONS[normalized]
        return feedback[(sequence // FEEDBACK_EVERY) % len(feedback)]
    questions = EVENING_QUESTIONS[normalized]
    return questions[sequence % len(questions)]
