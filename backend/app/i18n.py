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

LIFE_WEEKLY_AGENT_ORDER = ("marcus", "machiavelli", "jung")
LIFE_WEEKLY_AGENT_NAMES = {
    "en": {
        "marcus": "Marcus Aurelius",
        "machiavelli": "Niccolo Machiavelli",
        "jung": "Carl Jung",
    },
    "ru": {
        "marcus": "Марк Аврелий",
        "machiavelli": "Никколо Макиавелли",
        "jung": "Карл Юнг",
    },
}
LIFE_WEEKLY_TEXTS = {
    "en": {
        "marcus": (
            "Not everything was in your control. Your next choice still belongs to you.",
            "The past cannot be changed. Focus on what you can do now.",
            "A meaningful life is built from ordinary days lived with intention.",
            "Accept what has passed calmly, then choose your next step clearly.",
            "Your character is shaped by what you choose again and again.",
        ),
        "machiavelli": (
            "Another week is over, my lord. What will your next move be?",
            "Fortune favors the prepared. Choose your objective before you act.",
            "Intention without action changes nothing. It is time to make the first move.",
            "Do not let chance rule your week. Take the initiative.",
            "My lord, judge the results clearly: what strengthened your position?",
        ),
        "jung": (
            "What was changing within you while the world around you moved on?",
            "What you avoid may point toward the direction of your growth.",
            "Recurring events often carry a recurring lesson. Notice it.",
            "Is this goal truly yours, or was it shaped by someone else's expectations?",
            "Change begins when you see your present situation honestly.",
        ),
    },
    "ru": {
        "marcus": (
            "Не всё было в Вашей власти. Но Ваш следующий выбор принадлежит Вам.",
            "Прошлое уже не изменить. Направьте внимание на то, что можете сделать сейчас.",
            "Большая жизнь складывается из обычных дней, прожитых осознанно.",
            "Спокойно примите прошедшее и ясно определите следующий шаг.",
            "Ваш характер формируется тем, что Вы выбираете снова и снова.",
        ),
        "machiavelli": (
            "Ещё одна неделя завершена, мой господин. Каким будет Ваш следующий ход?",
            "Обстоятельства благоволят подготовленным. Определите свою цель заранее.",
            "Намерение без действия не меняет положения дел. Пора сделать первый шаг.",
            "Не позволяйте случаю распоряжаться Вашей неделей. Возьмите инициативу.",
            "Мой господин, оцените итоги трезво: что укрепило Вашу позицию?",
        ),
        "jung": (
            "Что происходило внутри Вас, пока менялся окружающий мир?",
            "То, чего Вы избегаете, может указывать на направление Вашего роста.",
            "Повторяющиеся события часто несут повторяющийся урок. Заметьте его.",
            "Эта цель действительно Ваша или она продиктована чужими ожиданиями?",
            "Изменение начинается в момент, когда Вы честно видите своё настоящее положение.",
        ),
    },
}
DAILY_NOTIFICATION_TEXTS = {
    "en": {
        "marcus": (
            "Do not try to change the entire day at once. Do well what is directly before you.",
            "Not everything will be in your control today. Your attitude and actions still belong to you.",
            "Ask yourself: what action today reflects the person you want to become?",
            "Do not wait for the right mood. Begin calmly, and inner order will follow action.",
            "You do not need to be perfect today. You only need to be mindful of your choices.",
        ),
        "machiavelli": (
            "My lord, the day has already begun. What first move will strengthen your position?",
            "Intention changes nothing until it becomes action. Take one precise step today.",
            "Do not let urgent matters take what is most important from you. Set your priority in advance.",
            "My lord, opportunity rarely announces its arrival. Be ready to use it.",
            "Judge your strength clearly. Today, doing what is necessary matters more than doing more.",
        ),
        "jung": (
            "Notice what you want to avoid today. Your growth may begin there.",
            "What feeling is following you today? Do not suppress it. First, try to understand it.",
            "Ask yourself: is today's choice truly yours, or was it shaped by someone else's expectations?",
            "What irritates you in others may reveal an unrecognized part of yourself.",
            "Do not rush to fix yourself. Begin by seeing your present state honestly.",
        ),
    },
    "ru": {
        "marcus": (
            "Не пытайтесь изменить весь день сразу. Сделайте достойно то, что находится перед Вами.",
            "Не всё сегодня будет зависеть от Вас. Но Ваше отношение и поступки остаются Вашими.",
            "Спросите себя: какое действие сегодня будет соответствовать человеку, которым Вы хотите стать?",
            "Не ждите подходящего настроения. Начните спокойно, и внутренний порядок последует за действием.",
            "Сегодня Вам не нужно быть идеальным. Достаточно быть внимательным к своему выбору.",
        ),
        "machiavelli": (
            "Мой господин, день уже начался. Какой первый ход укрепит Вашу позицию?",
            "Намерение ничего не меняет, пока не становится действием. Сделайте сегодня один точный шаг.",
            "Не позволяйте срочным делам отнять у Вас главное. Определите приоритет заранее.",
            "Мой господин, удачный момент редко объявляет о своём появлении. Будьте готовы использовать его.",
            "Оцените свои силы трезво. Сегодня важнее не сделать больше, а сделать необходимое.",
        ),
        "jung": (
            "Обратите внимание на то, чего Вам сегодня хочется избежать. Возможно, там начинается рост.",
            "Какое чувство сопровождает Вас сегодня? Не подавляйте его. Сначала постарайтесь его понять.",
            "Спросите себя: сегодняшний выбор действительно Ваш или продиктован чужими ожиданиями?",
            "То, что раздражает Вас в других, иногда указывает на непризнанную часть Вас самих.",
            "Не стремитесь немедленно исправить себя. Для начала честно увидьте своё нынешнее состояние.",
        ),
    },
}

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
            "✦ Welcome to Aeon.\n\n"
            "Become the man you choose to be.\n\n"
            "Think with Marcus Aurelius, Machiavelli, and Carl Jung. "
            "Build discipline, understand yourself, and act with purpose.\n\n"
            "What should we call you? 👤\n\n"
            "● ○ ○ ○"
        ),
        "ask_birthdate": "Your journey through time ⏳\n\nWhen were you born?\n\n● ● ○ ○",
        "bad_birthdate": "I cannot read that date. Send it as YYYY-MM-DD, for example 1995-05-18.",
        "ask_country": (
            "Where are you from, {name}? 🌍\n\n"
            "This helps Aeon personalize your experience.\n\n"
            "● ● ● ○"
        ),
        "done": (
            "Your journey begins, {name}. 🧭\n\n"
            "Bring one real question. Marcus Aurelius, Machiavelli, and Carl Jung "
            "will help you see it from three different perspectives.\n\n"
            "● ● ● ●"
        ),
        "unknown": "I am here. Press /start to register.",
        "birth_back": "← Periods",
        "birth_period": "Your journey through time ⏳\n\nChoose your birth period.\n\n● ● ○ ○",
        "birth_year": "Your journey through time ⏳\n\nChoose your birth year.\n\n● ● ○ ○",
        "birth_month": "Your journey through time ⏳\n\nChoose your birth month.\n\n● ● ○ ○",
        "birth_day": "Your journey through time ⏳\n\nChoose your birth day.\n\n● ● ○ ○",
        # Goals
        "goal_set": "Goal accepted. I will remind you every day until you close it.",
        "goal_closed": "Goal closed. Reminders stopped.",
        "reminder": (
            "Memento mori. Your active goal: {goal}\n\n"
            "Open the Mini App if the goal is done and should be closed."
        ),
        "life_weekly": (
            "{agent}\n\n"
            "Week {weeksLived} of your life has come to an end.\n\n"
            "{text}\n\n"
            "Choose one goal for the coming week."
        ),
        "life_weekly_button": "Open calendar",
        "daily_with_goal": (
            "{agent}\n\nYour active goal: {goal}\n\n{text}\n\nChoose one step for today."
        ),
        "daily_without_goal": "{agent}\n\n{text}\n\nChoose one meaningful action for today.",
        "daily_goal_button": "Open goal",
        "daily_calendar_button": "Set a goal",
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
        "onboarding_open_mini_app": "✦ Ask Your First Question",
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
            "✦ Добро пожаловать в Aeon.\n\n"
            "Станьте мужчиной, которым хотите быть.\n\n"
            "Размышляйте вместе с Марком Аврелием, Макиавелли и Карлом Юнгом. "
            "Укрепляйте дисциплину, познавайте себя и действуйте осознанно.\n\n"
            "Как к Вам обращаться? 👤\n\n"
            "● ○ ○ ○"
        ),
        "ask_birthdate": "Ваш путь во времени ⏳\n\nКогда Вы родились?\n\n● ● ○ ○",
        "bad_birthdate": "Не узнаю дату. Напиши в формате ГГГГ-ММ-ДД, например 1995-05-18.",
        "ask_country": (
            "Откуда Вы, {name}? 🌍\n\n"
            "Это поможет Aeon точнее настроить приложение для Вас.\n\n"
            "● ● ● ○"
        ),
        "done": (
            "Ваш путь начинается, {name}. 🧭\n\n"
            "Задайте вопрос, который действительно Вас волнует. Марк Аврелий, Макиавелли "
            "и Карл Юнг помогут взглянуть на него с трёх разных сторон.\n\n"
            "● ● ● ●"
        ),
        "unknown": "Я рядом. Нажми /start, чтобы пройти регистрацию.",
        "birth_back": "← Периоды",
        "birth_period": "Ваш путь во времени ⏳\n\nВыберите период рождения.\n\n● ● ○ ○",
        "birth_year": "Ваш путь во времени ⏳\n\nВыберите год рождения.\n\n● ● ○ ○",
        "birth_month": "Ваш путь во времени ⏳\n\nВыберите месяц рождения.\n\n● ● ○ ○",
        "birth_day": "Ваш путь во времени ⏳\n\nВыберите день рождения.\n\n● ● ○ ○",
        # Goals
        "goal_set": "Цель принята. Я буду напоминать о ней каждый день, пока ты её не закроешь.",
        "goal_closed": "Цель закрыта. Напоминания остановлены.",
        "reminder": (
            "Memento mori. Твоя активная цель: {goal}\n\n"
            "Открой Mini App, если цель уже выполнена и её нужно закрыть."
        ),
        "life_weekly": (
            "{agent}\n\n"
            "Завершилась {weeksLived}-я неделя Вашей жизни.\n\n"
            "{text}\n\n"
            "Выберите одну цель на новую неделю."
        ),
        "life_weekly_button": "Открыть календарь",
        "daily_with_goal": (
            "{agent}\n\nВаша активная цель: {goal}\n\n{text}\n\nВыберите один шаг на сегодня."
        ),
        "daily_without_goal": "{agent}\n\n{text}\n\nВыберите одно значимое действие на сегодня.",
        "daily_goal_button": "Открыть цель",
        "daily_calendar_button": "Поставить цель",
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
        "onboarding_open_mini_app": "✦ Задать первый вопрос",
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


