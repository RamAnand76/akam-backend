from typing import Literal
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    language: Literal["en", "ml"] = "en"
    device_id: str = Field(..., min_length=10, max_length=200)
    fcm_token: str = Field(..., min_length=10, max_length=500)
    device_platform: Literal["android", "ios"] = "android"


class AuthTokenData(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_expires_in: int = 2592000


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshTokenData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_expires_in: int = 2592000


class LogoutRequest(BaseModel):
    refresh_token: str


class LogoutData(BaseModel):
    revoked: bool = True


class LogoutAllData(BaseModel):
    sessions_revoked: int


class DeviceUpdateRequest(BaseModel):
    fcm_token: str = Field(..., min_length=10, max_length=500)
    device_platform: Literal["android", "ios"] = "android"


class DeviceUpdateData(BaseModel):
    updated: bool = True
