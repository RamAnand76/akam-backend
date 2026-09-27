from fastapi import APIRouter
from app.dependencies import CurrentUserDep, DbDep
from app.models.schemas.common import ApiResponse
from pydantic import BaseModel
from typing import Any

class MemoryResponse(BaseModel):
    id: str
    title: str
    subtitle: str | None = None
    badge: str | None = None
    top_icon: str | None = None
    image_url: str | None = None
    is_saved: bool
    created_at: str

class MemoriesListResponse(BaseModel):
    memories: list[MemoryResponse]

class GraphNodeResponse(BaseModel):
    id: str
    title: str
    category: str
    weight: int
    color: str

class GraphEdgeResponse(BaseModel):
    source: str
    target: str
    relationship: str

class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]

router = APIRouter(prefix="/memories", tags=["memories"])

@router.get("", response_model=ApiResponse[MemoriesListResponse])
async def get_memories(
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[MemoriesListResponse]:
    return ApiResponse(
        data=MemoriesListResponse(
            memories=[
                {
                    "id": "mem_001",
                    "title": "MAGNA\nCOASTAL",
                    "subtitle": "NOVEMBER",
                    "badge": "$ Invest In Future",
                    "top_icon": "hotel_outlined",
                    "image_url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750",
                    "is_saved": False,
                    "created_at": "2026-09-20T10:00:00Z"
                },
                {
                    "id": "mem_002",
                    "title": "SERENO\nHAVEN",
                    "subtitle": "OCTOBER",
                    "badge": "Explore Sanctuary",
                    "top_icon": "spa_outlined",
                    "image_url": "https://images.unsplash.com/photo-1613977257363-707ba9348227",
                    "is_saved": True,
                    "created_at": "2026-09-18T14:30:00Z"
                }
            ]
        )
    )

@router.post("/{id}/save", response_model=ApiResponse[dict[str, Any]])
async def save_memory(
    id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[dict[str, Any]]:
    return ApiResponse(
        data={
            "memory_id": id,
            "is_saved": True,
            "message": "Saved memory to vault!"
        }
    )

@router.get("/graph", response_model=ApiResponse[GraphResponse])
async def get_memories_graph(
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[GraphResponse]:
    return ApiResponse(
        data=GraphResponse(
            nodes=[
                {
                    "id": "node_1",
                    "title": "Sunday Reflection",
                    "category": "Voice Note",
                    "weight": 4,
                    "color": "#A855F7"
                }
            ],
            edges=[
                {
                    "source": "node_1",
                    "target": "node_2",
                    "relationship": "derived_from"
                }
            ]
        )
    )
