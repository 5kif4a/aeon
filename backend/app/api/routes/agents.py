import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.agents import AGENTS, agent_name, agent_role
from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import AgentOut, StartDialogRequest, StartDialogResponse
from app.bot import chat, runtime
from app.services import users

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=list[AgentOut])
async def list_agents(user: CurrentUser) -> list[AgentOut]:
    return [
        AgentOut(
            id=agent_id,
            name=agent_name(agent_id, user.language),
            role=agent_role(agent_id, user.language),
        )
        for agent_id in AGENTS
    ]


@router.post("/agents/{agent_id}/dialog", response_model=StartDialogResponse)
async def start_agent_dialog(
    agent_id: str, payload: StartDialogRequest, user: CurrentUser, session: SessionDep
) -> StartDialogResponse:
    if agent_id not in AGENTS:
        raise HTTPException(status_code=400, detail="Unknown agent")

    application = runtime.get_application()
    if application is None:
        raise HTTPException(status_code=503, detail="Telegram bot is not running")

    await users.update_user(session, user, {"active_agent": agent_id})

    initial_message = payload.message.strip()
    bot = application.bot
    if initial_message:
        task = asyncio.create_task(chat.process_agent_message(bot, user.id, initial_message))
        task.add_done_callback(_log_dialog_task_error)
    else:
        await bot.send_message(user.id, chat.build_agent_intro(agent_id, user.language))

    return StartDialogResponse(
        ok=True,
        agentName=agent_name(agent_id, user.language),
        botUsername=bot.username or "",
    )


def _log_dialog_task_error(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception():
        logger.warning("Mini App initiated dialog failed: %s", task.exception())
