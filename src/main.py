"""
########################################################################
# AI Prompt Service - main.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Add Postgres 16, add docker. Endpoint should work ad hoc (AS IS) or with session Mode.
# Version: 1.0.0
# Created: 2025-04-27
# 
# Data Structure Diagram:
# - FastAPI Application with endpoints:
#   - POST /api/prompt: Generate AI responses (ad hoc mode)
#   - POST /api/sessions: Create a new session
#   - GET /api/sessions/{session_id}: Get session details
#   - PUT /api/sessions/{session_id}: Update session
#   - DELETE /api/sessions/{session_id}: Delete session
#   - POST /api/sessions/{session_id}/messages: Add message to session
#   - GET /health: Health check
#
# Dependencies:
# - fastapi
# - logging
# - sqlalchemy.ext.asyncio
# - models module
# - services module
# - config module
# - database module
########################################################################
"""
import logging
import time
import uuid
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Request, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any, Optional, List
import traceback

from src.models import (
    PromptRequest, PromptResponse, AIProvider, 
    SessionCreate, SessionResponse, SessionUpdate,
    MessageCreate, MessageResponse
)
from src.services.claude_service import ClaudeService
from src.services.gemini_service import GeminiService
from src.services.session_service import SessionService
from src.config import settings
from src.database import get_db, async_session_factory

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Set third-party loggers to INFO to reduce noise
logging.getLogger('httpx').setLevel(logging.INFO)
logging.getLogger('httpcore').setLevel(logging.INFO)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize services
session_service = SessionService()

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    logger.info(f"Request {request_id} started: {request.method} {request.url.path}")
    
    # Try to log request body for POST requests
    if request.method == "POST":
        try:
            body = await request.body()
            if body:
                # Clone the request to read the body
                body_str = body.decode()
                logger.debug(f"Request {request_id} body: {body_str}")
                # Create a new body stream
                request._body = body
        except Exception as e:
            logger.warning(f"Could not log request body: {str(e)}")
    
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request {request_id} completed: {response.status_code} in {process_time:.4f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request {request_id} failed after {process_time:.4f}s: {str(e)}")
        raise

# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with a clean response."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": exc.errors()},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with a clean response."""
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"}
    )

# Service factory to get the appropriate AI service
def get_ai_service(ai_provider: AIProvider):
    """Factory function to get the appropriate AI service based on the provider."""
    if ai_provider == AIProvider.CLAUDE:
        return ClaudeService(api_key=settings.anthropic_api_key)
    elif ai_provider == AIProvider.GEMINI:
        return GeminiService(api_key=settings.google_api_key)
    else:
        raise ValueError(f"Unsupported AI provider: {ai_provider}")

# Background task to cleanup old sessions
async def cleanup_old_sessions():
    """Background task to cleanup old sessions periodically."""
    while True:
        try:
            # Create a session using the session factory directly
            db = async_session_factory()
            try:
                await session_service.cleanup_old_sessions(db)
                await db.commit()
            except Exception as e:
                await db.rollback()
                raise
            finally:
                await db.close()
            
            logger.info(f"Successfully cleaned up old sessions (older than {settings.session_expiry_hours} hours)")
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
        
        # Sleep for 1 hour before next cleanup
        await asyncio.sleep(3600)


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    # Start background task for session cleanup
    asyncio.create_task(cleanup_old_sessions())
    logger.info("Started background session cleanup task")


# Ad hoc mode endpoint
@app.post(
    "/api/prompt", 
    response_model=PromptResponse,
    tags=["Ad hoc Mode"],
    summary="Generate response from AI (stateless)",
    description="Send a prompt to an AI model and get a response with conversation history support (stateless).",
    response_description="The AI's response to the prompt.",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Successful response", 
            "model": PromptResponse
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Validation error"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Server error",
            "content": {
                "application/json": {
                    "example": {"detail": "An unexpected error occurred"}
                }
            }
        }
    }
)
async def generate_prompt_response(request: PromptRequest):
    """
    Generate a response from an AI model based on the provided inputs and conversation history.
    This is a stateless endpoint - no conversation state is stored on the server.
    
    - **system_prompt**: The system prompt that provides context and instructions to the AI
    - **human_input**: The current human/user input to respond to
    - **conversation_history**: Previous messages in the conversation (optional)
    - **ai_provider**: The AI provider to use (claude or gemini)
    - **model**: Specific model to use (optional)
    - **parameters**: Additional parameters for the AI request (optional)
    
    Example:
    ```json
    {
      "system_prompt": "You are a helpful AI assistant that specializes in quantum physics.",
      "human_input": "Explain quantum computing in simple terms",
      "conversation_history": [
        {"role": "human", "content": "What is superposition?"},
        {"role": "assistant", "content": "Superposition is a principle in quantum mechanics where particles can exist in multiple states simultaneously until measured."}
      ],
      "ai_provider": "claude",
      "model": "claude-3-sonnet-20240229",
      "parameters": {
        "max_tokens": 500,
        "temperature": 0.7
      }
    }
    ```
    """
    try:
        # Log request details
        logger.info(f"Received prompt request: AI Provider={request.ai_provider}, Model={request.model or 'default'}")
        logger.debug(f"Request details: {request.dict()}")
        
        # Get the appropriate service
        service = get_ai_service(request.ai_provider)
        logger.info(f"Using service: {service.__class__.__name__}")
        
        # Generate response
        logger.info(f"Generating response from {request.ai_provider}...")
        response = await service.generate_response(request)
        
        # Log success
        logger.info(f"Successfully generated response from {request.ai_provider}")
        logger.debug(f"Response details: {response.dict()}")
        
        return response
    except ValueError as e:
        # Handle specific value errors
        logger.error(f"Value error in prompt request: {str(e)}")
        logger.error(f"Request data: AI Provider={request.ai_provider}, Model={request.model or 'default'}")
        logger.debug(f"Full request: {request.dict()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Error generating AI response: {str(e)}")
        logger.error(f"Request data: AI Provider={request.ai_provider}, Model={request.model or 'default'}")
        logger.debug(f"Full request: {request.dict()}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error generating AI response: {str(e)}"
        )


