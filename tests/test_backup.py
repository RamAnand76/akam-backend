import hashlib
import io
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models.db.backup import UserBackup


@pytest.mark.asyncio
async def test_backup_upload_download_lifecycle(client: AsyncClient, auth_headers: dict, async_db):
    """Happy path: Upload opaque backup blob, retrieve metadata, download, and delete."""
    fake_ciphertext = b"\x00\x01\x02\x03CIPHERTEXT_BLOB_FOR_TESTING\xaa\xbb\xcc"
    sha256_hex = hashlib.sha256(fake_ciphertext).hexdigest()

    # 1. Upload
    files = {"file": ("backup.enc", io.BytesIO(fake_ciphertext), "application/octet-stream")}
    headers = {
        **auth_headers,
        "X-Backup-Version": "1",
        "X-Backup-Sha256": sha256_hex,
    }
    upload_resp = await client.put("/backup", headers=headers, files=files)
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()["data"]
    assert upload_data["version"] == 1
    assert upload_data["sha256"] == sha256_hex
    assert upload_data["size_bytes"] == len(fake_ciphertext)
    backup_id = upload_data["backup_id"]

    # 2. Get latest metadata
    meta_resp = await client.get("/backup", headers=auth_headers)
    assert meta_resp.status_code == 200
    assert meta_resp.json()["data"]["backup_id"] == backup_id

    # 3. Download raw bytes
    down_resp = await client.get("/backup/download", headers=auth_headers)
    assert down_resp.status_code == 200
    assert down_resp.content == fake_ciphertext
    assert down_resp.headers["X-Backup-Sha256"] == sha256_hex

    # 4. Delete
    del_resp = await client.delete("/backup", headers=auth_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted_count"] >= 1

    # Confirm 404 on subsequent get
    assert (await client.get("/backup", headers=auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_backup_checksum_mismatch_rejected(client: AsyncClient, auth_headers: dict):
    """Integrity test: Uploading a blob with incorrect SHA256 header must fail with 422."""
    fake_ciphertext = b"test payload"
    wrong_sha256 = "0" * 64

    files = {"file": ("backup.enc", io.BytesIO(fake_ciphertext), "application/octet-stream")}
    headers = {
        **auth_headers,
        "X-Backup-Version": "1",
        "X-Backup-Sha256": wrong_sha256,
    }
    resp = await client.put("/backup", headers=headers, files=files)
    assert resp.status_code == 422
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_backup_empty_blob_rejected(client: AsyncClient, auth_headers: dict):
    """Validation test: Empty backup blob is rejected with 422."""
    empty_bytes = b""
    sha256_hex = hashlib.sha256(empty_bytes).hexdigest()

    files = {"file": ("backup.enc", io.BytesIO(empty_bytes), "application/octet-stream")}
    headers = {
        **auth_headers,
        "X-Backup-Version": "1",
        "X-Backup-Sha256": sha256_hex,
    }
    resp = await client.put("/backup", headers=headers, files=files)
    assert resp.status_code == 422
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_backup_retention_limit_pruning(client: AsyncClient, auth_headers: dict, async_db):
    """Retention test: Uploading 6 versions retains only the top 5."""
    for v in range(1, 7):
        blob = f"backup_version_{v}_payload".encode()
        sha = hashlib.sha256(blob).hexdigest()
        files = {"file": ("backup.enc", io.BytesIO(blob), "application/octet-stream")}
        headers = {**auth_headers, "X-Backup-Version": str(v), "X-Backup-Sha256": sha}
        resp = await client.put("/backup", headers=headers, files=files)
        assert resp.status_code == 200

    # Verify database has at most 5 backups
    db_backups = (await async_db.execute(select(UserBackup))).scalars().all()
    assert len(db_backups) == 5
