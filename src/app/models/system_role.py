from sqlalchemy import Column, String, UUID as SQLUUID, text
from sqlalchemy.orm import relationship

from src.app.models.base import Base


class SystemRole(Base):
    """SystemRole model for system-level administration permissions (superadmin, admin, user)."""
    __tablename__ = "system_roles"
    
    name = Column(String, nullable=False, unique=True)
    
    # Relationships
    user_system_roles = relationship("UserSystemRole", back_populates="system_role")
    users = relationship("User", secondary="user_system_roles", back_populates="system_roles", viewonly=True) 