from typing import List, Optional
from uuid import UUID
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.utils.storage import get_bucket_name
from src.app.core.config import settings
from src.app.db.session import SessionDep
from src.app.crud.base import CRUDBase
from src.app.schemas.file import File, FileCreate, FileUpdate
from src.app.models.core import File as FileModel
from src.app.utils.storage import delete_from_s3

# Configure logging
logger = logging.getLogger(__name__)


class CRUDFile(CRUDBase[File, FileCreate, FileUpdate, FileModel]):
    """CRUD operations for file management."""
    
    async def get_by_owner(
        self, db: AsyncSession, *, owner_id: str
    ) -> list[FileModel]:
        """Get all files for an owner."""
        stmt = select(FileModel).where(FileModel.owner_id == owner_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def delete_file_from_storage(self, db: AsyncSession, *, file_id: UUID) -> None:
        """Delete file from storage (S3 or LocalStack)."""
        file = await self.get(db, id=file_id)
        if not file:
            return
        
        # Extract key from S3 URL
        key = file.download_url.split("/", 3)[-1]
        await delete_from_s3(key)


file = CRUDFile(File, FileModel)
