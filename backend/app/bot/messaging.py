"""Telegram messaging helpers: chunking long texts, edit-or-send."""

from telegram import Bot, InlineKeyboardMarkup, Message
from telegram.error import BadRequest

TELEGRAM_MESSAGE_LIMIT = 3900


def split_message(text: str) -> list[str]:
    text = str(text or "")
    if len(text) <= TELEGRAM_MESSAGE_LIMIT:
        return [text]

    chunks = []
    rest = text
    while len(rest) > TELEGRAM_MESSAGE_LIMIT:
        split_at = rest.rfind("\n\n", 0, TELEGRAM_MESSAGE_LIMIT)
        if split_at < TELEGRAM_MESSAGE_LIMIT // 2:
            split_at = rest.rfind("\n", 0, TELEGRAM_MESSAGE_LIMIT)
        if split_at < TELEGRAM_MESSAGE_LIMIT // 2:
            split_at = rest.rfind(" ", 0, TELEGRAM_MESSAGE_LIMIT)
        if split_at < TELEGRAM_MESSAGE_LIMIT // 2:
            split_at = TELEGRAM_MESSAGE_LIMIT
        chunks.append(rest[:split_at].strip())
        rest = rest[split_at:].strip()
    if rest:
        chunks.append(rest)
    return chunks


async def send_chunked(
    bot: Bot, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> Message | None:
    chunks = split_message(text)
    last_message = None
    for index, chunk in enumerate(chunks):
        markup = reply_markup if index == len(chunks) - 1 else None
        last_message = await bot.send_message(chat_id, chunk, reply_markup=markup)
    return last_message


async def try_edit(
    bot: Bot,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    try:
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup
        )
        return True
    except BadRequest as error:
        if "message is not modified" in str(error).lower():
            return True
        return False
    except Exception:
        return False


async def send_or_edit(bot: Bot, chat_id: int, message_id: int | None, text: str) -> None:
    chunks = split_message(text)
    if message_id and chunks:
        if not await try_edit(bot, chat_id, message_id, chunks[0]):
            await bot.send_message(chat_id, chunks[0])
        for chunk in chunks[1:]:
            await bot.send_message(chat_id, chunk)
        return
    await send_chunked(bot, chat_id, text)
