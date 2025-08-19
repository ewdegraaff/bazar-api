"""
life span events
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.app.api.auth_deps import get_supabase_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """life span events"""
    try:
        await get_supabase_client()
        yield
    finally:
        logging.info("lifespan shutdown")
