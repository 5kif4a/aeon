import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import User
from app.i18n import SUPPORTED_LANGUAGES
from app.services.users import calculate_age

LanguageCode = Literal[SUPPORTED_LANGUAGES]  # type: ignore[valid-type]


class ProfileOut(BaseModel):
    id: int
    language: str
    name: str
    gender: str
    birthDate: date | None
    age: int | None
    country: str
    location: str
    activity: str
    interests: str
    mainGoal: str
    currentProblem: str
    plan: str
    tokens: int
    activeAgent: str | None

    @classmethod
    def from_user(cls, user: User) -> "ProfileOut":
        return cls(
            id=user.id,
            language=user.language,
            name=user.name,
            gender=user.gender,
            birthDate=user.birth_date,
            age=calculate_age(user.birth_date) if user.birth_date else None,
            country=user.country,
            location=user.location,
            activity=user.activity,
            interests=user.interests,
            mainGoal=user.main_goal,
            currentProblem=user.current_problem,
            plan=user.plan,
            tokens=user.tokens,
            activeAgent=user.active_agent,
        )


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    gender: str | None = Field(default=None, max_length=32)
    birthDate: date | None = None
    country: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=128)
    activity: str | None = Field(default=None, max_length=256)
    interests: str | None = Field(default=None, max_length=2000)
    mainGoal: str | None = Field(default=None, max_length=2000)
    currentProblem: str | None = Field(default=None, max_length=2000)
    language: LanguageCode | None = None
    plan: str | None = Field(default=None, max_length=32)

    def to_user_fields(self) -> dict:
        mapping = {
            "name": "name",
            "gender": "gender",
            "birthDate": "birth_date",
            "country": "country",
            "location": "location",
            "activity": "activity",
            "interests": "interests",
            "mainGoal": "main_goal",
            "currentProblem": "current_problem",
            "language": "language",
            "plan": "plan",
        }
        data = self.model_dump(exclude_unset=True)
        return {mapping[key]: value for key, value in data.items() if key in mapping}


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    status: str
    created_at: datetime
    closed_at: datetime | None


class GoalCreate(BaseModel):
    text: str = Field(min_length=1, max_length=512)


class DiaryEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    created_at: datetime


class DiaryEntryCreate(BaseModel):
    text: str = Field(min_length=1, max_length=700)


class StartDialogRequest(BaseModel):
    message: str = Field(default="", max_length=2000)


class StartDialogResponse(BaseModel):
    ok: bool
    agentName: str
    botUsername: str


class AgentOut(BaseModel):
    id: str
    name: str
    role: str
