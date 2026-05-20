# aeon

Telegram Mini App с тремя основными разделами:

- Главная: выбор AI-наставника из трех агентов.
- Дневник: Memento Mori 90 лет в неделях, цель на текущий отрезок жизни и личные записи.
- Кабинет: личный штаб пользователя, память советника, профиль мышления и подписка.

Агенты:

- Марк Аврелий: личный мудрец и психолог.
- Макиавелли: коуч и тактический бизнес-тренер.
- Карл Юнг: психоаналитик тени.

## Локальный запуск Mini App

```powershell
cd C:\Users\diaaa\Documents\Codex\2026-05-18\new-chat
C:\Users\diaaa\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m http.server 5173 --bind 127.0.0.1
```

Открой:

```text
http://127.0.0.1:5173/
```

## Запуск бота

```powershell
$env:TELEGRAM_BOT_TOKEN="YOUR_TOKEN"
$env:WEBAPP_URL="https://your-public-mini-app-url"
$env:REMINDER_HOUR="9"
C:\Users\diaaa\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe bot.py
```

Бот регистрирует пользователя, собирает дату рождения и передает ее в Mini App через URL-параметр `birthDate`.

Цели из дневника отправляются боту через `Telegram.WebApp.sendData()`. Бот напоминает о цели каждый день, пока Mini App не отправит закрытие цели.
