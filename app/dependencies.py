from typing import Annotated
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.exceptions import UnauthorizedException
from app.models.db.user import User
from app.security.jwt import verify_token

DbDep = Annotated[AsyncSession, Depends(get_db)]
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    db: DbDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> User:
    if not credentials or not credentials.credentials:
        raise UnauthorizedException(code="UNAUTHORIZED", message="Missing or malformed Authorization Bearer token.")

    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(code="UNAUTHORIZED", message="Invalid token claims.")

    # Attach to request state for middleware tracking
    request.state.user_id = user_id

    result = await db.execute(select(User).where(User.id == user_id, User.status == "active"))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedException(code="TOKEN_REVOKED", message="User account is inactive or not found.")

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
