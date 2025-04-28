"""
########################################################################
# AI Prompt Service - models.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Add Postgres 16, add docker. Endpoint should work ad hoc (AS IS) or with session Mode.
# Version: 1.0.0
# Created: 2025-04-27
# 
# Data Structure Diagram:
# - AIProvider (Enum): CLAUDE, GEMINI
# - Message: role, content
# - PromptRequest: prompt, ai_provider, model, parameters
# - PromptResponse: response, ai_provider, model, usage, metadata
# - SessionCreate: ai_provider, model, system_prompt
# - SessionResponse: id, ai_provider, model, system_prompt, created_at, updated_at
# - MessageCreate: role, content
#
# Dependencies:
# - pydantic
# - enum
# - typing
# - uuid
# - datetime
########################################################################
"""
from enum import Enum
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, validator


class AIProvider(str, Enum):
    """Enum representing supported AI providers."""
    CLAUDE = "claude"
    GEMINI = "gemini"


class Message(BaseModel):
    """Model for a single message in a conversation."""
    role: str = Field(..., description="The role of the message sender (e.g., 'human', 'assistant')")
    content: str = Field(..., description="The content of the message")


class PromptRequest(BaseModel):
    """Model for prompt request data validation."""
    system_prompt: str = Field(..., description="The system prompt that provides context and instructions to the AI")
    human_input: str = Field(..., description="The current human/user input to respond to")
    conversation_history: Optional[List[Message]] = Field(default_factory=list, description="Previous messages in the conversation (optional)")
    ai_provider: AIProvider = Field(..., description="The AI provider to use")
    model: Optional[str] = Field(None, description="Specific model to use (if applicable)")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters for the AI request")
    
    class Config:
        """Configuration for the PromptRequest model."""
        json_encoders = {
            # Custom encoders if needed
        }
        extra = "ignore"  # Allow extra fields to be ignored instead of raising an error


class PromptResponse(BaseModel):
    """Model for prompt response data validation."""
    response: str = Field(..., description="The AI's response to the prompt")
    ai_provider: AIProvider = Field(..., description="The AI provider that was used")
    model: str = Field(..., description="The specific model that was used")
    usage: Optional[Dict[str, Any]] = Field(None, description="Usage information (tokens, etc.)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata from the AI response")


# Session-related models
class SessionCreate(BaseModel):
    """Model for creating a new session."""
    ai_provider: AIProvider = Field(..., description="The AI provider to use for this session")
    model: Optional[str] = Field(None, description="Specific model to use (if applicable)")
    system_prompt: str = Field(..., description="The system prompt that provides context and instructions to the AI")


class SessionUpdate(BaseModel):
    """Model for updating a session."""
    system_prompt: Optional[str] = Field(None, description="The updated system prompt")
    model: Optional[str] = Field(None, description="Updated model to use")


class MessageCreate(BaseModel):
    """Model for creating a new message in a session."""
    content: str = Field(..., description="The content of the message")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters for the AI request")


class MessageResponse(BaseModel):
    """Model for a message response."""
    id: UUID = Field(..., description="Unique identifier for the message")
    role: str = Field(..., description="The role of the message sender")
    content: str = Field(..., description="The content of the message")
    created_at: datetime = Field(..., description="When the message was created")


class SessionResponse(BaseModel):
    """Model for session response."""
    id: UUID = Field(..., description="Unique identifier for the session")
    ai_provider: AIProvider = Field(..., description="The AI provider used for this session")
    model: str = Field(..., description="The specific model used for this session")
    system_prompt: str = Field(..., description="The system prompt for this session")
    created_at: datetime = Field(..., description="When the session was created")
    updated_at: datetime = Field(..., description="When the session was last updated")
    messages: List[MessageResponse] = Field(default_factory=list, description="Messages in this session")
    
    class Config:
        """Configuration for the SessionResponse model."""
        from_attributes = True