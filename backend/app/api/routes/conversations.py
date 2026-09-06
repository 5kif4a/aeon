from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import ActiveConversationOut
from app.services import conversations

router = APIRouter(tags=["conversations"])


@router.get("/conversations/active", response_model=ActiveConversationOut | None)
async def get_active_conversation(
    user: CurrentUser, session: SessionDep
) -> ActiveConversationOut | None:
    conversation = await conversations.get_active_overview(session, user.id)
    if conversation is None:
        return None
    last_message = await conversations.get_last_agent_message(session, conversation.id)
    return ActiveConversationOut.from_conversation(conversation, last_message, user.language)
