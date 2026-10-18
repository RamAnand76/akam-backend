import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import CurrentUserDep, DbDep
from app.exceptions import AkamException, NotFoundException, RateLimitedException, UnauthorizedException
from app.models.db.auth import AuthSession, OtpCode, RefreshToken
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
    RequestOtpData,
    RequestOtpRequest,
    VerifyOtpRequest,
)
from app.models.schemas.common import ApiResponse, Meta
from app.security.identity import client_ip, keyed_hash
from app.security.jwt import create_access_token, create_refresh_token, verify_token
from app.security.sanitiser import sanitise_text
from app.services.email_service import EmailSender, get_email_sender

router = APIRouter(prefix="/auth", tags=["auth"])
logger = structlog.get_logger()


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    # SQLite returns naive datetimes; Postgres returns aware ones.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _new_refresh_row(db: AsyncSession, session: AuthSession) -> str:
    jti = str(uuid.uuid4())
    db.add(RefreshToken(
        jti=jti,
        session_id=session.id,
        user_id=session.user_id,
        expires_at=_now() + timedelta(seconds=settings.REFRESH_TOKEN_TTL_SECONDS),
    ))
    return create_refresh_token(session.user_id, session.device_id, session.id, jti)


async def _revoke_sessions(db: AsyncSession, where: list) -> int:
    """Revoke matching sessions and their live refresh tokens; returns the number of refresh tokens revoked."""
    now = _now()
    sids = select(AuthSession.id).where(*where, AuthSession.revoked_at.is_(None))
    count = (await db.execute(
        select(func.count()).select_from(RefreshToken).where(
            RefreshToken.session_id.in_(sids),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.rotated_at.is_(None),
            RefreshToken.expires_at > now,
        )
    )).scalar_one()
    await db.execute(update(RefreshToken).where(RefreshToken.session_id.in_(sids), RefreshToken.revoked_at.is_(None)).values(revoked_at=now))
    await db.execute(update(AuthSession).where(*where, AuthSession.revoked_at.is_(None)).values(revoked_at=now))
    return count


async def _issue_session(db: AsyncSession, user: User, device_id: str, is_new: bool) -> AuthTokenData:
    # One live session per user+device: a fresh login replaces the old one.
    await _revoke_sessions(db, [AuthSession.user_id == user.id, AuthSession.device_id == device_id])
    secret = secrets.token_urlsafe(32)
    session = AuthSession(user_id=user.id, device_id=device_id, device_secret_hash=keyed_hash(secret))
    db.add(session)
    await db.flush()
    refresh = await _new_refresh_row(db, session)
    return AuthTokenData(
        user_id=user.id,
        access_token=create_access_token(user.id, device_id, session.id),
        refresh_token=refresh,
        device_secret=secret,
        is_new_user=is_new,
        expires_in=settings.ACCESS_TOKEN_TTL_SECONDS,
        refresh_expires_in=settings.REFRESH_TOKEN_TTL_SECONDS,
    )


