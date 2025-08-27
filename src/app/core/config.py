import logging
import os
from pathlib import Path
from typing import ClassVar, Union

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, ConfigDict, Field, validator
from pydantic_settings import BaseSettings

log_format = logging.Formatter("%(asctime)s : %(levelname)s - %(message)s")

# root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# standard stream handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_format)
root_logger.addHandler(stream_handler)

logger = logging.getLogger(__name__)

# Load .env file from docker/server directory
env_path = Path("./docker/server/.env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Loaded environment from {env_path}")
else:
    logger.error(f"Required .env file not found at {env_path}")
    raise FileNotFoundError(f"Required .env file not found at {env_path}")

# TODO Retrieve secrets from AWS Secrets Manager

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    
    # Supabase Configuration
    SUPABASE_URL: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_URL"),
        description="Supabase project URL"
    )
    SUPABASE_KEY: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_KEY"),
        description="Supabase anon/public key"
    )
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL"),
        description="PostgreSQL database URL"
    )
    
    # Server Configuration
    SERVER_HOST: AnyHttpUrl = "https://localhost"
    SERVER_PORT: int = 8001
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, list[str]]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        elif isinstance(v, str):
            return [v]
        raise ValueError(v)
    
    PROJECT_NAME: str = "bazar-api"

    Config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)


settings = Settings()

# Validate required settings
if not settings.SUPABASE_URL:
    raise ValueError("SUPABASE_URL environment variable is required")
if not settings.SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY environment variable is required")
if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")
