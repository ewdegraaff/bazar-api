import asyncio
import json
import logging
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Tuple
import sys

from src.app.db.session import AsyncSessionLocal
from src.app.models.core import User

logger = logging.getLogger(__name__)

# Define system roles
SYSTEM_ROLES: list[Tuple[str, str]] = [
    ("superadmin", "9d6cc726-0114-4ad0-9e54-e9abaf99f77b"), 
    ("admin", "5bbda456-5e59-4844-9741-579f23ab38fe"), 
    ("user", "cf861d5b-1d6f-4e17-9417-9b689335f220")
]


async def _create_system_roles(db: AsyncSession) -> None:
    """Create system roles if they don't exist.
    
    Args:
        db: Database session
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    for role_name, role_id in SYSTEM_ROLES:
        result = await db.execute(
            text("SELECT 1 FROM system_roles WHERE id = :id"),
            {"id": role_id}
        )
        if not result.scalar():
            # Insert with specified UUID
            await db.execute(
                text("""
                INSERT INTO system_roles (id, name, created_at, updated_at)
                VALUES (:id, :name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """),
                {"id": role_id, "name": role_name}
            )
            logger.info(f"Created system role: {role_name} with id: {role_id}")
        else:
            logger.info(f"System role already exists: {role_name} - skipping")


async def _create_users(db: AsyncSession) -> None:
    """Create users from JSON seed files if they don't exist.
    
    Creates users with the following field values:
    - is_anonymous: false (seed users are regular users)
    - marked_for_deletion: false (seed users are not marked for deletion)
    - anonymous_id: NULL (not applicable for seed users)
    - converted_from_anonymous_id: NULL (not applicable for seed users)
    
    Args:
        db: Database session
        
    Raises:
        SQLAlchemyError: If database operation fails
        ValueError: If user data doesn't match required schema
    """
    users_dir = Path(__file__).parent / "seed" / "users"
    
    if not users_dir.exists():
        logger.info("No users seed directory found - skipping user creation")
        return
    
    # Create a mapping of role names to role IDs for quick lookup
    role_map = {role_name: role_id for role_name, role_id in SYSTEM_ROLES}
    
    # Process all JSON files in the users directory
    for user_file in users_dir.glob("*.json"):
        try:
            with open(user_file, "r") as f:
                user_data = json.load(f)
            
            # The file should contain a single role name as key with user details as value
            if len(user_data) != 1:
                logger.warning(f"Invalid user data format in {user_file}, skipping")
                continue
            
            # Extract role name and user details
            role_name = next(iter(user_data))
            user_details = user_data[role_name]
            
            # Check if role exists
            if role_name not in role_map:
                logger.warning(f"Unknown role '{role_name}' in {user_file}, skipping user creation")
                continue
            
            role_id = role_map[role_name]
            
            # Check if user already exists
            # Note: This works with both old and new schema versions
            result = await db.execute(
                text("SELECT 1 FROM users WHERE email = :email"),
                {"email": user_details["email"]}
            )
            
            if result.scalar():
                logger.info(f"User already exists: {user_details['email']} - skipping")
                continue
            
            # Create user with all required fields
            # Note: Seed users are regular users (not anonymous) and not marked for deletion
            # Optional fields (anonymous_id, converted_from_anonymous_id, deleted_at) default to NULL
            await db.execute(
                text("""
                INSERT INTO users (id, name, email, is_anonymous, marked_for_deletion, created_at, updated_at)
                VALUES (:id, :name, :email, false, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """),
                {
                    "id": user_details["id"],
                    "name": user_details["name"],
                    "email": user_details["email"]
                }
            )
            
            # Assign system role to user
            await db.execute(
                text("""
                INSERT INTO user_system_roles (
                    user_id, system_role_id, created_at, updated_at
                ) VALUES (
                    :user_id, :system_role_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """),
                {
                    "user_id": user_details["id"],
                    "system_role_id": role_id
                }
            )
            
            # Create default Free plan for user
            await db.execute(
                text("""
                INSERT INTO user_plans (
                    user_id, plan_type, is_active, created_at, updated_at
                ) VALUES (
                    :user_id, 'Free', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """),
                {
                    "user_id": user_details["id"]
                }
            )
            
            logger.info(f"Assigned role '{role_name}' and Free plan to user: {user_details['name']}")
            
        except Exception as e:
            logger.error(f"Error processing user file {user_file}: {str(e)}")
            continue


async def _create_files(db: AsyncSession) -> None:
    """Create files from JSON seed files if they don't exist.
    
    Args:
        db: Database session
        
    Raises:
        SQLAlchemyError: If database operation fails
        ValueError: If file data doesn't match required schema
    """
    files_dir = Path(__file__).parent / "seed" / "files"
    
    if not files_dir.exists():
        logger.info("No files seed directory found - skipping file creation")
        return
    
    # Process all JSON files in the files directory
    for file_path in files_dir.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                file_data = json.load(f)
            
            # Check if file already exists
            result = await db.execute(
                text("SELECT 1 FROM files WHERE id = :id"),
                {"id": file_data["id"]}
            )
            
            if result.scalar():
                logger.info(f"File already exists: {file_data['name']} - skipping")
                continue
            
            # Create file
            await db.execute(
                text("""
                INSERT INTO files (id, name, download_url, owner_id, created_at, updated_at)
                VALUES (:id, :name, :download_url, :owner_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """),
                {
                    "id": file_data["id"],
                    "name": file_data["name"],
                    "download_url": file_data["download_url"],
                    "owner_id": file_data.get("owner_id")
                }
            )
            
            logger.info(f"Created file: {file_data['name']}")
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            continue


async def init_db() -> None:
    """Initialize the database with seed data."""
    async with AsyncSessionLocal() as db:
        try:
            # Create system roles
            await _create_system_roles(db)
            
            # Create users
            await _create_users(db)
            
            # Create files
            await _create_files(db)
            
            # Commit all changes
            await db.commit()
            
            logger.info("Database initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            await db.rollback()
            raise


def main() -> None:
    """Main function to run database initialization."""
    try:
        asyncio.run(init_db())
        print("✅ Database initialization completed successfully!")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 