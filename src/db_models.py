"""
########################################################################
# AI Prompt Service - db_models.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Add Postgres 16, add docker. Endpoint should work ad hoc (AS IS) or with session Mode.
# Version: 1.0.0
# Created: 2025-04-27
# 
# UML Representation:
# +-------------------------+     +-------------------------+
# |         Session         |     |         Message         |
# +-------------------------+     +-------------------------+
# | id: UUID               |<>---| id: UUID                |
# | ai_provider: String    |     | session_id: UUID        |
# | model: String          |     | role: String            |
# | system_prompt: String  |     | content: Text           |
# | created_at: DateTime   |     | created_at: DateTime    |
# | updated_at: DateTime   |     | order: Integer          |
# +-------------------------+     +-------------------------+
#
# Dependencies:
# - sqlalchemy
# - uuid
# - datetime
# - database
########################################################################
"""
import uuid
from datetime import datetime
from typing import List

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database import Base


class Session(Base):
    """Database model for a conversation session."""
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    system_prompt = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship to messages
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.order")
    
    def __repr__(self):
        return f"<Session(id={self.id}, ai_provider={self.ai_provider}, model={self.model})>"


class Message(Base):
    """Database model for a message in a conversation."""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)  # 'human' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    order = Column(Integer, nullable=False)  # To maintain message order
    
    # Relationship to session
    session = relationship("Session", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, session_id={self.session_id})>"