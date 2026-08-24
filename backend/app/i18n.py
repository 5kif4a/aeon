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
LIFE_WEEKLY_AGENT_IDS = {
    "marcus": "aurelius",
    "machiavelli": "machiavelli",
    "jung": "jung",
}
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
            "A week is not judged by comfort, but by the character you practiced within it.",
            "Keep the lesson from what is unfinished, then release the weight of it.",
            "Before choosing the next goal, ask whether it serves your principles or merely your pride.",
        ),
        "machiavelli": (
            "Another week is over, my lord. What will your next move be?",
            "Fortune favors the prepared. Choose your objective before you act.",
            "Intention without action changes nothing. It is time to make the first move.",
            "Do not let chance rule your week. Take the initiative.",
            "My lord, judge the results clearly: what strengthened your position?",
            "Activity is not always progress. Measure what actually changed your position.",
            "A wise plan leaves room for fortune without surrendering direction to it.",
            "The coming week belongs less to the hopeful than to the prepared.",
        ),
        "jung": (
            "What was changing within you while the world around you moved on?",
            "What you avoid may point toward the direction of your growth.",
            "Recurring events often carry a recurring lesson. Notice it.",
            "Is this goal truly yours, or was it shaped by someone else's expectations?",
            "Change begins when you see your present situation honestly.",
            "The part of the week you resist remembering may contain its most useful truth.",
            "Growth asks not only what you achieved, but what you learned about yourself.",
            "A goal gains power when conscious intention meets an honest inner need.",
        ),
    },
    "ru": {
        "marcus": (
            "Не всё было в Вашей власти. Но Ваш следующий выбор принадлежит Вам.",
            "Прошлое уже не изменить. Направьте внимание на то, что можете сделать сейчас.",
            "Большая жизнь складывается из обычных дней, прожитых осознанно.",
            "Спокойно примите прошедшее и ясно определите следующий шаг.",
            "Ваш характер формируется тем, что Вы выбираете снова и снова.",
            "Неделю определяет не лёгкость, а характер, который Вы проявляли в ней.",
            "Сохраните урок незавершённого, но освободитесь от его тяжести.",
            "Прежде чем выбрать новую цель, спросите: служит ли она Вашим принципам или лишь гордости?",
        ),
        "machiavelli": (
            "Ещё одна неделя завершена, мой господин. Каким будет Ваш следующий ход?",
            "Обстоятельства благоволят подготовленным. Определите свою цель заранее.",
            "Намерение без действия не меняет положения дел. Пора сделать первый шаг.",
            "Не позволяйте случаю распоряжаться Вашей неделей. Возьмите инициативу.",
            "Мой господин, оцените итоги трезво: что укрепило Вашу позицию?",
            "Деятельность не всегда означает прогресс. Оцените, что действительно укрепило Вашу позицию.",
            "Мудрый план оставляет место удаче, но не отдаёт ей направление.",
            "Новая неделя принадлежит не столько надеющимся, сколько подготовленным.",
        ),
        "jung": (
            "Что происходило внутри Вас, пока менялся окружающий мир?",
            "То, чего Вы избегаете, может указывать на направление Вашего роста.",
            "Повторяющиеся события часто несут повторяющийся урок. Заметьте его.",
            "Эта цель действительно Ваша или она продиктована чужими ожиданиями?",
            "Изменение начинается в момент, когда Вы честно видите своё настоящее положение.",
            "Та часть недели, которую не хочется вспоминать, может содержать самый ценный смысл.",
            "Рост определяется не только достижениями, но и тем, что Вы узнали о себе.",
            "Цель обретает силу, когда осознанное намерение встречается с честной внутренней потребностью.",
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
            "Let the quality of this hour be enough. A worthy day is built one action at a time.",
            "Discipline begins when you act from principle instead of waiting for motivation.",
            "Meet the task before you without complaint; this is where character becomes visible.",
        ),
        "machiavelli": (
            "My lord, the day has already begun. What first move will strengthen your position?",
            "Intention changes nothing until it becomes action. Take one precise step today.",
            "Do not let urgent matters take what is most important from you. Set your priority in advance.",
            "My lord, opportunity rarely announces its arrival. Be ready to use it.",
            "Judge your strength clearly. Today, doing what is necessary matters more than doing more.",
            "Begin with the move that creates options instead of merely consuming effort.",
            "Protect your attention. Whoever controls your priorities controls the direction of your day.",
            "A small advantage used today is worth more than a perfect plan delayed.",
        ),
        "jung": (
            "Notice what you want to avoid today. Your growth may begin there.",
            "What feeling is following you today? Do not suppress it. First, try to understand it.",
            "Ask yourself: is today's choice truly yours, or was it shaped by someone else's expectations?",
            "What irritates you in others may reveal an unrecognized part of yourself.",
            "Do not rush to fix yourself. Begin by seeing your present state honestly.",
            "Before acting, notice which part of you wants this choice and which part resists it.",
            "The task you postpone may be carrying a message about fear, meaning, or identity.",
            "Give today's strongest emotion a name; what is seen clearly no longer rules from the shadows.",
        ),
    },
    "ru": {
        "marcus": (
            "Не пытайтесь изменить весь день сразу. Сделайте достойно то, что находится перед Вами.",
            "Не всё сегодня будет зависеть от Вас. Но Ваше отношение и поступки остаются Вашими.",
            "Спросите себя: какое действие сегодня будет соответствовать человеку, которым Вы хотите стать?",
            "Не ждите подходящего настроения. Начните спокойно, и внутренний порядок последует за действием.",
            "Сегодня Вам не нужно быть идеальным. Достаточно быть внимательным к своему выбору.",
            "Пусть качества этого часа будет достаточно. Достойный день складывается из отдельных поступков.",
            "Дисциплина начинается, когда Вы действуете из принципа, а не ждёте мотивации.",
            "Примите стоящую перед Вами задачу без жалоб: именно здесь проявляется характер.",
        ),
        "machiavelli": (
            "Мой господин, день уже начался. Какой первый ход укрепит Вашу позицию?",
            "Намерение ничего не меняет, пока не становится действием. Сделайте сегодня один точный шаг.",
            "Не позволяйте срочным делам отнять у Вас главное. Определите приоритет заранее.",
            "Мой господин, удачный момент редко объявляет о своём появлении. Будьте готовы использовать его.",
            "Оцените свои силы трезво. Сегодня важнее не сделать больше, а сделать необходимое.",
            "Начните с хода, который создаёт новые возможности, а не просто расходует силы.",
            "Защищайте своё внимание. Кто управляет Вашими приоритетами, тот определяет направление дня.",
            "Небольшое преимущество, использованное сегодня, ценнее идеального плана, отложенного на потом.",
        ),
        "jung": (
            "Обратите внимание на то, чего Вам сегодня хочется избежать. Возможно, там начинается рост.",
            "Какое чувство сопровождает Вас сегодня? Не подавляйте его. Сначала постарайтесь его понять.",
            "Спросите себя: сегодняшний выбор действительно Ваш или продиктован чужими ожиданиями?",
            "То, что раздражает Вас в других, иногда указывает на непризнанную часть Вас самих.",
            "Не стремитесь немедленно исправить себя. Для начала честно увидьте своё нынешнее состояние.",
            "Перед действием заметьте, какая часть Вас стремится к этому выбору, а какая ему сопротивляется.",
            "Откладываемая задача может говорить о страхе, смысле или Вашем представлении о себе.",
            "Назовите сильнейшее чувство этого дня: увиденное ясно больше не управляет из тени.",
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
        "home_welcome": (
            "✦ Welcome to Aeon, {name}.\n\n"
            "Bring one real decision. Marcus Aurelius will examine what is in your control, "
            "Machiavelli will test the strategy, and Carl Jung will look beneath the surface.\n\n"
            "Choose one mind, or ask all three."
        ),
        "home_returning": "Welcome back, {name}.\n\nWhat do you want to examine today?",
        "traveler_name": "Traveler",
        "intro": (
            "✦ Welcome to Aeon.\n\n"
            "Become the man you choose to be.\n\n"
            "Think with Marcus Aurelius, Machiavelli, and Carl Jung. "
            "Build discipline, understand yourself, and act with purpose.\n\n"
            "What should we call you? 👤\n\n"
            "● ○ ○ ○"
        ),
        "ask_birthdate": (
            "Your life calendar\n\nWhen were you born? This unlocks your Memento Mori calendar "
            "and schedules your weekly reflection."
        ),
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
        "profile_saved": (
            "Life calendar unlocked. You are {age}.\n\n"
            "Choose your local time in Settings so reflections arrive when they are useful."
        ),
        "unknown": "I am here. Press /start to register.",
        "birth_back": "← Periods",
        "birth_back_years": "← Years",
        "birth_back_months": "← Months",
        "birth_period": "Your journey through time ⏳\n\nChoose your birth period.\n\n● ● ○ ○",
        "birth_year": "Your journey through time ⏳\n\nChoose your birth year.\n\n● ● ○ ○",
        "birth_month": "Your journey through time ⏳\n\nChoose your birth month.\n\n● ● ○ ○",
        "birth_day": "Your journey through time ⏳\n\nChoose your birth day.\n\n● ● ○ ○",
        # Goals
        "goal_set": "Goal accepted. I will keep it visible until you close it.",
        "goal_closed": "Goal closed. Reminders stopped.",
        "reminder": "Your active goal: {goal}\n\nWhat is the smallest useful step you can complete today?",
        "life_weekly": (
            "“{text}”\n\n"
            "— {agent}\n\n"
            "Week {weeksLived} of your life has come to an end.\n\n"
            "Choose one goal for the coming week."
        ),
        "life_weekly_button": "Open calendar",
        "daily_with_goal": (
            "“{text}”\n\n— {agent}\n\nYour active goal: {goal}\n\nChoose one step for today."
        ),
        "daily_without_goal": "“{text}”\n\n— {agent}\n\nChoose one meaningful action for today.",
        "daily_goal_button": "Open goal",
        "daily_calendar_button": "Set a goal",
        "daily_done_button": "✓ Done for today",
        "daily_checkin_saved": "Action recorded. Your current streak is {streak} day(s).",
        "notification_settings_button": "Notification settings",
        "ask_quote_author_button": "Ask the author",
        # Billing
        "payment_pro_title": "Aeon Pro",
        "payment_pro_description": "30 days of answers grounded in original works and the Council of Three.",
        "payment_pro_price": "Aeon Pro · 30 days",
        "payment_invalid": "This payment link is invalid or no longer available.",
        "payment_success": "Aeon Pro is active. Your agents now answer with their books and the Council of Three is available.",
        "payment_no_subscription": "You do not have an active renewable Pro subscription.",
        "payment_canceled": "Automatic renewal is canceled. Pro remains active until {date}.",
        "payment_support": "For payment help, describe the issue and include the approximate payment date. We will check the Telegram Stars transaction and help with cancellation or a legitimate refund.",
        "question_limit_free": "You have used today's 3 free questions. Your limit resets tomorrow. Start the 7-day Trial to continue with answers grounded in the original books.",
        "question_limit_trial": "Today's Trial questions are used. Your book-grounded allowance resets tomorrow, or you can continue with Pro.",
        "question_limit_pro": "Today's Pro questions are used. Your allowance resets tomorrow.",
        "council_usage": "Send one important question after the command:\n/council Should I change careers?",
        "council_thinking": "Marcus Aurelius, Machiavelli, and Carl Jung are considering your question...",
        "council_prompt": (
            "Council of Three\n\nSend one important decision or situation. "
            "You will receive three distinct perspectives and one concrete next step."
        ),
        "council_limit_free": "The Council of Three is available in the free Trial and Pro.",
        "council_limit_trial": "Your one Trial Council has already been used. Upgrade to Pro for three councils per day.",
        "council_limit_pro": "Today's three Pro councils have been used. The limit resets tomorrow.",
        # Agent dialogue
        "agent_mode_closed": "Dialogue closed. Choose what you want to do next.",
        "agent_intro_suffix": "Send one real question. You can switch perspectives after the answer.",
        "agent_thinking": "{name} is thinking...",
        "agent_continue": "Continuing...",
        "stream_fallback": "Streaming did not respond. Trying the regular mode...",
        "gemini_not_configured": "The advisors are temporarily unavailable. Please try again later.",
        # Pickers and menus
        "choose_agent": "Whose perspective do you need?",
        "choose_agent_for_question": "Who should examine this question? Your message is saved.",
        "dialog_menu_title": "What do you want to do?",
        "pick_agent_button": "Choose an advisor",
        "open_mini_app": "Open Aeon",
        "onboarding_open_mini_app": "✦ Ask Your First Question",
        "open_aeon": "Open Aeon",
        "council_button": "Council of Three",
        "complete_profile_button": "Unlock life calendar",
        "settings_button": "Settings",
        "back_home": "← Main menu",
        "back_settings": "← Settings",
        "switch_agent_button": "Switch advisor",
        "start_trial_button": "Start 7-day Trial",
        "upgrade_pro_button": "Continue with Pro",
        "chat_menu_button": "Open Aeon",
        # Settings
        "settings_title": (
            "Settings\n\nReflections arrive at {hour:02d}:00 in {timezone}. "
            "You can pause daily and weekly messages independently."
        ),
        "daily_setting": "Daily",
        "weekly_setting": "Weekly",
        "notifications_on": "On",
        "notifications_off": "Off",
        "reminder_time_button": "Time {hour:02d}:00",
        "timezone_button": "Zone: {timezone}",
        "choose_reminder_time": "When should Aeon send your reflections?",
        "choose_timezone": "Choose the city closest to your time zone.",
        # LLM error messages
        "error_rate_limit": "The advisors are receiving too many questions right now. Please try again shortly.",
        "error_overloaded": "The advisors are temporarily unavailable. Please try again in a couple of minutes.",
        "error_model_unavailable": "The advisors are temporarily unavailable. Please try again later.",
        "error_key_rejected": "The advisors are temporarily unavailable. Please try again later.",
        "error_network": "The answer took too long to arrive. Please try again in a minute.",
        "error_empty": "No answer arrived. Try rephrasing your question.",
        "error_generic": "The agent could not answer right now. Try again in a minute.",
    },
    "ru": {
        # Onboarding
        "home_welcome": (
            "✦ Добро пожаловать в Aeon, {name}.\n\n"
            "Принесите одно настоящее решение. Марк Аврелий отделит подвластное Вам, "
            "Макиавелли проверит стратегию, а Карл Юнг поможет заглянуть под поверхность.\n\n"
            "Выберите одного советника или спросите всех троих."
        ),
        "home_returning": "С возвращением, {name}.\n\nЧто Вы хотите обдумать сегодня?",
        "traveler_name": "Путник",
        "intro": (
            "✦ Добро пожаловать в Aeon.\n\n"
            "Станьте мужчиной, которым хотите быть.\n\n"
            "Размышляйте вместе с Марком Аврелием, Макиавелли и Карлом Юнгом. "
            "Укрепляйте дисциплину, познавайте себя и действуйте осознанно.\n\n"
            "Как к Вам обращаться? 👤\n\n"
            "● ○ ○ ○"
        ),
        "ask_birthdate": (
            "Календарь жизни\n\nКогда Вы родились? Это откроет календарь Memento Mori "
            "и еженедельные размышления."
        ),
        "bad_birthdate": "Не удалось распознать дату. Напишите её в формате ГГГГ-ММ-ДД, например 1995-05-18.",
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
        "profile_saved": (
            "Календарь жизни открыт. Ваш возраст: {age}.\n\n"
            "Выберите местное время в настройках, чтобы сообщения приходили вовремя."
        ),
        "unknown": "Я рядом. Откройте главное меню командой /start.",
        "birth_back": "← Периоды",
        "birth_back_years": "← Годы",
        "birth_back_months": "← Месяцы",
        "birth_period": "Ваш путь во времени ⏳\n\nВыберите период рождения.\n\n● ● ○ ○",
        "birth_year": "Ваш путь во времени ⏳\n\nВыберите год рождения.\n\n● ● ○ ○",
        "birth_month": "Ваш путь во времени ⏳\n\nВыберите месяц рождения.\n\n● ● ○ ○",
        "birth_day": "Ваш путь во времени ⏳\n\nВыберите день рождения.\n\n● ● ○ ○",
        # Goals
        "goal_set": "Цель принята. Я буду держать её в поле внимания, пока Вы её не закроете.",
        "goal_closed": "Цель закрыта. Напоминания остановлены.",
        "reminder": "Ваша активная цель: {goal}\n\nКакой самый небольшой полезный шаг Вы можете завершить сегодня?",
        "life_weekly": (
            "«{text}»\n\n"
            "— {agent}\n\n"
            "Завершилась {weeksLived}-я неделя Вашей жизни.\n\n"
            "Выберите одну цель на новую неделю."
        ),
        "life_weekly_button": "Открыть календарь",
        "daily_with_goal": (
            "«{text}»\n\n— {agent}\n\nВаша активная цель: {goal}\n\nВыберите один шаг на сегодня."
        ),
        "daily_without_goal": "«{text}»\n\n— {agent}\n\nВыберите одно значимое действие на сегодня.",
        "daily_goal_button": "Открыть цель",
        "daily_calendar_button": "Поставить цель",
        "daily_done_button": "✓ Выполнено сегодня",
        "daily_checkin_saved": "Действие отмечено. Ваша текущая серия: {streak} дн.",
        "notification_settings_button": "Настроить уведомления",
        "ask_quote_author_button": "Спросить автора",
        # Billing
        "payment_pro_title": "Aeon Pro",
        "payment_pro_description": "30 дней ответов с опорой на оригинальные труды и доступ к Совету трёх.",
        "payment_pro_price": "Aeon Pro · 30 дней",
        "payment_invalid": "Эта ссылка оплаты недействительна или больше недоступна.",
        "payment_success": "Aeon Pro активирован. Агенты теперь отвечают с опорой на книги, а Совет трёх доступен.",
        "payment_no_subscription": "У Вас нет активной Pro-подписки с автопродлением.",
        "payment_canceled": "Автопродление отключено. Pro продолжит работать до {date}.",
        "payment_support": "Для помощи с оплатой опишите проблему и укажите примерную дату платежа. Мы проверим транзакцию Telegram Stars и поможем с отменой или обоснованным возвратом.",
        "question_limit_free": "Сегодняшние 3 бесплатных вопроса использованы. Лимит обновится завтра. Запустите 7-дневный пробный период, чтобы продолжить с ответами на основе оригинальных книг.",
        "question_limit_trial": "Вопросы пробного периода на сегодня использованы. Лимит ответов по книгам обновится завтра, либо Вы можете продолжить с Pro.",
        "question_limit_pro": "Вопросы Pro на сегодня использованы. Лимит обновится завтра.",
        "council_usage": "Добавьте один важный вопрос после команды:\n/council Стоит ли мне сменить профессию?",
        "council_thinking": "Марк Аврелий, Макиавелли и Карл Юнг рассматривают Ваш вопрос...",
        "council_prompt": (
            "Совет трёх\n\nОтправьте одно важное решение или ситуацию. "
            "Вы получите три разных взгляда и один конкретный следующий шаг."
        ),
        "council_limit_free": "Совет трёх доступен в бесплатном Trial и Pro.",
        "council_limit_trial": "Единственный пробный Совет трёх уже использован. В Pro доступно три совета в день.",
        "council_limit_pro": "Сегодняшние три Совета Pro использованы. Лимит обновится завтра.",
        # Agent dialogue
        "agent_mode_closed": "Диалог завершён. Выберите, что хотите сделать дальше.",
        "agent_intro_suffix": "Отправьте один настоящий вопрос. После ответа можно сменить точку зрения.",
        "agent_thinking": "{name} размышляет...",
        "agent_continue": "Продолжаю...",
        "stream_fallback": "Потоковая генерация не ответила. Пробую обычный режим...",
        "gemini_not_configured": "Советники временно недоступны. Пожалуйста, попробуйте позже.",
        # Pickers and menus
        "choose_agent": "Чья точка зрения Вам нужна?",
        "choose_agent_for_question": "Кто должен рассмотреть этот вопрос? Ваше сообщение сохранено.",
        "dialog_menu_title": "Что Вы хотите сделать?",
        "pick_agent_button": "Выбрать советника",
        "open_mini_app": "Открыть Aeon",
        "onboarding_open_mini_app": "✦ Задать первый вопрос",
        "open_aeon": "Открыть Aeon",
        "council_button": "Совет трёх",
        "complete_profile_button": "Открыть календарь жизни",
        "settings_button": "Настройки",
        "back_home": "← Главное меню",
        "back_settings": "← Настройки",
        "switch_agent_button": "Сменить советника",
        "start_trial_button": "Начать 7-дневный период",
        "upgrade_pro_button": "Продолжить с Pro",
        "chat_menu_button": "Открыть Aeon",
        # Settings
        "settings_title": (
            "Настройки\n\nСообщения приходят в {hour:02d}:00, часовой пояс: {timezone}. "
            "Ежедневные и еженедельные сообщения можно отключать отдельно."
        ),
        "daily_setting": "Ежедневные",
        "weekly_setting": "Еженедельные",
        "notifications_on": "Вкл.",
        "notifications_off": "Выкл.",
        "reminder_time_button": "Время {hour:02d}:00",
        "timezone_button": "Пояс: {timezone}",
        "choose_reminder_time": "В какое время Aeon должен присылать размышления?",
        "choose_timezone": "Выберите город с ближайшим к Вам часовым поясом.",
        # LLM error messages
        "error_rate_limit": "Советники сейчас получают слишком много вопросов. Пожалуйста, попробуйте немного позже.",
        "error_overloaded": "Советники временно недоступны. Пожалуйста, попробуйте через пару минут.",
        "error_model_unavailable": "Советники временно недоступны. Пожалуйста, попробуйте позже.",
        "error_key_rejected": "Советники временно недоступны. Пожалуйста, попробуйте позже.",
        "error_network": "Ответ не успел прийти. Пожалуйста, попробуйте ещё раз через минуту.",
        "error_empty": "Ответ не пришёл. Попробуйте переформулировать вопрос.",
        "error_generic": "Советник сейчас не смог ответить. Пожалуйста, попробуйте ещё раз через минуту.",
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


def notification_agent_id(sequence: int) -> str:
    """Return the canonical agent id for a rotating notification sequence."""
    agent = LIFE_WEEKLY_AGENT_ORDER[sequence % len(LIFE_WEEKLY_AGENT_ORDER)]
    return LIFE_WEEKLY_AGENT_IDS[agent]


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
