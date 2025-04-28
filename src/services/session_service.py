"""
########################################################################
# AI Prompt Service - services/session_service.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Add Postgres 16, add docker. Endpoint should work ad hoc (AS IS) or with session Mode.
# Version: 1.0.0
# Created: 2025-04-27
# 
# UML Representation:
# +-------------------------+
# |     SessionService      |
# +-------------------------+
# | +create_session()       |
# | +get_session()          |
# | +update_session()       |
# | +add_message()          |
# | +delete_session()       |
# | +cleanup_old_sessions() |
# +-------------------------+
#
# Dependencies:
# - uuid
# - datetime
# - sqlalchemy
# - models
# - db_models
# - config
########################################################################
"""
import logging
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models import Message as MessageModel, AIProvider, SessionCreate, SessionUpdate
from src.db_models import Session, Message
from src.config import settings

logger = logging.getLogger(__name__)

class SessionService:
    """Service for managing conversation sessions."""
    
    async def create_session(
        self, 
        db: AsyncSession,
        session_data: SessionCreate
    ) -> Session:
        """
        Create a new conversation session.
        
        Args:
            db: Database session
            session_data: Session creation data
            
        Returns:
            The created session object
        """
        # Use default model if not provided
        model = session_data.model
        if not model:
            model = (
                settings.default_claude_model 
                if session_data.ai_provider == AIProvider.CLAUDE 
                else settings.default_gemini_model
            )
            
        # Create new session
        session = Session(
            ai_provider=session_data.ai_provider,
            model=model,
            system_prompt=session_data.system_prompt
        )
        
        db.add(session)
        await db.flush()
        
        logger.info(f"Created new session: {session.id} with provider {session_data.ai_provider}")
        return session
    
    async def get_session(
        self, 
        db: AsyncSession,
        session_id: UUID
    ) -> Optional[Session]:
        """
        Get a session by ID.
        
        Args:
            db: Database session
            session_id: The ID of the session to retrieve
            
        Returns:
            The session object or None if not found
        """
        result = await db.execute(
            select(Session)
            .where(Session.id == session_id)
        )
        session = result.scalars().first()
        
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return None
            
        return session
    
    async def update_session(
        self,
        db: AsyncSession,
        session_id: UUID,
        update_data: SessionUpdate
    ) -> Optional[Session]:
        """
        Update a session.
        
        Args:
            db: Database session
            session_id: The ID of the session to update
            update_data: The data to update
            
        Returns:
            The updated session or None if not found
        """
        session = await self.get_session(db, session_id)
        if not session:
            return None
            
        # Update fields if provided
        if update_data.system_prompt is not None:
            session.system_prompt = update_data.system_prompt
            
        if update_data.model is not None:
            session.model = update_data.model
            
        session.updated_at = datetime.utcnow()
        await db.flush()
        
        logger.info(f"Updated session: {session_id}")
        return session
    
    async def add_message(
        self,
        db: AsyncSession,
        session_id: UUID,
        role: str,
        content: str
    ) -> Optional[Tuple[Session, Message]]:
        """
        Add a message to a session.
        
        Args:
            db: Database session
            session_id: The ID of the session
            role: The role of the message sender (human or assistant)
            content: The content of the message
            
        Returns:
            Tuple of (session, message) or None if session not found
        """
        session = await self.get_session(db, session_id)
        if not session:
            return None
            
        # Get the next order number
        result = await db.execute(
            select(func.coalesce(func.max(Message.order), -1) + 1)
            .where(Message.session_id == session_id)
        )
        next_order = result.scalar()
        
        # Create the message
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            order=next_order
        )
        
        db.add(message)
        
        # Update session timestamp
        session.updated_at = datetime.utcnow()
        await db.flush()
        
        logger.info(f"Added {role} message to session {session_id}")
        return (session, message)
    
    async def delete_session(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> bool:
        """
        Delete a session.
        
        Args:
            db: Database session
            session_id: The ID of the session to delete
            
        Returns:
            True if deleted, False if not found
        """
        result = await db.execute(
            delete(Session)
            .where(Session.id == session_id)
            .returning(Session.id)
        )
        deleted_id = result.scalar()
        
        if not deleted_id:
            logger.warning(f"Session not found for deletion: {session_id}")
            return False
            
        logger.info(f"Deleted session: {session_id}")
        return True
    
    async def cleanup_old_sessions(
        self,
        db: AsyncSession,
        hours: int = settings.session_expiry_hours
    ) -> int:
        """
        Delete sessions older than the specified timeframe.
        
        Args:
            db: Database session
            hours: Hours of inactivity after which sessions are deleted
            
        Returns:
            Number of sessions deleted
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        result = await db.execute(
            delete(Session)
            .where(Session.updated_at < cutoff)
            .returning(Session.id)
        )
        deleted_ids = result.scalars().all()
        
        count = len(deleted_ids)
        if count > 0:
            logger.info(f"Cleaned up {count} old sessions")
            
        return count
    
    async def get_messages_for_session(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> List[Message]:
        """
        Get all messages for a session.
        
        Args:
            db: Database session
            session_id: The ID of the session
            
        Returns:
            List of messages ordered by order field
        """
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.order)
        )
        
        return result.scalars().all()