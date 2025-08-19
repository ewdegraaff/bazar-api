from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Annotated, Optional
from uuid import UUID
import logging

from src.app.api.auth_deps import CurrentUser
from src.app.db.session import SessionDep
from src.app.core.pbac import require_permission
from src.app.schemas.file import FileCreate, FileUpdate, FileResponse
from src.app.crud.crud_files import file as crud_file
from src.app.utils.storage import validate_file, stream_to_s3

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=FileResponse)
async def create_file(
    current_user: Annotated[CurrentUser, Depends(require_permission("create", "files"))],
    db: SessionDep,
    file: UploadFile = File(...),
) -> FileResponse:
    """Create new file with streaming upload."""
    try:
        await validate_file(file)
        
        # Generate S3 key for user files
        s3_key = f"files/{current_user.id}/{file.filename}"
            
        download_url = await stream_to_s3(file, s3_key)
        
        file_in = FileCreate(
            name=file.filename,
            download_url=download_url,
            owner_id=current_user.id
        )
        
        return await crud_file.create(db, obj_in=file_in)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while processing file"
        )


@router.get("/{file_id}", response_model=FileResponse)
async def read_file(
    file_id: UUID,
    db: SessionDep,
    current_user: Annotated[CurrentUser, Depends(require_permission("read", "files"))]
) -> FileResponse:
    """Get file by ID."""
    file = await crud_file.get(db, id=file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file


@router.put("/{file_id}", response_model=FileResponse)
async def update_file(
    file_id: UUID,
    file_in: FileUpdate,
    db: SessionDep,
    current_user: Annotated[CurrentUser, Depends(require_permission("update", "files"))]
) -> FileResponse:
    """Update file."""
    file = await crud_file.get(db, id=file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return await crud_file.update(db, obj_in=file_in)


@router.delete("/{file_id}", response_model=FileResponse)
async def delete_file(
    file_id: UUID,
    db: SessionDep,
    current_user: Annotated[CurrentUser, Depends(require_permission("delete", "files"))]
) -> FileResponse:
    """Delete file."""
    file = await crud_file.get(db, id=file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return await crud_file.delete(db, id=file_id)
