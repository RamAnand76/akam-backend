from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Query, Request
from sqlalchemy import func, or_, select
from app.dependencies import CurrentUserDep, DbDep
from app.models.db.graph import Edge, Node
from app.models.schemas.common import ApiResponse, Meta
from app.models.schemas.graph import (
    DeleteNodeData,
    EdgeItem,
    GraphData,
    GraphStats,
    NeighbourItem,
    NodeDetailData,
    NodeItem,
    NodePosition,
    UpdateNodeRequest,
)
from app.security.permissions import ensure_ownership
from app.security.sanitiser import sanitise_text

router = APIRouter(prefix="/graph", tags=["graph"])


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


@router.get("", response_model=ApiResponse[GraphData])
async def get_graph(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
    type_filter: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    min_edge_weight: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
) -> ApiResponse[GraphData]:
    # Query Nodes
    node_query = select(Node).where(Node.user_id == current_user.id, Node.is_active == True)
    if type_filter:
        types = [t.strip() for t in type_filter.split(",")]
        node_query = node_query.where(Node.type.in_(types))
    node_query = node_query.limit(limit)

    node_res = await db.execute(node_query)
    nodes = node_res.scalars().all()
    node_ids = {n.id for n in nodes}

    # Query Edges
    edge_query = select(Edge).where(
        Edge.user_id == current_user.id,
        Edge.weight >= min_edge_weight,
    )
    edge_res = await db.execute(edge_query)
    edges = [e for e in edge_res.scalars().all() if e.source_node_id in node_ids and e.target_node_id in node_ids]

    # Edge count map per node
    edge_counts: dict[str, int] = {nid: 0 for nid in node_ids}
    for e in edges:
        edge_counts[e.source_node_id] = edge_counts.get(e.source_node_id, 0) + 1
        edge_counts[e.target_node_id] = edge_counts.get(e.target_node_id, 0) + 1

    node_items = [
        NodeItem(
            node_id=n.id,
            label=n.label,
            type=n.type,
            display_type=n.display_type,
            body_preview=n.body_preview,
            tags=n.tags,
            position=NodePosition(x=n.pos_x, y=n.pos_y) if n.pos_x is not None and n.pos_y is not None else None,
            is_active=n.is_active,
            edge_count=edge_counts.get(n.id, 0),
            last_active=n.last_active,
        )
        for n in nodes
    ]

    edge_items = [
        EdgeItem(
            edge_id=e.id,
            source_node_id=e.source_node_id,
            target_node_id=e.target_node_id,
            weight=e.weight,
            edge_type=e.edge_type,
            llm_labeled=e.llm_labeled,
        )
        for e in edges
    ]

    # Summary statistics
    stats = GraphStats(
        total_nodes=len(node_items),
        total_edges=len(edge_items),
        strongest_node_label=node_items[0].label if node_items else None,
        most_active_topic="General",
    )

    return ApiResponse(
        status="success",
        data=GraphData(nodes=node_items, edges=edge_items, graph_stats=stats),
        meta=_make_meta(request),
    )


