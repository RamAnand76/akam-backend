from datetime import datetime
from fastapi import APIRouter, Request
from app.dependencies import CurrentUserDep, DbDep
from app.models.schemas.dashboard import DashboardHomeResponse, UserProfileResponse
from app.models.schemas.common import ApiResponse, Meta

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


@router.get("/home", response_model=ApiResponse[DashboardHomeResponse])
async def get_dashboard_home(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[DashboardHomeResponse]:
    # Mocking implementation for frontend integration
    return ApiResponse(
        status="success",
        data=DashboardHomeResponse(
            profile=UserProfileResponse(
                id=current_user.id,
                name=current_user.name if hasattr(current_user, "name") else "User",
                language="en"
            ),
            recommendations=[],
            pinned_clusters=[],
            unread_notifications_count=0
        ),
        meta=_make_meta(request),
    )