# Session mode endpoints
@app.post(
    "/api/sessions",
    response_model=SessionResponse,
    tags=["Session Mode"],
    summary="Create a new session",
    description="Create a new conversation session with an AI model.",
    status_code=status.HTTP_201_CREATED
)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new conversation session with an AI model.
    
    - **ai_provider**: The AI provider to use (claude or gemini)
    - **model**: Specific model to use (optional)
    - **system_prompt**: The system prompt that provides context and instructions to the AI
    
    Returns a session object with a unique ID that can be used for subsequent requests.
    """
    try:
        # Create new session
        session = await session_service.create_session(db, session_data)
        
        # Convert to response model
        return SessionResponse(
            id=session.id,
            ai_provider=session.ai_provider,
            model=session.model,
            system_prompt=session.system_prompt,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=[]  # No messages yet
        )
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating session: {str(e)}"
        )


@app.get(
    "/api/sessions/{session_id}",
    response_model=SessionResponse,
    tags=["Session Mode"],
    summary="Get session details",
    description="Get details of an existing conversation session including all messages."
)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of an existing conversation session including all messages.
    
    - **session_id**: The ID of the session to retrieve
    """
    # Get session
    session = await session_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    # Get messages
    messages = await session_service.get_messages_for_session(db, session_id)
    
    # Convert to response models
    message_responses = [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at
        )
        for msg in messages
    ]
    
    # Return session response
    return SessionResponse(
        id=session.id,
        ai_provider=session.ai_provider,
        model=session.model,
        system_prompt=session.system_prompt,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=message_responses
    )


@app.put(
    "/api/sessions/{session_id}",
    response_model=SessionResponse,
    tags=["Session Mode"],
    summary="Update session",
    description="Update properties of an existing session."
)
async def update_session(
    session_id: uuid.UUID,
    update_data: SessionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update properties of an existing session.
    
    - **session_id**: The ID of the session to update
    - **system_prompt**: Updated system prompt (optional)
    - **model**: Updated model (optional)
    """
    # Update session
    session = await session_service.update_session(db, session_id, update_data)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    # Get messages
    messages = await session_service.get_messages_for_session(db, session_id)
    
    # Convert to response models
    message_responses = [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at
        )
        for msg in messages
    ]
    
    # Return session response
    return SessionResponse(
        id=session.id,
        ai_provider=session.ai_provider,
        model=session.model,
        system_prompt=session.system_prompt,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=message_responses
    )


@app.delete(
    "/api/sessions/{session_id}",
    tags=["Session Mode"],
    summary="Delete session",
    description="Delete an existing session and all its messages.",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an existing session and all its messages.
    
    - **session_id**: The ID of the session to delete
    """
    # Delete session
    deleted = await session_service.delete_session(db, session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    # Return no content
    return


@app.post(
    "/api/sessions/{session_id}/messages",
    response_model=PromptResponse,
    tags=["Session Mode"],
    summary="Send message in session",
    description="Send a message in an existing session and get an AI response."
)
async def send_message(
    session_id: uuid.UUID,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message in an existing session and get an AI response.
    
    - **session_id**: The ID of the session
    - **content**: The human message content
    - **parameters**: Additional parameters for the AI request (optional)
    """
    try:
        # Get session
        session = await session_service.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
        # Get messages for conversation history
        db_messages = await session_service.get_messages_for_session(db, session_id)
        
        # Convert to conversation history format
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in db_messages
        ]
        
        # Create prompt request
        request = PromptRequest(
            system_prompt=session.system_prompt,
            human_input=message_data.content,
            conversation_history=conversation_history,
            ai_provider=session.ai_provider,
            model=session.model,
            parameters=message_data.parameters
        )
        
        # Get AI service
        service = get_ai_service(AIProvider(session.ai_provider))
        
        # Generate response
        response = await service.generate_response(request)
        
        # Add messages to session
        await session_service.add_message(db, session_id, "human", message_data.content)
        await session_service.add_message(db, session_id, "assistant", response.response)
        
        # Return response
        return response
    except ValueError as e:
        logger.error(f"Value error in message request: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending message: {str(e)}"
        )


@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Simple health check endpoint to verify the API is running.",
    response_description="Health status of the API.",
    status_code=status.HTTP_200_OK
)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint that verifies database connectivity."""
    try:
        # Try a simple database query to verify connectivity
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "disconnected"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "version": settings.app_version,
        "database": db_status
    }


@app.get(
    "/", 
    tags=["System"],
    summary="Root endpoint",
    description="Redirects to API documentation.",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT
)
async def root():
    """Redirect to API documentation."""
    return RedirectResponse(url="/api/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)