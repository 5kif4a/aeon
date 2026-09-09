from fastapi import APIRouter

from app.api.routes import (
    admin,
    admin_access,
    admin_audience,
    agents,
    billing,
    conversations,
    diary,
    goal,
    me,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(me.router)
api_router.include_router(goal.router)
api_router.include_router(diary.router)
api_router.include_router(agents.router)
api_router.include_router(conversations.router)
api_router.include_router(billing.router)
api_router.include_router(admin.router)
# Same `/admin` prefix, split by concern: access control and audience/broadcast tooling.
api_router.include_router(admin_access.router)
api_router.include_router(admin_audience.router)
