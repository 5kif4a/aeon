"""Internationalization: ru/en catalogs for every user-facing backend string.

Code is English-only; user-visible text lives here, keyed by language. The bot
picks the language from the user's profile; the LLM is told to reply in it.
"""

SUPPORTED_LANGUAGES = ("ru", "en")
DEFAULT_LANGUAGE = "en"

# Display name of each language (in its own script), for the UI and pickers.
LANGUAGE_NAMES = {"ru": "Русский", "en": "English"}
# English endonym used inside prompts to instruct the model which language to use.
LANGUAGE_IN_ENGLISH = {"ru": "Russian", "en": "English"}

CHOOSE_LANGUAGE = "Choose language / Выберите язык:"

COUNTRIES = [
    ("kz", {"ru": "Казахстан", "en": "Kazakhstan"}),
    ("ru", {"ru": "Россия", "en": "Russia"}),
    ("us", {"ru": "США", "en": "United States"}),
    ("tr", {"ru": "Турция", "en": "Turkey"}),
    ("ae", {"ru": "ОАЭ", "en": "UAE"}),
    ("de", {"ru": "Германия", "en": "Germany"}),
    ("other", {"ru": "Другая страна", "en": "Other"}),
]

MONTHS = {
    "ru": ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        # Onboarding
        "intro": (
            "1/4 Greetings, traveler.\n"
            "I am AI Marcus Aurelius: memory, goals, Memento Mori, and three advisors.\n\n"
            "What should I call you?"
        ),
        "ask_birthdate": "2/4 Birth date for the Memento Mori calendar.\nChoose a birth period.",
        "bad_birthdate": "I cannot read that date. Send it as YYYY-MM-DD, for example 1995-05-18.",
        "ask_country": "3/4 Where are you from, {name}?\nChoose a country.",
        "done": (
            "4/4 Done. I remembered the core profile.\n\n"
            "Name: {name}\n"
            "Age: {age}\n"
            "Birth date: {birthDate}\n"
            "Country: {country}\n\n"
            "The Mini App will open with your cabinet and calendar filled.\n"
            "Agents are available inside the Mini App or with /agents."
        ),
        "unknown": "I am here. Press /start to register.",
        "birth_back": "← Periods",
        "birth_period": "2/4 Choose your birth period.",
        "birth_year": "2/4 Choose your birth year.",
        "birth_month": "2/4 Choose your birth month.",
        "birth_day": "2/4 Choose your birth day.",
        # Goals
        "goal_set": "Goal accepted. I will remind you every day until you close it.",
        "goal_closed": "Goal closed. Reminders stopped.",
        "reminder": (
            "Memento mori. Your active goal: {goal}\n\n"
            "Open the Mini App if the goal is done and should be closed."
        ),
        # Agent dialogue
        "agent_mode_closed": "Agent mode closed. To pick a new agent, press /agents.",
        "agent_intro_suffix": (
            "Write here like in a normal chat.\n\n"
            "Commands:\n"
            "/agents — switch agent\n"
            "/app — open the Mini App\n"
            "/stop — end the dialogue"
        ),
        "agent_thinking": "{name} is thinking...",
        "agent_continue": "Continuing...",
        "stream_fallback": "Streaming did not respond. Trying the regular mode...",
        "gemini_not_configured": (
            "GEMINI_API_KEY is not configured. Add the key to the environment and restart the bot."
        ),
        # Pickers and menus
        "choose_agent": (
            "Choose an agent for a separate dialogue in the bot.\n\n"
            "After choosing, just write here — the selected agent will reply.\n"
            "Commands: /agents — switch agent, /stop — close agent mode."
        ),
        "dialog_menu_title": "Dialogue controls:",
        "pick_agent_button": "Choose an agent",
        "open_mini_app": "Open Mini App",
        # LLM error messages
        "error_rate_limit": "Gemini limit reached or too many requests. Please try again a bit later.",
        "error_overloaded": "The AI service is temporarily overloaded. Please try again in a couple of minutes.",
        "error_model_unavailable": (
            "Gemini model `{model}` is unavailable. Change GEMINI_MODEL and restart the bot."
        ),
        "error_key_rejected": "The Gemini API key was rejected or has no access to the model. Check GEMINI_API_KEY.",
        "error_network": "The network did not receive a response from Gemini in time. Try again in a minute.",
        "error_empty": "Gemini returned an empty answer. Try rephrasing your question.",
        "error_generic": "The agent could not answer right now. Try again in a minute.",
    },
    "ru": {
        # Onboarding
        "intro": (
            "1/4 Приветствую, путник.\n"
            "Я ИИ Марк Аврелий: память, цели, Memento Mori и три советника.\n\n"
            "Как мне к тебе обращаться?"
        ),
        "ask_birthdate": "2/4 Дата рождения для календаря Memento Mori.\nВыбери период рождения.",
        "bad_birthdate": "Не узнаю дату. Напиши в формате ГГГГ-ММ-ДД, например 1995-05-18.",
        "ask_country": "3/4 Откуда ты, {name}?\nВыбери страну.",
        "done": (
            "4/4 Готово. Я запомнил основу профиля.\n\n"
            "Имя: {name}\n"
            "Возраст: {age}\n"
            "Дата рождения: {birthDate}\n"
            "Страна: {country}\n\n"
            "Mini App уже откроется с заполненным кабинетом и календарём.\n"
            "Агентов можно выбрать внутри Mini App или командой /agents."
        ),
        "unknown": "Я рядом. Нажми /start, чтобы пройти регистрацию.",
        "birth_back": "← Периоды",
        "birth_period": "2/4 Выбери период рождения.",
        "birth_year": "2/4 Выбери год рождения.",
        "birth_month": "2/4 Выбери месяц рождения.",
        "birth_day": "2/4 Выбери число рождения.",
        # Goals
        "goal_set": "Цель принята. Я буду напоминать о ней каждый день, пока ты её не закроешь.",
        "goal_closed": "Цель закрыта. Напоминания остановлены.",
        "reminder": (
            "Memento mori. Твоя активная цель: {goal}\n\n"
            "Открой Mini App, если цель уже выполнена и её нужно закрыть."
        ),
        # Agent dialogue
        "agent_mode_closed": "Режим агента закрыт. Чтобы выбрать нового агента, нажми /agents.",
        "agent_intro_suffix": (
            "Пиши сюда как в обычный чат.\n\n"
            "Команды:\n"
            "/agents — сменить агента\n"
            "/app — открыть Mini App\n"
            "/stop — завершить диалог"
        ),
        "agent_thinking": "{name} размышляет...",
        "agent_continue": "Продолжаю...",
        "stream_fallback": "Потоковая генерация не ответила. Пробую обычный режим...",
        "gemini_not_configured": (
            "GEMINI_API_KEY не настроен. Добавь ключ в переменные окружения и перезапусти бота."
        ),
        # Pickers and menus
        "choose_agent": (
            "Выбери агента для отдельного диалога в боте.\n\n"
            "После выбора просто пиши сообщение сюда — отвечать будет выбранный агент.\n"
            "Команды: /agents — сменить агента, /stop — закрыть режим агента."
        ),
        "dialog_menu_title": "Управление диалогом:",
        "pick_agent_button": "Выбрать агента",
        "open_mini_app": "Открыть Mini App",
        # LLM error messages
        "error_rate_limit": "Лимит Gemini исчерпан или запросов слишком много. Попробуй чуть позже.",
        "error_overloaded": "Сервис AI временно перегружен. Попробуй ещё раз через пару минут.",
        "error_model_unavailable": (
            "Модель Gemini `{model}` недоступна. Нужно поменять GEMINI_MODEL и перезапустить бота."
        ),
        "error_key_rejected": "Gemini API ключ не принят или нет доступа к модели. Проверь GEMINI_API_KEY.",
        "error_network": "Сеть не успела получить ответ от Gemini. Попробуй ещё раз через минуту.",
        "error_empty": "Gemini вернул пустой ответ. Попробуй переформулировать вопрос.",
        "error_generic": "Агент сейчас не смог ответить. Попробуй ещё раз через минуту.",
    },
}


def normalize_language(code: str | None) -> str:
    """Map an arbitrary language code (e.g. 'en-US', 'RU') to a supported one."""
    if not code:
        return DEFAULT_LANGUAGE
    base = code.strip().lower().replace("_", "-").split("-", 1)[0]
    return base if base in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def t(lang: str | None, key: str, **kwargs) -> str:
    language = normalize_language(lang)
    catalog = MESSAGES[language]
    template = catalog.get(key) or MESSAGES[DEFAULT_LANGUAGE].get(key, key)
    return template.format(**kwargs) if kwargs else template


def birth_picker_text(lang: str, stage: str) -> str:
    return t(lang, f"birth_{stage}")


def country_label(code: str, lang: str) -> str:
    language = normalize_language(lang)
    labels = dict(COUNTRIES).get(code) or dict(COUNTRIES)["other"]
    return labels.get(language, labels["en"])


def month_labels(lang: str) -> list[str]:
    return MONTHS[normalize_language(lang)]
