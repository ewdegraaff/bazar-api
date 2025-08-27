from sqlalchemy import Column, ForeignKey, String, UUID as SQLUUID
from sqlalchemy.orm import relationship

from src.app.models.base import Base


class UserSystemRole(Base):
    """Association table for User-SystemRole many-to-many relationship."""
    __tablename__ = "user_system_roles"
    
    user_id = Column(SQLUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    system_role_id = Column(SQLUUID, ForeignKey("system_roles.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="user_system_roles")
    system_role = relationship("SystemRole", back_populates="user_system_roles") 