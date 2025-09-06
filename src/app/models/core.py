from typing import Optional
from sqlalchemy import Boolean, Column, ForeignKey, String, Integer, Enum as SQLEnum, UUID as SQLUUID, DateTime, text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship, remote

from .base import Base

class User(Base):
    """User model for managing users."""
    __tablename__ = "users"
    
    email = Column(String, nullable=True, unique=True)  # Made nullable for anonymous users
    name = Column(String, nullable=True)
    is_anonymous = Column(Boolean, default=False, nullable=False)
    anonymous_id = Column(String, nullable=True, unique=True)  # For tracking before email confirmation
    converted_from_anonymous_id = Column(String, nullable=True)  # Links to previous anonymous profile
    marked_for_deletion = Column(Boolean, default=False, nullable=False)  # Mark user for deletion
    
    # Relationships
    files = relationship("File", back_populates="owner")
    user_system_roles = relationship("UserSystemRole", back_populates="user")
    system_roles = relationship("SystemRole", secondary="user_system_roles", back_populates="users", viewonly=True)
    user_plans = relationship("UserPlan", back_populates="user")


class File(Base):
    """File model."""
    __tablename__ = "files"
    
    name = Column(String, nullable=False)
    download_url = Column(String, nullable=False)
    owner_id = Column(SQLUUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="files") 