@router.post("/request-otp", response_model=ApiResponse[RequestOtpData])
async def request_otp(
    body: RequestOtpRequest,
    db: DbDep,
    request: Request,
    sender: EmailSender = Depends(get_email_sender),
) -> ApiResponse[RequestOtpData]:
    email = body.email.strip().lower()
    ip_hash = keyed_hash(f"ip:{client_ip(request)}")
    now = _now()
    since = now - timedelta(seconds=settings.OTP_REQUEST_WINDOW_SECONDS)

    # Durable limits: counted from stored rows, so they survive cold starts and span instances.
    for column, value, limit in (
        (OtpCode.email, email, settings.OTP_REQUESTS_PER_EMAIL),
        (OtpCode.ip_hash, ip_hash, settings.OTP_REQUESTS_PER_IP),
    ):
        n = (await db.execute(select(func.count()).select_from(OtpCode).where(column == value, OtpCode.created_at > since))).scalar_one()
        if n >= limit:
            raise RateLimitedException("Too many codes requested. Please try again later.")

    # Only the newest code is valid.
    await db.execute(update(OtpCode).where(OtpCode.email == email, OtpCode.consumed_at.is_(None)).values(consumed_at=now))
    code = f"{secrets.randbelow(10**6):06d}"
    db.add(OtpCode(
        email=email,
        code_hash=keyed_hash(f"{email}:{code}"),
        ip_hash=ip_hash,
        expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
    ))
    await db.commit()  # persist before sending so the rate limit holds even if sending fails

    try:
        await sender.send_otp(email, code, settings.OTP_TTL_SECONDS // 60)
    except Exception:
        logger.exception("otp_email_failed")
        raise AkamException(code="EMAIL_SEND_FAILED", message="Could not send the code. Please try again.", status_code=503)

    # Same response whether or not the email already has an account.
    return ApiResponse(data=RequestOtpData(expires_in=settings.OTP_TTL_SECONDS), meta=_make_meta(request))


@router.post("/verify-otp", response_model=ApiResponse[AuthTokenData])
async def verify_otp(body: VerifyOtpRequest, db: DbDep, request: Request) -> ApiResponse[AuthTokenData]:
    email = body.email.strip().lower()
    now = _now()
    otp = (await db.execute(
        select(OtpCode).where(OtpCode.email == email, OtpCode.consumed_at.is_(None)).order_by(OtpCode.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    if not otp or _aware(otp.expires_at) <= now:
        raise AkamException(code="OTP_INVALID", message="Code is invalid or expired.", status_code=400)
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise AkamException(code="OTP_ATTEMPTS_EXCEEDED", message="Too many attempts. Request a new code.", status_code=429)

    if not hmac.compare_digest(otp.code_hash, keyed_hash(f"{email}:{body.code}")):
        otp.attempts += 1
        await db.commit()  # get_db rolls back on exceptions; the attempt must stick
        raise AkamException(code="OTP_INVALID", message="Code is invalid or expired.", status_code=400)

    otp.consumed_at = now
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    is_new = user is None
    if user is None:
        user = User(email=email, name=email.split("@")[0][:100], language=body.language, status="active", token_generation=0)
        db.add(user)
        await db.flush()
        db.add(UserPreferences(user_id=user.id))
    elif user.status != "active":
        raise UnauthorizedException(code="TOKEN_REVOKED", message="User account is inactive.")
    if body.fcm_token:
        user.fcm_token = body.fcm_token
    user.device_platform = body.device_platform

    data = await _issue_session(db, user, body.device_id, is_new)
    await db.commit()
    return ApiResponse(data=data, meta=_make_meta(request))


@router.post(
    "/register",
    response_model=ApiResponse[AuthTokenData],
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
    summary="Legacy device-only registration (disabled unless ENABLE_LEGACY_REGISTER=true)",
)
async def register(body: RegisterRequest, db: DbDep, request: Request) -> ApiResponse[AuthTokenData]:
    if not settings.ENABLE_LEGACY_REGISTER:
        raise NotFoundException(message="Not found.")
    clean_name = sanitise_text(body.name, max_length=100)
    user = (await db.execute(select(User).where(User.device_id == body.device_id))).scalar_one_or_none()
    is_new = user is None
    if is_new:
        user = User(name=clean_name, language=body.language, device_id=body.device_id, status="active", token_generation=0)
        db.add(user)
        await db.flush()
        db.add(UserPreferences(user_id=user.id))
    user.name = clean_name
    user.fcm_token = body.fcm_token
    user.device_platform = body.device_platform
    data = await _issue_session(db, user, body.device_id, is_new)
    await db.commit()
    return ApiResponse(data=data, meta=_make_meta(request))


@router.post("/refresh", response_model=ApiResponse[RefreshTokenData])
async def refresh(body: RefreshRequest, db: DbDep, request: Request) -> ApiResponse[RefreshTokenData]:
    payload = verify_token(body.refresh_token)
    if payload.get("scope") != "refresh":
        raise UnauthorizedException(code="TOKEN_INVALID", message="Provided token is not a refresh token.")

    row = await db.get(RefreshToken, payload.get("jti", ""))
    session = await db.get(AuthSession, row.session_id) if row else None
    if not row or not session:
        raise UnauthorizedException(code="TOKEN_INVALID", message="Token is invalid or malformed.")
    # Secret first: a stolen refresh token alone can neither refresh nor trigger family revocation.
    if not hmac.compare_digest(session.device_secret_hash, keyed_hash(body.device_secret)):
        raise UnauthorizedException(code="TOKEN_INVALID", message="Device secret mismatch.")
    if session.revoked_at is not None or row.revoked_at is not None:
        raise UnauthorizedException(code="TOKEN_REVOKED", message="Token has been revoked.")
    if row.rotated_at is not None:
        # Rotated token replayed: assume theft and kill the whole family.
        await _revoke_sessions(db, [AuthSession.id == session.id])
        await db.commit()
        logger.warning("refresh_token_reuse", session_id=session.id)
        raise UnauthorizedException(code="TOKEN_REUSE_DETECTED", message="Refresh token reuse detected; session revoked.")

    user = (await db.execute(select(User).where(User.id == session.user_id, User.status == "active"))).scalar_one_or_none()
    if not user:
        raise UnauthorizedException(code="TOKEN_REVOKED", message="User account not found or inactive.")

    row.rotated_at = _now()
    new_refresh = await _new_refresh_row(db, session)
    await db.commit()
    return ApiResponse(
        data=RefreshTokenData(
            access_token=create_access_token(user.id, session.device_id, session.id),
            refresh_token=new_refresh,
            expires_in=settings.ACCESS_TOKEN_TTL_SECONDS,
            refresh_expires_in=settings.REFRESH_TOKEN_TTL_SECONDS,
        ),
        meta=_make_meta(request),
    )


@router.post("/logout", response_model=ApiResponse[LogoutData])
async def logout(body: LogoutRequest, current_user: CurrentUserDep, db: DbDep, request: Request) -> ApiResponse[LogoutData]:
    # Revoking the session invalidates both its access tokens and its refresh tokens.
    await _revoke_sessions(db, [AuthSession.id == request.state.session_id, AuthSession.user_id == current_user.id])
    await db.commit()
    return ApiResponse(data=LogoutData(revoked=True), meta=_make_meta(request))


@router.post("/logout_all", response_model=ApiResponse[LogoutAllData])
async def logout_all(current_user: CurrentUserDep, db: DbDep, request: Request) -> ApiResponse[LogoutAllData]:
    count = await _revoke_sessions(db, [AuthSession.user_id == current_user.id])
    await db.commit()
    return ApiResponse(data=LogoutAllData(sessions_revoked=count), meta=_make_meta(request))


@router.put("/device", response_model=ApiResponse[DeviceUpdateData])
async def update_device(body: DeviceUpdateRequest, current_user: CurrentUserDep, db: DbDep, request: Request) -> ApiResponse[DeviceUpdateData]:
    current_user.fcm_token = body.fcm_token
    current_user.device_platform = body.device_platform
    await db.commit()
    return ApiResponse(data=DeviceUpdateData(updated=True), meta=_make_meta(request))
