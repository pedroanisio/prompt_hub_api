"""
########################################################################
# AI Prompt Service - main.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Build a FastAPI that will use Claude and Gemini, with endpoints for prompts
# Version: 1.0.0
# Created: 2025-04-27
# 
# Data Structure Diagram:
# - FastAPI Application with endpoints:
#   - POST /api/prompt: Generate AI responses
#   - GET /health: Health check
#
# Dependencies:
# - fastapi
# - logging
# - models module
# - services module
# - config module
########################################################################
"""
import logging
import time
import uuid
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Dict, Any, Optional
import traceback

from src.models import PromptRequest, PromptResponse, AIProvider
from src.services.claude_service import ClaudeService
from src.services.gemini_service import GeminiService
from src.config import settings

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


@app.post(
    "/api/prompt", 
    response_model=PromptResponse,
    tags=["AI"],
    summary="Generate response from AI",
    description="Send a prompt to an AI model and get a response with conversation history support.",
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


@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Simple health check endpoint to verify the API is running.",
    response_description="Health status of the API.",
    status_code=status.HTTP_200_OK
)
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


@app.get(
    "/", 
    tags=["System"],
    summary="Root endpoint",
    description="Redirects to API documentation.",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT
)
async def root():
    """Redirect to API documentation."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)