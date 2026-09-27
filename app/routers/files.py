from fastapi import APIRouter
from app.dependencies import CurrentUserDep, DbDep
from app.models.schemas.files import FilesHierarchyResponse
from app.models.schemas.common import ApiResponse

router = APIRouter(prefix="/files", tags=["files"])


@router.get("", response_model=ApiResponse[FilesHierarchyResponse])
async def get_files(
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[FilesHierarchyResponse]:
    # Mocking implementation for frontend integration
    return ApiResponse(
        data=FilesHierarchyResponse(
            folders=[
                {"id": "fld_01", "name": "Work Projects", "item_count": 14}
            ],
            files=[
                {"id": "fil_101", "name": "Architecture_Spec.pdf", "size_bytes": 2048000}
            ]
        )
    )
