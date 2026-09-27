from datetime import datetime
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    request_id: str = Field(..., description="Unique trace ID for the request")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp")
    version: str = Field(default="2.0.0", description="API version")


class Pagination(BaseModel):
    cursor: str | None = Field(default=None, description="Cursor for the next page")
    has_more: bool = Field(..., description="Whether more items exist")
    total_count: int = Field(..., description="Total items available")
    limit: int = Field(..., description="Maximum items returned in this page")


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    pagination: Pagination


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str
    value_received: Any = None


class ApiError(BaseModel):
    code: str
    message: str
    field: str | None = None
    details: list[ErrorDetail] = []
    doc_url: str = "https://docs.akam.app/errors"


from pydantic import BaseModel, Field, model_validator

class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ApiError | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode='before')
    @classmethod
    def convert_legacy_args(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "status" in data:
                data["success"] = (data.pop("status") == "success")
            if "meta" in data:
                meta = data.pop("meta")
                if hasattr(meta, "timestamp"):
                    data["timestamp"] = meta.timestamp
                elif isinstance(meta, dict) and "timestamp" in meta:
                    data["timestamp"] = meta["timestamp"]
        return data
