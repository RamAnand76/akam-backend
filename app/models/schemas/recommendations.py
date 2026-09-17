from pydantic import BaseModel
from typing import Any


class RecommendationResponse(BaseModel):
    id: str
    title: str
    subtitle: str | None = None
    action_type: str
    meta_data: dict[str, Any] | None = None
