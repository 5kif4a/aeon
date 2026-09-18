"""DB-free: callback handlers ignore updates that do not come from a private chat."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.constants import ChatType

from app.bot import messaging
from app.bot.handlers import commands, onboarding


def _callback_update(chat_type: str, data: str) -> MagicMock:
    update = MagicMock()
    update.effective_chat.type = chat_type
    update.effective_chat.id = -100_500
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.data = data
    return update


def test_is_private_chat_reads_the_chat_type():
    assert messaging.is_private_chat(_callback_update(ChatType.PRIVATE, "menu:home")) is True
    assert messaging.is_private_chat(_callback_update(ChatType.GROUP, "menu:home")) is False
    assert messaging.is_private_chat(_callback_update(ChatType.SUPERGROUP, "x")) is False
    no_chat = MagicMock()
    no_chat.effective_chat = None
    assert messaging.is_private_chat(no_chat) is False


@pytest.mark.parametrize(
    ("handler", "data", "touched"),
    [
        (commands.navigation_callback, "billing:trial", (commands, "_user_for_update")),
        (commands.agent_callback, "agent:marcus", (commands.chat, "set_active_agent")),
        (
            onboarding.onboarding_agent_callback,
            "onboarding:agent:marcus",
            (onboarding, "SessionFactory"),
        ),
    ],
)
async def test_group_callbacks_are_answered_and_dropped(monkeypatch, handler, data, touched):
    module, attribute = touched
    sentinel = MagicMock(side_effect=AssertionError("a group callback reached the database"))
    monkeypatch.setattr(module, attribute, sentinel)
    update = _callback_update(ChatType.SUPERGROUP, data)
    context = MagicMock()
    context.user_data = {}

    await handler(update, context)

    update.callback_query.answer.assert_awaited_once()
    sentinel.assert_not_called()