def life_weekly_content(lang: str | None, weeks_lived: int) -> tuple[str, str]:
    """Rotate agents weekly and each agent's message every third week."""
    language = normalize_language(lang)
    agent_index = weeks_lived % len(LIFE_WEEKLY_AGENT_ORDER)
    agent = LIFE_WEEKLY_AGENT_ORDER[agent_index]
    texts = LIFE_WEEKLY_TEXTS[language][agent]
    text_index = (weeks_lived // len(LIFE_WEEKLY_AGENT_ORDER)) % len(texts)
    return LIFE_WEEKLY_AGENT_NAMES[language][agent], texts[text_index]


def daily_notification_content(lang: str | None, sequence: int) -> tuple[str, str]:
    """Rotate agents daily and each agent's message every third day."""
    language = normalize_language(lang)
    agent_index = sequence % len(LIFE_WEEKLY_AGENT_ORDER)
    agent = LIFE_WEEKLY_AGENT_ORDER[agent_index]
    texts = DAILY_NOTIFICATION_TEXTS[language][agent]
    text_index = (sequence // len(LIFE_WEEKLY_AGENT_ORDER)) % len(texts)
    return LIFE_WEEKLY_AGENT_NAMES[language][agent], texts[text_index]


def birth_picker_text(lang: str, stage: str) -> str:
    return t(lang, f"birth_{stage}")


def country_label(code: str, lang: str) -> str:
    language = normalize_language(lang)
    labels = dict(COUNTRIES).get(code) or dict(COUNTRIES)["other"]
    return labels.get(language, labels["en"])


def month_labels(lang: str) -> list[str]:
    return MONTHS[normalize_language(lang)]
