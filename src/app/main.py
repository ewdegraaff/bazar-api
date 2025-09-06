import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import time
from datetime import datetime

import os
import sys

from src.app.api.api_v1.api import api_router
from src.app.core.config import settings
from src.app.core.error_handlers import (
    validation_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler,
)
from src.app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for FastAPI application."""
    logger.info(f"Environment: {os.getenv('ENV', 'not set')}")
    
    # Simple database connectivity check
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            await session.close()
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        # Don't fail startup for database issues in development
        if os.getenv("ENV") == "production":
            raise
    
    yield

def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        lifespan=lifespan,
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )
    
    # Health check endpoint
    @app.get("/healthz")
    async def health_check():
        """Health check endpoint for container orchestration."""
        try:
            # Test database connectivity
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
                await session.close()
            
            return {
                "status": "healthy", 
                "timestamp": datetime.utcnow().isoformat(),
                "service": "bazar-api"
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(
                status_code=503, 
                detail="Service unhealthy"
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
        
        # Mask sensitive headers (Authorization)
        headers_dict = dict(request.headers)
        if 'authorization' in headers_dict:
            auth_header = headers_dict['authorization']
            if auth_header.startswith('Bearer '):
                # Show only first 10 characters of the token
                masked_token = auth_header[:16] + "..." if len(auth_header) > 16 else auth_header
                headers_dict['authorization'] = masked_token
        logger.info(f"Headers: {headers_dict}")
        logger.info(f"Client: {request.client}")
        
        # Log request body for POST requests
        if request.method == "POST":
            try:
                body = await request.body()
                if body:
                    # Try to parse as JSON for better readability
                    try:
                        import json
                        body_json = json.loads(body.decode('utf-8'))
                        logger.info(f"Request body: {body_json}")
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # If not JSON, log as string (truncated if too long)
                        body_str = body.decode('utf-8', errors='replace')
                        if len(body_str) > 1000:
                            body_str = body_str[:1000] + "... (truncated)"
                        logger.info(f"Request body: {body_str}")
                else:
                    logger.info("Request body: (empty)")
            except Exception as e:
                logger.warning(f"Could not read request body: {str(e)}")
        
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
