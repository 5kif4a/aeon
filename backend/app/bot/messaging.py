"""Telegram messaging helpers: chunking long texts, edit-or-send.

`markdown=True` marks text written by the model: each chunk is converted to
Telegram HTML (`app.bot.formatting`) and sent with `parse_mode="HTML"`. If
Telegram still refuses to parse it, the same chunk goes out as plain text - a
formatting bug must never cost the user their answer.
"""

import logging

from telegram import Bot, InlineKeyboardMarkup, Message
from telegram.error import BadRequest

from app.bot import formatting

logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 3900

_PARSE_ERRORS = ("can't parse entities", "unsupported start tag", "unclosed start tag")


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


def _is_parse_error(error: BadRequest) -> bool:
    message = str(error).lower()
    return any(marker in message for marker in _PARSE_ERRORS)


async def _send(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    markdown: bool = False,
) -> Message:
    if not markdown:
        return await bot.send_message(chat_id, text, reply_markup=reply_markup)
    try:
        return await bot.send_message(
            chat_id, formatting.to_telegram_html(text), reply_markup=reply_markup, parse_mode="HTML"
        )
    except BadRequest as error:
        if not _is_parse_error(error):
            raise
        logger.warning("Telegram rejected the formatted message, sending it plain: %s", error)
        return await bot.send_message(chat_id, text, reply_markup=reply_markup)


async def send_chunked(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    markdown: bool = False,
) -> Message | None:
    chunks = split_message(text)
    last_message = None
    for index, chunk in enumerate(chunks):
        markup = reply_markup if index == len(chunks) - 1 else None
        last_message = await _send(bot, chat_id, chunk, markup, markdown)
    return last_message


async def try_edit(
    bot: Bot,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    markdown: bool = False,
) -> bool:
    try:
        await bot.edit_message_text(
            formatting.to_telegram_html(text) if markdown else text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
            parse_mode="HTML" if markdown else None,
        )
        return True
    except BadRequest as error:
        if "message is not modified" in str(error).lower():
            return True
        if markdown and _is_parse_error(error):
            logger.warning("Telegram rejected the formatted edit, editing it plain: %s", error)
            return await try_edit(bot, chat_id, message_id, text, reply_markup)
        return False
    except Exception:
        return False


async def send_or_edit(
    bot: Bot,
    chat_id: int,
    message_id: int | None,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    markdown: bool = False,
) -> None:
    chunks = split_message(text)
    if message_id and chunks:
        first_markup = reply_markup if len(chunks) == 1 else None
        if not await try_edit(bot, chat_id, message_id, chunks[0], first_markup, markdown):
            await _send(bot, chat_id, chunks[0], first_markup, markdown)
        for index, chunk in enumerate(chunks[1:], start=1):
            markup = reply_markup if index == len(chunks) - 1 else None
            await _send(bot, chat_id, chunk, markup, markdown)
        return
    await send_chunked(bot, chat_id, text, reply_markup, markdown)
