from fastapi import APIRouter
from app.dependencies import CurrentUserDep, DbDep
from app.models.schemas.common import ApiResponse
from pydantic import BaseModel

class PinnedItemResponse(BaseModel):
    id: str
    type: str
    title: str
    date: str
    location: str | None = None
    media_url: str | None = None
    badge: str | None = None
    is_pinned: bool

class PinnedFeedResponse(BaseModel):
    items: list[PinnedItemResponse]

router = APIRouter(prefix="/feed", tags=["feed"])

@router.get("/pinned", response_model=ApiResponse[PinnedFeedResponse])
async def get_pinned_feed(
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[PinnedFeedResponse]:
    # Mocking implementation for frontend integration
    return ApiResponse(
        data=PinnedFeedResponse(
            items=[
                {
                    "id": "pin_101",
                    "type": "memory",
                    "title": "Atmosphere & Wave Reflection",
                    "date": "2026-01-01T00:00:00Z",
                    "location": "Miami",
                    "media_url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750",
                    "badge": "Video",
                    "is_pinned": True
                }
            ]
        )
    )
