from datetime import datetime
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")

class Meta(BaseModel):
    request_id: str
    timestamp: datetime

class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: Any | None = None
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

# Test
m = Meta(request_id="123", timestamp=datetime(2026, 1, 1))
resp = ApiResponse(status="success", data={"hello": "world"}, meta=m)
print(resp.model_dump_json(indent=2))
