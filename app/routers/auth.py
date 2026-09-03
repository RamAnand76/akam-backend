from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Header, Request, status
from sqlalchemy import select
from app.dependencies import CurrentUserDep, DbDep
from app.exceptions import UnauthorizedException
from app.models.db.user import User, UserPreferences
from app.models.schemas.auth import (
    AuthTokenData,
    DeviceUpdateData,
    DeviceUpdateRequest,
    LogoutAllData,
    LogoutData,
    LogoutRequest,
    RefreshRequest,
    RefreshTokenData,
    RegisterRequest,
)
from app.models.schemas.common import ApiResponse, Meta
from app.security.jwt import (
    create_access_token,
    create_refresh_token,
    invalidate_all_user_sessions,
    revoke_token,
    verify_token,
)
from app.security.sanitiser import sanitise_text

router = APIRouter(prefix="/auth", tags=["auth"])


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


@router.post(
    "/register",
    response_model=ApiResponse[AuthTokenData],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    db: DbDep,
    request: Request,
) -> ApiResponse[AuthTokenData]:
    clean_name = sanitise_text(body.name, max_length=100)

    # Check if user with device_id exists or create new
    result = await db.execute(select(User).where(User.device_id == body.device_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            name=clean_name,
            language=body.language,
            device_id=body.device_id,
            fcm_token=body.fcm_token,
            device_platform=body.device_platform,
            status="active",
            token_generation=0,
        )
        db.add(user)
        await db.flush()

        # Create default preferences
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
        await db.commit()
        await db.refresh(user)
    else:
        user.name = clean_name
        user.fcm_token = body.fcm_token
        user.device_platform = body.device_platform
        await db.commit()

    access_token = create_access_token(user.id, user.device_id, user.token_generation)
    refresh_token = create_refresh_token(user.id, user.device_id, user.token_generation)

    return ApiResponse(
        status="success",
        data=AuthTokenData(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=3600,
            refresh_expires_in=2592000,
        ),
        meta=_make_meta(request),
    )


@router.post("/refresh", response_model=ApiResponse[RefreshTokenData])
async def refresh(
    body: RefreshRequest,
    db: DbDep,
    request: Request,
) -> ApiResponse[RefreshTokenData]:
    payload = verify_token(body.refresh_token)
    if payload.get("scope") != "refresh":
        raise UnauthorizedException(code="TOKEN_INVALID", message="Provided token is not a refresh token.")

    user_id = payload.get("sub")
    device_id = payload.get("device_id", "")
    old_jti = payload.get("jti")

    # Blacklist old refresh token immediately (rotation)
    if old_jti:
        revoke_token(old_jti)

    result = await db.execute(select(User).where(User.id == user_id, User.status == "active"))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedException(code="TOKEN_REVOKED", message="User account not found or inactive.")

    new_access = create_access_token(user.id, device_id, user.token_generation)
    new_refresh = create_refresh_token(user.id, device_id, user.token_generation)

    return ApiResponse(
        status="success",
        data=RefreshTokenData(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="Bearer",
            expires_in=3600,
            refresh_expires_in=2592000,
        ),
        meta=_make_meta(request),
    )


@router.post("/logout", response_model=ApiResponse[LogoutData])
async def logout(
    body: LogoutRequest,
    current_user: CurrentUserDep,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> ApiResponse[LogoutData]:
    # Revoke access token if present
    acc_token = None
    if authorization and authorization.startswith("Bearer "):
        acc_token = authorization.split(" ", 1)[1]
    elif request.headers.get("authorization", "").startswith("Bearer "):
        acc_token = request.headers.get("authorization", "").split(" ", 1)[1]

    if acc_token:
        try:
            acc_payload = verify_token(acc_token)
            acc_jti = acc_payload.get("jti")
            if acc_jti:
                revoke_token(acc_jti, ttl=3600)
        except Exception:
            pass

    # Revoke refresh token
    try:
        ref_payload = verify_token(body.refresh_token)
        ref_jti = ref_payload.get("jti")
        if ref_jti:
            revoke_token(ref_jti, ttl=2592000)
    except Exception:
        pass

    return ApiResponse(
        status="success",
        data=LogoutData(revoked=True),
        meta=_make_meta(request),
    )


@router.post("/logout_all", response_model=ApiResponse[LogoutAllData])
async def logout_all(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[LogoutAllData]:
    current_user.token_generation += 1
    invalidate_all_user_sessions(current_user.id, current_user.token_generation)
    await db.commit()

    return ApiResponse(
        status="success",
        data=LogoutAllData(sessions_revoked=1),
        meta=_make_meta(request),
    )


@router.put("/device", response_model=ApiResponse[DeviceUpdateData])
async def update_device(
    body: DeviceUpdateRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[DeviceUpdateData]:
    current_user.fcm_token = body.fcm_token
    current_user.device_platform = body.device_platform
    await db.commit()

    return ApiResponse(
        status="success",
        data=DeviceUpdateData(updated=True),
        meta=_make_meta(request),
    )
