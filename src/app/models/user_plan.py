from sqlalchemy import Column, String, UUID as SQLUUID, DateTime, text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from src.app.models.base import Base


class UserPlan(Base):
    """UserPlan model for subscription-based feature access (Free, Plus, Premium)."""
    __tablename__ = "user_plans"
    
    id = Column(SQLUUID, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id = Column(SQLUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_type = Column(String, nullable=False)  # "Free", "Plus", "Premium"
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="user_plans") 