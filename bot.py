import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


API_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://example.com")
API_URL = f"https://api.telegram.org/bot{API_TOKEN}" if API_TOKEN else ""
DATA_DIR = Path("data")
REGISTRATIONS_FILE = DATA_DIR / "registrations.json"
REMINDER_HOUR = int(os.environ.get("REMINDER_HOUR", "9"))

LANGUAGES = {"ru": "Русский", "en": "English"}
AGE_RANGES = ["0-10", "11-16", "17-20", "21-30", "31+"]
COUNTRIES = [
    ("kz", "Kazakhstan"),
    ("ru", "Russia"),
    ("us", "United States"),
    ("tr", "Turkey"),
    ("ae", "UAE"),
    ("de", "Germany"),
    ("other", "Other"),
]

MESSAGES = {
    "ru": {
        "intro": (
            "Приветствую тебя, путник. Я ИИ Марк Аврелий.\n\n"
            "Я помогу тебе помнить о времени, выбирать цель и держать внимание на важном.\n"
            "Сначала представься. Напиши свое имя, ищущий знание."
        ),
        "ask_age": "Рад встрече, {name}. Выбери свой возрастной период.",
        "ask_birthdate": "Теперь напиши дату рождения в формате ГГГГ-ММ-ДД. Например: 1995-05-18.",
        "bad_birthdate": "Не узнаю дату. Напиши в формате ГГГГ-ММ-ДД, например 1995-05-18.",
        "ask_country": "Откуда ты, {name}? Выбери страну.",
        "done": (
            "Регистрация завершена.\n\n"
            "Имя: {name}\n"
            "Возраст: {age}\n"
            "Дата рождения: {birthDate}\n"
            "Страна: {country}\n\n"
            "Открой Mini App: дата рождения уже будет в календаре."
        ),
        "unknown": "Я рядом. Нажми /start, чтобы пройти регистрацию.",
        "goal_set": "Цель принята. Я буду напоминать о ней каждый день, пока ты ее не закроешь.",
        "goal_closed": "Цель закрыта. Напоминания остановлены.",
        "reminder": "Memento mori. Твоя активная цель: {goal}\n\nОткрой Mini App, если цель уже выполнена и ее нужно закрыть.",
    },
    "en": {
        "intro": (
            "Greetings, traveler. I am AI Marcus Aurelius.\n\n"
            "I will help you remember time, choose a goal, and keep attention on what matters.\n"
            "First, introduce yourself. Write your name."
        ),
        "ask_age": "Good to meet you, {name}. Choose your age range.",
        "ask_birthdate": "Now send your birth date as YYYY-MM-DD. Example: 1995-05-18.",
        "bad_birthdate": "I cannot read that date. Send it as YYYY-MM-DD, for example 1995-05-18.",
        "ask_country": "Where are you from, {name}? Choose a country.",
        "done": (
            "Registration is complete.\n\n"
            "Name: {name}\n"
            "Age: {age}\n"
            "Birth date: {birthDate}\n"
            "Country: {country}\n\n"
            "Open the Mini App: your birth date will already be in the calendar."
        ),
        "unknown": "I am here. Press /start to register.",
        "goal_set": "Goal accepted. I will remind you every day until you close it.",
        "goal_closed": "Goal closed. Reminders stopped.",
        "reminder": "Memento mori. Your active goal: {goal}\n\nOpen the Mini App if the goal is done and should be closed.",
    },
}

sessions = {}


def main():
    if not API_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN before running bot.py")

    DATA_DIR.mkdir(exist_ok=True)
    ensure_registrations_file()
    offset = None
    print("Marcus Aurelius bot is running. Press Ctrl+C to stop.")

    while True:
        try:
            remind_due_goals()
            updates = api_call("getUpdates", {"timeout": 30, "offset": offset})
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                handle_update(update)
        except urllib.error.URLError as error:
            print(f"Network error: {error}")
            time.sleep(3)
        except Exception as error:
            print(f"Bot error: {error}")
            time.sleep(1)


def handle_update(update):
    if "callback_query" in update:
        handle_callback(update["callback_query"])
        return

    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]

    if "web_app_data" in message:
        handle_web_app_data(chat_id, message["web_app_data"].get("data", "{}"))
        return

    text = (message.get("text") or "").strip()
    if text == "/start":
        sessions[chat_id] = {"step": "language"}
        send_language_picker(chat_id)
        return

    session = sessions.get(chat_id)
    if session and session.get("step") == "name":
        session["name"] = text[:48] if text else "Traveler"
        session["step"] = "age"
        send_age_picker(chat_id, session)
        return

    if session and session.get("step") == "birthdate":
        if not is_valid_birthdate(text):
            send_message(chat_id, t(session["lang"], "bad_birthdate"))
            return
        session["birthDate"] = text
        session["step"] = "country"
        send_country_picker(chat_id, session)
        return

    lang = session.get("lang", "ru") if session else "ru"
    send_message(chat_id, t(lang, "unknown"))


