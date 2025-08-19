from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from pydantic import BaseModel
from uuid import UUID

from src.app.schemas.base import CreateBase, UpdateBase, ResponseBase
from src.app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=ResponseBase)
CreateSchemaType = TypeVar("CreateSchemaType", bound=CreateBase)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=UpdateBase)
SQLModelType = TypeVar("SQLModelType", bound=Base)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType, SQLModelType]):
    def __init__(self, model: Type[ModelType], sql_model: Type[SQLModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        **Parameters**
        * `model`: A Pydantic model class
        * `sql_model`: A SQLAlchemy model class
        """
        self.model = model
        self.sql_model = sql_model

    def _serialize_uuid(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize UUID fields to strings."""
        for key, value in data.items():
            if isinstance(value, UUID):
                data[key] = str(value)
            elif isinstance(value, dict):
                data[key] = self._serialize_uuid(value)
            elif isinstance(value, list):
                data[key] = [self._serialize_uuid(item) if isinstance(item, dict) else str(item) if isinstance(item, UUID) else item for item in value]
        return data

    async def exists(self, db: AsyncSession, *, id: str) -> bool:
        """Check if an object exists."""
        stmt = select(self.sql_model).where(self.sql_model.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count(self, db: AsyncSession) -> int:
        """Count all objects."""
        stmt = select(func.count()).select_from(self.sql_model)
        result = await db.execute(stmt)
        return result.scalar_one()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, with_relationships: bool = False
    ) -> list[ModelType]:
        """Get multiple objects.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            with_relationships: Whether to load relationships (implementation varies by subclass)
            
        Returns:
            list[ModelType]: List of model objects
        """
        stmt = select(self.sql_model).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get(self, db: AsyncSession, *, id: str) -> ModelType | None:
        """Get a single object by ID."""
        stmt = select(self.sql_model).where(self.sql_model.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[SQLModelType]:
        """Get all objects."""
        stmt = select(self.sql_model).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_key(self, db: AsyncSession, *, key_field: str, key_value: str) -> Optional[SQLModelType]:
        """Get by key field and value"""
        stmt = select(self.sql_model).where(getattr(self.sql_model, key_field) == key_value)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new object."""
        obj_in_data = obj_in.model_dump()
        db_obj = self.sql_model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: SQLModelType, obj_in: UpdateSchemaType
    ) -> SQLModelType:
        """Update an object."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field in update_data:
            setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: str) -> SQLModelType | None:
        """Remove an object."""
        obj = await self.get(db, id=id)
        if not obj:
            return None
        await db.delete(obj)
        await db.commit()
        return obj

    async def delete(self, db: AsyncSession, *, id: str) -> SQLModelType:
        """Delete object"""
        stmt = delete(self.sql_model).where(self.sql_model.id == id).returning(self.sql_model)
        result = await db.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="Object not found")
        await db.commit()
        return obj

    