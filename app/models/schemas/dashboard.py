from pydantic import BaseModel
from typing import Any
from app.models.schemas.recommendations import RecommendationResponse
from app.models.schemas.clusters import ClusterItem


class UserProfileResponse(BaseModel):
    id: str
    name: str
    language: str


class DashboardHomeResponse(BaseModel):
    profile: UserProfileResponse
    recommendations: list[RecommendationResponse]
    pinned_clusters: list[ClusterItem]
    unread_notifications_count: int