def handle_callback(callback):
    chat_id = callback["message"]["chat"]["id"]
    data = callback.get("data", "")
    session = sessions.setdefault(chat_id, {})
    answer_callback(callback["id"])

    if data.startswith("lang:"):
        lang = data.split(":", 1)[1]
        session.clear()
        session.update({"step": "name", "lang": lang})
        send_message(chat_id, t(lang, "intro"))
        return

    if data.startswith("age:"):
        session["age"] = data.split(":", 1)[1]
        session["step"] = "birthdate"
        send_message(chat_id, t(session["lang"], "ask_birthdate"))
        return

    if data.startswith("country:"):
        country_code = data.split(":", 1)[1]
        session["country"] = dict(COUNTRIES).get(country_code, "Other")
        session["step"] = "done"
        save_registration(chat_id, session)
        send_completion(chat_id, session)


def handle_web_app_data(chat_id, raw_data):
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError:
        return

    registrations = read_registrations()
    profile = registrations.setdefault(str(chat_id), {})
    lang = profile.get("language", "ru")

    if payload.get("type") == "goal_set":
        profile["goal"] = {
            "id": payload.get("goalId"),
            "text": payload.get("goalText", ""),
            "createdAt": payload.get("createdAt"),
            "status": "active",
            "lastReminderDate": "",
        }
        write_registrations(registrations)
        send_message(chat_id, t(lang, "goal_set"))

    if payload.get("type") == "goal_close":
        if profile.get("goal"):
            profile["goal"]["status"] = "closed"
            profile["goal"]["closedAt"] = payload.get("closedAt")
        write_registrations(registrations)
        send_message(chat_id, t(lang, "goal_closed"))


def remind_due_goals():
    now = datetime.now()
    if now.hour < REMINDER_HOUR:
        return

    today = now.date().isoformat()
    registrations = read_registrations()
    changed = False

    for chat_id, profile in registrations.items():
        goal = profile.get("goal") or {}
        if goal.get("status") != "active":
            continue
        if goal.get("lastReminderDate") == today:
            continue

        send_message(chat_id, t(profile.get("language", "ru"), "reminder", goal=goal.get("text", "")))
        goal["lastReminderDate"] = today
        changed = True

    if changed:
        write_registrations(registrations)


def send_language_picker(chat_id):
    keyboard = [[{"text": label, "callback_data": f"lang:{code}"}] for code, label in LANGUAGES.items()]
    send_message(chat_id, "Выбери язык / Choose language:", keyboard)


def send_age_picker(chat_id, session):
    keyboard = [[{"text": age, "callback_data": f"age:{age}"}] for age in AGE_RANGES]
    send_message(chat_id, t(session["lang"], "ask_age", name=session["name"]), keyboard)


def send_country_picker(chat_id, session):
    keyboard = [[{"text": country, "callback_data": f"country:{code}"}] for code, country in COUNTRIES]
    send_message(chat_id, t(session["lang"], "ask_country", name=session["name"]), keyboard)


def send_completion(chat_id, session):
    lang = session["lang"]
    text = t(
        lang,
        "done",
        name=session["name"],
        age=session["age"],
        birthDate=session["birthDate"],
        country=session["country"],
    )
    keyboard = [[{"text": "Open Mini App", "web_app": {"url": build_webapp_url(session)}}]]
    send_message(chat_id, text, keyboard)


def build_webapp_url(session):
    params = urllib.parse.urlencode(
        {
            "lang": session["lang"],
            "name": session["name"],
            "age": session["age"],
            "birthDate": session["birthDate"],
            "country": session["country"],
        }
    )
    separator = "&" if "?" in WEBAPP_URL else "?"
    return f"{WEBAPP_URL}{separator}{params}"


def save_registration(chat_id, session):
    registrations = read_registrations()
    existing = registrations.get(str(chat_id), {})
    registrations[str(chat_id)] = {
        **existing,
        "language": session["lang"],
        "name": session["name"],
        "age": session["age"],
        "birthDate": session["birthDate"],
        "country": session["country"],
        "registeredAt": int(time.time()),
    }
    write_registrations(registrations)


def send_message(chat_id, text, inline_keyboard=None):
    payload = {"chat_id": chat_id, "text": text}
    if inline_keyboard:
        payload["reply_markup"] = {"inline_keyboard": inline_keyboard}
    api_call("sendMessage", payload)


def answer_callback(callback_id):
    api_call("answerCallbackQuery", {"callback_query_id": callback_id})


def api_call(method, payload):
    request = urllib.request.Request(
        f"{API_URL}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def t(lang, key, **kwargs):
    return MESSAGES.get(lang, MESSAGES["ru"])[key].format(**kwargs)


def is_valid_birthdate(value):
    try:
        date = datetime.strptime(value, "%Y-%m-%d")
        return date <= datetime.now()
    except ValueError:
        return False


def ensure_registrations_file():
    if not REGISTRATIONS_FILE.exists():
        REGISTRATIONS_FILE.write_text("{}", encoding="utf-8")


def read_registrations():
    ensure_registrations_file()
    return json.loads(REGISTRATIONS_FILE.read_text(encoding="utf-8"))


def write_registrations(registrations):
    REGISTRATIONS_FILE.write_text(
        json.dumps(registrations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
