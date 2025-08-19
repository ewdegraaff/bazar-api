from typing import ClassVar, Optional, List, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from src.app.schemas.base import CreateBase, BaseResponseSchema, BaseSchema

class FileBase(BaseModel):
    """Base file schema."""
    name: str
    download_url: str
    workflow_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None


class FileCreate(FileBase):
    """Schema for creating a file."""
    pass


class FileUpdate(BaseModel):
    """Schema for updating a file."""
    name: Optional[str] = None
    download_url: Optional[str] = None
    owner_id: Optional[UUID] = None


class FileResponse(FileBase, BaseResponseSchema):
    """Schema for file response."""
    model_config = ConfigDict(from_attributes=True)


class FileWithRelationshipsResponse(BaseModel):
    """Contracted file for workflow."""
    id: UUID
    name: str
    download_url: str


class File(FileBase):
    """Schema for file in database."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    table_name: ClassVar[str] = "files"


class FileVerification(BaseSchema):
    """Schema for file verification in updates."""
    id: UUID
    name: str
    download_url: str 