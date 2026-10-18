from datetime import datetime
from pydantic import BaseModel, Field


class BackupMetadataResponse(BaseModel):
    backup_id: str
    version: int
    sha256: str
    size_bytes: int
    download_url: str
    created_at: datetime


class BackupDeleteResponse(BaseModel):
    deleted: bool = True
    deleted_count: int
