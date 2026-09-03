from datetime import datetime
from pydantic import BaseModel, Field


class ClusterPreview(BaseModel):
    type: str = "text_cards"
    snippets: list[str] = []


class CrossClusterLink(BaseModel):
    cluster_id: str
    label: str
    edge_weight: float
    shared_message_count: int = 1


class ClusterItem(BaseModel):
    cluster_id: str
    label: str
    card_style: str = "standard"
    color_accent: str | None = None
    preview: ClusterPreview | None = None
    message_count: int = 0
    last_active: datetime
    tags: list[str] = []
    cross_cluster_links: list[CrossClusterLink] = []


class CreateClusterRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=200)
    color_accent: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class PatchClusterRequest(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    color_accent: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class DeleteClusterData(BaseModel):
    deleted: bool = True
    messages_queued_for_reassignment: int = 0
    reassignment_job_id: str = "local-reassignment-completed"


class ClusterMemberMessage(BaseModel):
    message_id: str
    content: str
    role: str
    created_at: datetime
    membership_weight: float = 0.90
    is_partial_member: bool = False
    also_in_clusters: list[dict] = []


class ClusterDetailData(BaseModel):
    cluster: ClusterItem
    items: list[ClusterMemberMessage]
