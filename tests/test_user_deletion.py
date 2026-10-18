import hashlib
import io
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.db.auth import AuthSession, RefreshToken
from app.models.db.backup import UserBackup
from app.models.db.user import User, UserPreferences


@pytest.mark.asyncio
async def test_real_account_deletion_cleans_all_tables(client: AsyncClient, auth_headers: dict, async_db):
    """Integrity test: DELETE /user/data completely purges user, sessions, backups, and preferences."""
    # 1. Fetch user ID
    me_resp = await client.get("/user/me", headers=auth_headers)
    assert me_resp.status_code == 200
    user_id = me_resp.json()["data"]["user_id"]

    # 2. Upload a backup for this user
    blob = b"sample_encrypted_data"
    sha = hashlib.sha256(blob).hexdigest()
    files = {"file": ("backup.enc", io.BytesIO(blob), "application/octet-stream")}
    headers = {**auth_headers, "X-Backup-Version": "1", "X-Backup-Sha256": sha}
    await client.put("/backup", headers=headers, files=files)

    # 3. Confirm rows exist in tables
    assert (await async_db.execute(select(User).where(User.id == user_id))).scalar_one_or_none() is not None
    assert (await async_db.execute(select(UserPreferences).where(UserPreferences.user_id == user_id))).scalar_one_or_none() is not None
    assert (await async_db.execute(select(UserBackup).where(UserBackup.user_id == user_id))).scalars().all() != []

    # 4. Trigger account deletion with exact confirmation
    del_resp = await client.request(
        "DELETE",
        "/user/data",
        headers=auth_headers,
        json={"confirmation": "DELETE MY DATA"},
    )
    assert del_resp.status_code == 200
    del_data = del_resp.json()["data"]
    assert del_data["status"] == "completed"
    assert del_data["steps"]["user_account_deleted"] is True
    assert del_data["steps"]["backups_purged"] is True

    # 5. Assert ZERO rows remain in any user-scoped table
    assert (await async_db.execute(select(User).where(User.id == user_id))).scalar_one_or_none() is None
    assert (await async_db.execute(select(UserPreferences).where(UserPreferences.user_id == user_id))).scalar_one_or_none() is None
    assert (await async_db.execute(select(AuthSession).where(AuthSession.user_id == user_id))).scalars().all() == []
    assert (await async_db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id))).scalars().all() == []
    assert (await async_db.execute(select(UserBackup).where(UserBackup.user_id == user_id))).scalars().all() == []

    # 6. Verify subsequent requests with old token fail with 401
    follow_up_resp = await client.get("/user/me", headers=auth_headers)
    assert follow_up_resp.status_code == 401
