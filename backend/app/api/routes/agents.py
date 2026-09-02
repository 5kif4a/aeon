import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.agents import AGENTS, agent_name, agent_role
from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import AgentOut, StartCouncilRequest, StartDialogRequest, StartDialogResponse
from app.bot import chat, runtime
from app.services import conversations, users

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


@router.post("/agents/council/dialog", response_model=StartDialogResponse)
async def start_council_dialog(
    payload: StartCouncilRequest, user: CurrentUser
) -> StartDialogResponse:
    application = runtime.get_application()
    if application is None:
        raise HTTPException(status_code=503, detail="Telegram bot is not running")
    task = asyncio.create_task(
        chat.process_council_message(application.bot, user.id, payload.message.strip())
    )
    task.add_done_callback(_log_dialog_task_error)
    return StartDialogResponse(
        ok=True,
        agentName="Council of Three" if user.language == "en" else "Совет трёх",
        botUsername=application.bot.username or "",
    )


@router.post("/agents/{agent_id}/dialog", response_model=StartDialogResponse)
async def start_agent_dialog(
    agent_id: str, payload: StartDialogRequest, user: CurrentUser, session: SessionDep
) -> StartDialogResponse:
    if agent_id not in AGENTS:
        raise HTTPException(status_code=400, detail="Unknown agent")

    application = runtime.get_application()
    if application is None:
        raise HTTPException(status_code=503, detail="Telegram bot is not running")

    await conversations.start_session(session, user.id, agent_id)
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
