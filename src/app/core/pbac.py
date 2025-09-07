import logging
from typing import Callable, Dict, List, Optional, Annotated
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from yaml import safe_load

from src.app.api.auth_deps import get_current_user
from src.app.schemas import User
from src.app.models.core import User as UserModel
from src.app.db.session import SessionDep

logger = logging.getLogger(__name__)

# Load policies from YAML file
def load_policies() -> Dict:
    try:
        import os
        # Try multiple possible paths for policies.yaml
        possible_paths = [
            "policies.yaml",  # Current directory
            "/app/policies.yaml",  # Docker app directory
            os.path.join(os.path.dirname(__file__), "../../../policies.yaml"),  # Relative to this file
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Loading policies from: {path}")
                with open(path, "r") as f:
                    return safe_load(f)
        
        logger.error(f"policies.yaml not found in any of these paths: {possible_paths}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load policies: {e}")
        return {}


class Policy(BaseModel):
    roles: List[str]
    actions: List[str]
    resources: List[str]


async def check_policy(user: User, action: str, resource: str, db: SessionDep) -> bool:
    """Check if user has permission to perform action on resource."""
    policies = load_policies()
    
    logger.info(f"Checking policy for user {user.id}, action: {action}, resource: {resource}")
    
    # Load user with system roles
    stmt = select(UserModel).options(selectinload(UserModel.system_roles)).where(UserModel.id == user.id)
    result = await db.execute(stmt)
    user_with_roles = result.scalar_one_or_none()
    
    if not user_with_roles:
        logger.warning(f"User {user.id} not found in database")
        return False
    
    # Get user system roles
    user_system_roles = [role.name for role in user_with_roles.system_roles]
    logger.info(f"User {user.id} has roles: {user_system_roles}")
    
    # Check each policy
    for policy in policies.get("policies", []):
        policy_obj = Policy(**policy)
        logger.info(f"Checking policy: roles={policy_obj.roles}, actions={policy_obj.actions}, resources={policy_obj.resources}")
        
        # Check if user has required role
        if not any(role in user_system_roles for role in policy_obj.roles):
            logger.info(f"User {user.id} does not have required role from {policy_obj.roles}")
            continue
            
        # Check if action is allowed
        if action not in policy_obj.actions:
            logger.info(f"Action {action} not allowed in policy actions {policy_obj.actions}")
            continue
            
        # Check if resource is allowed (including wildcard "*")
        if "*" not in policy_obj.resources and resource not in policy_obj.resources:
            logger.info(f"Resource {resource} not allowed in policy resources {policy_obj.resources}")
            continue
            
        logger.info(f"Policy check passed for user {user.id}")
        return True
    
    logger.warning(f"No matching policy found for user {user.id}, action: {action}, resource: {resource}")
    return False


def require_permission(action: str, resource: str):
    """Decorator to require specific permission for an endpoint."""
    async def permission_dependency(
        request: Request,
        current_user: Annotated[User, Depends(get_current_user)],
        db: SessionDep
    ) -> User:
        if not await check_policy(current_user, action, resource, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        return current_user
    
    return permission_dependency 