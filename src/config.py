"""
########################################################################
# AI Prompt Service - config.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Build a FastAPI that will use Claude and Gemini, with endpoints for prompts
# Version: 1.0.0
# Created: 2025-04-27
# 
# Data Structure Diagram:
# - Settings: app_name, app_version, app_description, API keys, default models
#
# Dependencies:
# - os
# - pydantic
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
    anthropic_api_key: str
    google_api_key: str = os.environ.get("GOOGLE_API_KEY", "")
    
    # Default models
    default_claude_model: str = "claude-3-sonnet-20240229"
    default_gemini_model: str = "gemini-pro"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create global settings instance
settings = Settings()