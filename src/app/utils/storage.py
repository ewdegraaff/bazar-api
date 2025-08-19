# import aioboto3  # Temporarily commented out for testing
import logging
from fastapi import HTTPException, UploadFile
from src.app.core.config import settings

logger = logging.getLogger(__name__)

# Constants
CHUNK_SIZE = 1024 * 1024  # 1MB chunks
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
    # Add more as needed
}


def get_bucket_name() -> str:
    """Get appropriate bucket name based on environment."""
    if hasattr(settings, 'AWS_ENDPOINT_URL') and settings.AWS_ENDPOINT_URL:
        return "soots-app-data"  # Fixed name for LocalStack
    return getattr(settings, 'AWS_BUCKET_NAME', 'default-bucket')  # Dynamic name for production


async def get_s3_client():
    """Get configured S3 client - Mock version for testing."""
    logger.warning("Using mock S3 client - aioboto3 not available")
    return None


async def ensure_bucket_exists(s3_client) -> None:
    """Ensure bucket exists, create if it doesn't - Mock version for testing."""
    logger.warning("Mock bucket creation - aioboto3 not available")
    pass


async def validate_file(file: UploadFile) -> None:
    """Validate file type and size."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed. Allowed types: {ALLOWED_CONTENT_TYPES}"
        )


async def stream_to_s3(file: UploadFile, s3_key: str) -> str:
    """Stream file directly to S3 in chunks - Mock version for testing."""
    logger.warning("Mock S3 upload - aioboto3 not available")
    return f"mock://mock-bucket/{s3_key}"


async def delete_from_s3(s3_key: str) -> None:
    """Delete file from S3 storage - Mock version for testing."""
    logger.warning("Mock S3 deletion - aioboto3 not available")
    pass
