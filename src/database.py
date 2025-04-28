"""
########################################################################
# AI Prompt Service - database.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Add Postgres 16, add docker. Endpoint should work ad hoc (AS IS) or with session Mode.
# Version: 1.0.0
# Created: 2025-04-27
# 
# Data Structure Diagram:
# - Database connection setup
# - Database session management
#
# Dependencies:
# - sqlalchemy
# - asyncpg
# - config
########################################################################
"""
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from src.config import settings

# Create async engine for PostgreSQL
DATABASE_URL = settings.database_url
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.db_echo,
    future=True,
    poolclass=NullPool if settings.testing else None,
)

# Create session factory
async_session_factory = async_sessionmaker(
    engine, 
    expire_on_commit=False, 
    class_=AsyncSession
)

# Create declarative base for models
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session for dependency injection.
    
    Usage:
    ```
    @app.get("/items/")
    async def get_items(db: AsyncSession = Depends(get_db)):
        # Use db session here
    ```
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise