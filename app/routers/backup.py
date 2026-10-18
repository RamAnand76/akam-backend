import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Header, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, select

from app.config import settings
from app.dependencies import CurrentUserDep, DbDep
from app.exceptions import AkamException, NotFoundException, ValidationException
from app.models.db.backup import UserBackup
from app.models.schemas.backup import BackupDeleteResponse, BackupMetadataResponse
from app.models.schemas.common import ApiResponse, Meta

router = APIRouter(prefix="/backup", tags=["backup"])

MAX_BACKUP_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit
MAX_BACKUP_VERSIONS = 5

if os.name == "nt":
    BACKUP_DIR = Path("./data/backups")
else:
    BACKUP_DIR = Path("/tmp/backups")


def _meta(request: Request) -> Meta:
    return Meta(
        request_id=getattr(request.state, "request_id", "unknown"),
        timestamp=datetime.now(timezone.utc),
        version="2.0.0",
    )


@router.put("", response_model=ApiResponse[BackupMetadataResponse])
async def upload_backup(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
    file: UploadFile = File(...),
    x_backup_version: Annotated[int, Header()] = 1,
    x_backup_sha256: Annotated[str, Header()] = "",
) -> ApiResponse[BackupMetadataResponse]:
    """Upload an opaque encrypted backup blob."""
    sha256_header = x_backup_sha256.strip().lower()
    if not sha256_header or len(sha256_header) != 64:
        raise ValidationException("Missing or invalid 'X-Backup-Sha256' header (must be 64-character hex string).")

    contents = await file.read()
    size_bytes = len(contents)

    if size_bytes == 0:
        raise ValidationException("Uploaded backup blob is empty.")
    if size_bytes > MAX_BACKUP_SIZE_BYTES:
        raise ValidationException(f"Backup size exceeds maximum limit of {MAX_BACKUP_SIZE_BYTES // (1024 * 1024)}MB.")

    computed_sha256 = hashlib.sha256(contents).hexdigest().lower()
    if computed_sha256 != sha256_header:
        raise ValidationException(
            f"Checksum verification failed. Provided: {sha256_header}, Computed: {computed_sha256}."
        )

    # Save to disk / storage
    user_dir = BACKUP_DIR / current_user.id
    user_dir.mkdir(parents=True, exist_ok=True)

    backup_record = UserBackup(
        user_id=current_user.id,
        version=x_backup_version,
        sha256=computed_sha256,
        size_bytes=size_bytes,
        storage_path="",
    )
    db.add(backup_record)
    await db.flush()

    file_path = user_dir / f"{backup_record.id}.enc"
    file_path.write_bytes(contents)
    backup_record.storage_path = str(file_path)

    # Prune older versions if count > MAX_BACKUP_VERSIONS
    existing_backups = (
        await db.execute(
            select(UserBackup)
            .where(UserBackup.user_id == current_user.id)
            .order_by(UserBackup.created_at.desc())
        )
    ).scalars().all()

    if len(existing_backups) > MAX_BACKUP_VERSIONS:
        for old in existing_backups[MAX_BACKUP_VERSIONS:]:
            try:
                Path(old.storage_path).unlink(missing_ok=True)
            except OSError:
                pass
            await db.delete(old)

    await db.commit()

    download_url = f"{str(request.base_url).rstrip('/')}/api/v1/backup/download"
    return ApiResponse(
        data=BackupMetadataResponse(
            backup_id=backup_record.id,
            version=backup_record.version,
            sha256=backup_record.sha256,
            size_bytes=backup_record.size_bytes,
            download_url=download_url,
            created_at=backup_record.created_at,
        ),
        meta=_meta(request),
    )


@router.get("", response_model=ApiResponse[BackupMetadataResponse])
async def get_latest_backup_metadata(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[BackupMetadataResponse]:
    """Retrieve metadata of the user's latest encrypted backup."""
    backup = (
        await db.execute(
            select(UserBackup)
            .where(UserBackup.user_id == current_user.id)
            .order_by(UserBackup.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if not backup:
        raise NotFoundException(code="BACKUP_NOT_FOUND", message="No backup found for this account.")

    download_url = f"{str(request.base_url).rstrip('/')}/api/v1/backup/download"
    return ApiResponse(
        data=BackupMetadataResponse(
            backup_id=backup.id,
            version=backup.version,
            sha256=backup.sha256,
            size_bytes=backup.size_bytes,
            download_url=download_url,
            created_at=backup.created_at,
        ),
        meta=_meta(request),
    )


@router.get("/download")
async def download_latest_backup(
    current_user: CurrentUserDep,
    db: DbDep,
) -> FileResponse:
    """Download the raw opaque encrypted backup bytes."""
    backup = (
        await db.execute(
            select(UserBackup)
            .where(UserBackup.user_id == current_user.id)
            .order_by(UserBackup.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if not backup or not Path(backup.storage_path).exists():
        raise NotFoundException(code="BACKUP_NOT_FOUND", message="No backup file found to download.")

    return FileResponse(
        path=backup.storage_path,
        media_type="application/octet-stream",
        filename=f"akam_backup_v{backup.version}.enc",
        headers={"X-Backup-Sha256": backup.sha256, "X-Backup-Version": str(backup.version)},
    )


@router.delete("", response_model=ApiResponse[BackupDeleteResponse])
async def delete_all_backups(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[BackupDeleteResponse]:
    """Permanently delete all backups for the authenticated user."""
    backups = (
        await db.execute(
            select(UserBackup).where(UserBackup.user_id == current_user.id)
        )
    ).scalars().all()

    deleted_count = len(backups)
    for b in backups:
        try:
            Path(b.storage_path).unlink(missing_ok=True)
        except OSError:
            pass
        await db.delete(b)

    await db.commit()
    return ApiResponse(
        data=BackupDeleteResponse(deleted=True, deleted_count=deleted_count),
        meta=_meta(request),
    )
