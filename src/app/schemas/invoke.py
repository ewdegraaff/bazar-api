from typing import Optional
from pydantic import BaseModel, ConfigDict

from .base import BaseSchema


class InvokeRequest(BaseSchema):
    """Schema for invoke request."""
    model: str
    input: str


class InvokeResponse(BaseSchema):
    """Schema for invoke response."""
    output: str
    model: str
    status: str = "success"
    
    model_config = ConfigDict(from_attributes=True) 