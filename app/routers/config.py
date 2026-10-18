from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.config import settings
from app.exceptions import NotFoundException
from app.models.schemas.common import ApiResponse, Meta

router = APIRouter(prefix="/config", tags=["config"])


class ModelManifest(BaseModel):
    version: str
    url: str
    sha256: str
    size_bytes: int


class AppConfig(BaseModel):
    min_app_version: str
    feature_flags: dict


def _meta(request: Request) -> Meta:
    return Meta(request_id=getattr(request.state, "request_id", "unknown"), timestamp=datetime.utcnow(), version="2.0.0")


@router.get("/models", response_model=ApiResponse[ModelManifest])
async def get_model_manifest(request: Request) -> ApiResponse[ModelManifest]:
    """On-device model manifest. Public (no auth) so the app can fetch it before sign-in."""
    if not (settings.MODEL_VERSION and settings.MODEL_URL and settings.MODEL_SHA256):
        raise NotFoundException(code="MODEL_MANIFEST_NOT_CONFIGURED", message="No on-device model is published yet.")
    return ApiResponse(
        data=ModelManifest(
            version=settings.MODEL_VERSION,
            url=settings.MODEL_URL,
            sha256=settings.MODEL_SHA256.lower(),
            size_bytes=settings.MODEL_SIZE_BYTES,
        ),
        meta=_meta(request),
    )


@router.get("/app", response_model=ApiResponse[AppConfig])
async def get_app_config(request: Request) -> ApiResponse[AppConfig]:
    return ApiResponse(
        data=AppConfig(min_app_version=settings.MIN_APP_VERSION, feature_flags=settings.feature_flags),
        meta=_meta(request),
    )
