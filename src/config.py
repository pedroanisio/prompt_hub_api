"""
########################################################################
# AI Prompt Service - config.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Add Postgres 16, add docker. Endpoint should work ad hoc (AS IS) or with session Mode.
# Version: 1.0.0
# Created: 2025-04-27
# 
# Data Structure Diagram:
# - Settings: app_name, app_version, app_description, API keys, default models, database settings
#
# Dependencies:
# - os
# - pydantic_settings
########################################################################
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API configuration
    app_name: str = "AI Prompt Service"
    app_version: str = "1.0.0"
    app_description: str = "FastAPI service for interacting with AI models like Claude and Gemini"
    
    # API Keys
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    google_api_key: str = os.environ.get("GOOGLE_API_KEY", "")
    
    # Default models
    default_claude_model: str = "claude-3-sonnet-20240229"
    default_gemini_model: str = "gemini-pro"
    
    # PostgreSQL settings
    postgres_user: str = os.environ.get("POSTGRES_USER", "postgres")
    postgres_password: str = os.environ.get("POSTGRES_PASSWORD", "postgres")
    postgres_db: str = os.environ.get("POSTGRES_DB", "prompt_service")
    postgres_host: str = os.environ.get("POSTGRES_HOST", "localhost")
    postgres_port: str = os.environ.get("POSTGRES_PORT", "5432")
    
    # Database settings
    database_url: str = os.environ.get(
        "DATABASE_URL", 
        f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    )
    db_echo: bool = os.environ.get("DB_ECHO", "false").lower() == "true"
    
    # Session settings
    session_expiry_hours: int = int(os.environ.get("SESSION_EXPIRY_HOURS", "24"))
    
    # Testing flag
    testing: bool = os.environ.get("TESTING", "false").lower() == "true"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow extra fields from environment


# Create global settings instance
settings = Settings()