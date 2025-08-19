from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict, validator
from uuid import UUID, uuid4
from datetime import datetime

# request


# Shared properties
# class CRUDBaseModel(BaseModel):
#     # where the data
#     table_name: str


# Properties to receive on object creation
# in
class CreateBase(BaseModel):
    """Base class for create schemas."""
    model_config = ConfigDict(from_attributes=True)
    id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('id', pre=True)
    def convert_id_to_uuid(cls, v):
        if isinstance(v, str):
            return UUID(v)
        return v

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = uuid4()
        now = datetime.utcnow()
        if not self.created_at:
            self.created_at = now
        elif self.created_at and self.created_at.tzinfo:
            # If created_at has timezone info, convert to naive datetime
            self.created_at = self.created_at.replace(tzinfo=None)
        if not self.updated_at:
            self.updated_at = now
        elif self.updated_at and self.updated_at.tzinfo:
            # If updated_at has timezone info, convert to naive datetime
            self.updated_at = self.updated_at.replace(tzinfo=None)

    def model_dump(self, **kwargs):
        """Override model_dump to handle UUID serialization."""
        data = super().model_dump(**kwargs)
        # Convert UUID to string if present
        if isinstance(data.get('id'), UUID):
            data['id'] = str(data['id'])
        return data


# Properties to receive on object update
# in


class UpdateBase(BaseModel):
    """Base class for update schemas."""
    id: str
    model_config = ConfigDict(from_attributes=True)
    updated_at: Optional[datetime] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.updated_at:
            self.updated_at = datetime.utcnow()
        elif self.updated_at and self.updated_at.tzinfo:
            # If updated_at has timezone info, convert to naive datetime
            self.updated_at = self.updated_at.replace(tzinfo=None)

# response


# Properties shared by models stored in DB
class InDBBase(BaseModel):
    id: UUID
    updated_at: str
    created_at: str


# Properties to return to client
# curd model
# out
class ResponseBase(BaseModel):
    """Base class for response schemas."""
    id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

    def model_dump(self, **kwargs):
        """Override model_dump to handle UUID serialization."""
        data = super().model_dump(**kwargs)
        # Convert UUID to string if present
        if isinstance(data.get('id'), UUID):
            data['id'] = str(data['id'])
        return data


class BaseSchema(BaseModel):
    """Base schema with common fields."""
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class IDSchema(BaseSchema):
    """Schema with ID field."""
    id: UUID


class BaseResponseSchema(TimestampSchema, IDSchema):
    """Base response schema with ID and timestamp fields."""
    pass