@router.get("/nodes/{node_id}", response_model=ApiResponse[NodeDetailData])
async def get_node(
    node_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[NodeDetailData]:
    result = await db.execute(
        select(Node).where(Node.id == node_id, Node.user_id == current_user.id)
    )
    node = result.scalar_one_or_none()
    await ensure_ownership(node, current_user.id)

    # Fetch incident edges
    edge_res = await db.execute(
        select(Edge).where(
            Edge.user_id == current_user.id,
            or_(Edge.source_node_id == node_id, Edge.target_node_id == node_id),
        )
    )
    edges = edge_res.scalars().all()

    # Fetch neighbours
    neighbour_ids = [e.target_node_id if e.source_node_id == node_id else e.source_node_id for e in edges]
    neighbours: list[NeighbourItem] = []
    if neighbour_ids:
        neigh_res = await db.execute(
            select(Node).where(Node.id.in_(neighbour_ids), Node.user_id == current_user.id)
        )
        neigh_map = {n.id: n for n in neigh_res.scalars().all()}
        for e in edges:
            other_id = e.target_node_id if e.source_node_id == node_id else e.source_node_id
            if other_id in neigh_map:
                n_obj = neigh_map[other_id]
                neighbours.append(
                    NeighbourItem(
                        node_id=n_obj.id,
                        label=n_obj.label,
                        display_type=n_obj.display_type,
                        edge_weight=e.weight,
                        edge_type=e.edge_type,
                        edge_id=e.id,
                    )
                )

    detail = NodeDetailData(
        node_id=node.id,
        label=node.label,
        type=node.type,
        display_type=node.display_type,
        body_preview=node.body_preview,
        tags=node.tags,
        position=NodePosition(x=node.pos_x, y=node.pos_y) if node.pos_x is not None and node.pos_y is not None else None,
        is_active=node.is_active,
        edge_count=len(edges),
        last_active=node.last_active,
        neighbours=neighbours,
        related_messages=[],
    )

    return ApiResponse(status="success", data=detail, meta=_make_meta(request))


@router.patch("/nodes/{node_id}", response_model=ApiResponse[NodeItem])
async def patch_node(
    node_id: str,
    body: UpdateNodeRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[NodeItem]:
    result = await db.execute(
        select(Node).where(Node.id == node_id, Node.user_id == current_user.id)
    )
    node = result.scalar_one_or_none()
    await ensure_ownership(node, current_user.id)

    if body.label is not None:
        node.label = sanitise_text(body.label, max_length=200)
    if body.tags is not None:
        node.tags = [sanitise_text(t, max_length=50) for t in body.tags[:10]]
    if body.position is not None:
        node.pos_x = body.position.x
        node.pos_y = body.position.y

    await db.commit()

    return ApiResponse(
        status="success",
        data=NodeItem(
            node_id=node.id,
            label=node.label,
            type=node.type,
            display_type=node.display_type,
            body_preview=node.body_preview,
            tags=node.tags,
            position=NodePosition(x=node.pos_x, y=node.pos_y) if node.pos_x is not None and node.pos_y is not None else None,
            is_active=node.is_active,
            edge_count=0,
            last_active=node.last_active,
        ),
        meta=_make_meta(request),
    )


@router.delete("/nodes/{node_id}", response_model=ApiResponse[DeleteNodeData])
async def delete_node(
    node_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[DeleteNodeData]:
    result = await db.execute(
        select(Node).where(Node.id == node_id, Node.user_id == current_user.id)
    )
    node = result.scalar_one_or_none()
    await ensure_ownership(node, current_user.id)

    # Count edges
    edge_res = await db.execute(
        select(Edge).where(
            Edge.user_id == current_user.id,
            or_(Edge.source_node_id == node_id, Edge.target_node_id == node_id),
        )
    )
    edges = edge_res.scalars().all()
    edge_count = len(edges)

    for e in edges:
        await db.delete(e)
    await db.delete(node)
    await db.commit()

    return ApiResponse(
        status="success",
        data=DeleteNodeData(deleted=True, edges_removed=edge_count, node_id=node_id),
        meta=_make_meta(request),
    )


@router.get("/subgraph", response_model=ApiResponse[GraphData])
async def get_subgraph(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
    node_id: Annotated[str, Query()],
    depth: Annotated[int, Query(ge=1, le=2)] = 1,
) -> ApiResponse[GraphData]:
    # Root node check
    res = await db.execute(select(Node).where(Node.id == node_id, Node.user_id == current_user.id))
    root = res.scalar_one_or_none()
    await ensure_ownership(root, current_user.id)

    visited_node_ids = {node_id}
    current_layer = {node_id}

    edges_collected: list[Edge] = []
    for _ in range(depth):
        if not current_layer:
            break
        edge_res = await db.execute(
            select(Edge).where(
                Edge.user_id == current_user.id,
                or_(Edge.source_node_id.in_(current_layer), Edge.target_node_id.in_(current_layer)),
            )
        )
        layer_edges = edge_res.scalars().all()
        next_layer = set()
        for e in layer_edges:
            edges_collected.append(e)
            next_layer.add(e.source_node_id)
            next_layer.add(e.target_node_id)
        current_layer = next_layer - visited_node_ids
        visited_node_ids.update(next_layer)

    node_res = await db.execute(select(Node).where(Node.id.in_(visited_node_ids)))
    nodes = node_res.scalars().all()

    node_items = [
        NodeItem(
            node_id=n.id,
            label=n.label,
            type=n.type,
            display_type=n.display_type,
            body_preview=n.body_preview,
            tags=n.tags,
            position=NodePosition(x=n.pos_x, y=n.pos_y) if n.pos_x is not None and n.pos_y is not None else None,
            is_active=n.is_active,
            edge_count=0,
            last_active=n.last_active,
        )
        for n in nodes
    ]

    edge_items = [
        EdgeItem(
            edge_id=e.id,
            source_node_id=e.source_node_id,
            target_node_id=e.target_node_id,
            weight=e.weight,
            edge_type=e.edge_type,
            llm_labeled=e.llm_labeled,
        )
        for e in edges_collected
    ]

    return ApiResponse(
        status="success",
        data=GraphData(
            nodes=node_items,
            edges=edge_items,
            graph_stats=GraphStats(total_nodes=len(node_items), total_edges=len(edge_items)),
        ),
        meta=_make_meta(request),
    )
