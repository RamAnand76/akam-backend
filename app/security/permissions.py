import asyncio
import time
from typing import Any
from app.exceptions import NotFoundException


async def ensure_ownership(
    entity: Any | None,
    user_id: str,
    entity_user_id_field: str = "user_id",
    min_response_ms: float = 0.050,
) -> Any:
    """
    Enforces object ownership. If entity does not exist or belongs to another user,
    raises ENTITY_NOT_FOUND (404) with minimum 50ms constant-time sleep to prevent
    timing-based enumeration attacks.
    """
    start = time.monotonic()
    
    is_valid = False
    if entity is not None:
        owner_id = str(getattr(entity, entity_user_id_field, ""))
        if owner_id == str(user_id):
            is_valid = True

    elapsed = time.monotonic() - start
    if elapsed < min_response_ms:
        await asyncio.sleep(min_response_ms - elapsed)

    if not is_valid:
        raise NotFoundException("ENTITY_NOT_FOUND", "The requested entity does not exist.")

    return entity
