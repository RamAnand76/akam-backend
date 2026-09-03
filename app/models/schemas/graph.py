from datetime import datetime
from pydantic import BaseModel, Field


class NodePosition(BaseModel):
    x: float
    y: float


class NodeItem(BaseModel):
    node_id: str
    label: str
    type: str
    display_type: str
    body_preview: str | None = None
    tags: list[str] = []
    position: NodePosition | None = None
    is_active: bool = True
    edge_count: int = 0
    last_active: datetime


class EdgeItem(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    weight: float
    edge_type: str | None = None
    llm_labeled: bool = False


class GraphStats(BaseModel):
    total_nodes: int
    total_edges: int
    strongest_node_label: str | None = None
    most_active_topic: str | None = None


class GraphData(BaseModel):
    nodes: list[NodeItem]
    edges: list[EdgeItem]
    graph_stats: GraphStats


class NeighbourItem(BaseModel):
    node_id: str
    label: str
    display_type: str
    edge_weight: float
    edge_type: str | None = None
    edge_id: str


class RelatedMessageItem(BaseModel):
    message_id: str
    content_preview: str
    created_at: datetime


class NodeDetailData(BaseModel):
    node_id: str
    label: str
    type: str
    display_type: str
    body_preview: str | None = None
    tags: list[str] = []
    position: NodePosition | None = None
    is_active: bool = True
    edge_count: int = 0
    last_active: datetime
    neighbours: list[NeighbourItem] = []
    related_messages: list[RelatedMessageItem] = []


class UpdateNodeRequest(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    tags: list[str] | None = None
    position: NodePosition | None = None


class DeleteNodeData(BaseModel):
    deleted: bool = True
    edges_removed: int
    node_id: str
