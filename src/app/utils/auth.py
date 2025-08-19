"""
Token handling utilities for client-side token management.
"""
import time
from typing import Optional

from src.app.schemas import Token


def is_token_expired(expires_at: int, buffer_seconds: int = 30) -> bool:
    """
    Check if a token is expired with a buffer time.
    
    Args:
        expires_at: Token expiration timestamp
        buffer_seconds: Buffer time in seconds to refresh before actual expiration
        
    Returns:
        True if token is expired or will expire soon, False otherwise
    """
    current_time = int(time.time())
    return current_time >= (expires_at - buffer_seconds)


def should_refresh_token(expires_at: int, refresh_buffer_seconds: int = 300) -> bool:
    """
    Determine if a token should be refreshed based on its expiration time.
    
    Args:
        expires_at: Token expiration timestamp
        refresh_buffer_seconds: Time buffer in seconds to trigger refresh (default: 5 minutes)
        
    Returns:
        True if token should be refreshed, False otherwise
    """
    # If token will expire within the buffer time, it should be refreshed
    current_time = int(time.time())
    return current_time >= (expires_at - refresh_buffer_seconds)


def store_tokens(tokens: Token, storage_dict: dict) -> None:
    """
    Store authentication tokens (for client-side implementation).
    
    Args:
        tokens: Token object containing access and refresh tokens
        storage_dict: Dictionary to store the tokens in
    """
    storage_dict["access_token"] = tokens.access_token
    storage_dict["refresh_token"] = tokens.refresh_token


def get_stored_refresh_token(storage_dict: dict) -> Optional[str]:
    """
    Retrieve stored refresh token (for client-side implementation).
    
    Args:
        storage_dict: Dictionary containing stored tokens
        
    Returns:
        Refresh token if available, None otherwise
    """
    return storage_dict.get("refresh_token")
