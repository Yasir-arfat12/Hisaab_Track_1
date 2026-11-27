from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GoogleStartData(BaseModel):
    redirect_url: str


class GoogleCallbackData(BaseModel):
    user_id: UUID
    email: str
    display_name: str
    created_at: datetime


class DemoAuthData(BaseModel):
    user_id: UUID
    email: str
    display_name: str
    is_demo: bool
    seed_scenario: str


class LogoutData(BaseModel):
    logged_out: bool


class UserProfileData(BaseModel):
    user_id: UUID
    email: str
    display_name: str
    is_demo: bool
    gmail_connected: bool
    created_at: datetime


class DeleteAccountData(BaseModel):
    deleted: bool
