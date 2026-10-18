from datetime import datetime, timezone
from fastapi import APIRouter, Request, status

from app.dependencies import CurrentUserDep, DbDep
from app.models.db.analytics import AnalyticsEvent
from app.models.schemas.analytics import AnalyticsIngestRequest, AnalyticsIngestResponse
from app.models.schemas.common import ApiResponse, Meta

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _meta(request: Request) -> Meta:
    return Meta(
        request_id=getattr(request.state, "request_id", "unknown"),
        timestamp=datetime.now(timezone.utc),
        version="2.0.0",
    )


@router.post(
    "/events",
    response_model=ApiResponse[AnalyticsIngestResponse],
    status_code=status.HTTP_200_OK,
    summary="Ingest privacy-preserving, allow-listed anonymous telemetry events",
)
async def ingest_analytics_events(
    body: AnalyticsIngestRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[AnalyticsIngestResponse]:
    # Persist batch of anonymous events. Notice we explicitly DO NOT attach current_user.id or email.
    for event_item in body.events:
        db.add(
            AnalyticsEvent(
                anon_id=body.anon_id,
                app_version=body.app_version,
                event_name=event_item.name,
                event_timestamp=event_item.ts,
                properties=event_item.props,
            )
        )
    await db.commit()

    return ApiResponse(
        data=AnalyticsIngestResponse(accepted=len(body.events)),
        meta=_meta(request),
    )
