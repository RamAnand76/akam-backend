from pydantic import BaseModel

class FolderResponse(BaseModel):
    id: str
    name: str
    item_count: int

class FileResponse(BaseModel):
    id: str
    name: str
    size_bytes: int

class FilesHierarchyResponse(BaseModel):
    folders: list[FolderResponse]
    files: list[FileResponse]
