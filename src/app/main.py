import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
import time

import os
import sys

from src.app.api.api_v1.api import api_router
from src.app.core.config import settings
from src.app.core.error_handlers import (
    validation_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler,
)
from src.app.db.init_db import init_db
from src.app.db.init_auth import main as init_auth
from src.app.db.session import SessionLocal, AsyncSessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for FastAPI application."""
    logger.info(f"Environment: {os.getenv('ENV', 'not set')}")
    logger.info(f"INIT_DB_ON_STARTUP: {os.getenv('INIT_DB_ON_STARTUP', 'not set')}")
    logger.info(f"INIT_AUTH_ON_STARTUP: {os.getenv('INIT_AUTH_ON_STARTUP', 'not set')}")

    # Initialize database if enabled
    if settings.INIT_DB_ON_STARTUP:
        try:
            await init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    else:
        logger.info("Database initialization skipped (INIT_DB_ON_STARTUP=false)")
    
    # Initialize Supabase authentication if enabled
    if settings.INIT_AUTH_ON_STARTUP:
        try:
            logger.info("Initializing Supabase authentication...")
            init_auth()
            logger.info("Supabase authentication initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase authentication: {e}")
            # Don't raise here as auth is not critical for app startup
            logger.warning("Continuing app startup despite auth initialization failure")
    else:
        logger.info("Supabase authentication initialization skipped (INIT_AUTH_ON_STARTUP=false)")
    
    yield

def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        lifespan=lifespan,
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        # generate_unique_id_function=lambda router: f"{router.tags[0]}-{router.name}",
    )
    
    # Add debug middleware to log all incoming requests
    @app.middleware("http")
    async def debug_request_middleware(request: Request, call_next):
        start_time = time.time()
        
        # Log incoming request details
        logger.info(f"=== INCOMING REQUEST DEBUG ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"URL: {request.url}")
        logger.info(f"Path: {request.url.path}")
        logger.info(f"Query params: {dict(request.query_params)}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Client: {request.client}")
        
        # Process the request
        response = await call_next(request)
        
        # Log response details
        process_time = time.time() - start_time
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Process time: {process_time:.4f}s")
        logger.info(f"=== END REQUEST DEBUG ===")
        
        return response
    
    # Add exception handlers
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # Set CORS - be more permissive for local development
    logger.info("CORS Origins from settings: %s", settings.BACKEND_CORS_ORIGINS)
    
    # For local development, allow all origins
    environment = os.getenv("ENV", "development")
    
    if environment == "development":
        logger.info("Development mode: Allowing all CORS origins")
        cors_origins = ["*"]  # Allow all origins in development
    else:
        # For production, use configured origins only
        cors_origins = settings.BACKEND_CORS_ORIGINS.copy()
        
        # Add common localhost development ports as fallback
        dev_origins = [
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://localhost:5173",  # Vite default
            "http://localhost:8080",  # Common dev server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8080",
        ]
        
        # Add dev origins if not already present
        for origin in dev_origins:
            if origin not in cors_origins:
                cors_origins.append(origin)
    
    logger.info("Final CORS Origins: %s", cors_origins)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600,  # Cache preflight requests for 10 minutes
    )
        
    # Include the routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = create_app()

if __name__ == "__main__":
    host = "localhost"
    port = settings.SERVER_PORT
    uvicorn.run(app, host=host, port=port)
