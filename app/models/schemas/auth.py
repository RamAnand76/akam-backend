from typing import Literal
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    language: Literal["en", "ml"] = "en"
    device_id: str = Field(..., min_length=10, max_length=200)
    fcm_token: str = Field(..., min_length=10, max_length=500)
    device_platform: Literal["android", "ios"] = "android"


EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RequestOtpRequest(BaseModel):
    email: str = Field(..., max_length=320, pattern=EMAIL_PATTERN)
    device_id: str = Field(..., min_length=10, max_length=200)


class RequestOtpData(BaseModel):
    sent: bool = True
    expires_in: int


class VerifyOtpRequest(BaseModel):
    email: str = Field(..., max_length=320, pattern=EMAIL_PATTERN)
    code: str = Field(..., pattern=r"^\d{6}$")
    device_id: str = Field(..., min_length=10, max_length=200)
    language: Literal["en", "ml"] = "en"
    fcm_token: str | None = Field(default=None, min_length=10, max_length=500)
    device_platform: Literal["android", "ios"] = "android"


class AuthTokenData(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str
    device_secret: str | None = None  # shown once at verify; required by /auth/refresh
    is_new_user: bool = False
    token_type: str = "Bearer"
    expires_in: int
    refresh_expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str
    device_secret: str = Field(..., min_length=16, max_length=200)


class RefreshTokenData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_expires_in: int


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
