"""
########################################################################
# AI Prompt Service - services/claude_service.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Build a FastAPI that will use Claude and Gemini, with endpoints for prompts
# Version: 1.0.0
# Created: 2025-04-27
# 
# UML Representation:
# +-------------------------+     +-------------------------+
# |       AIService         |     |     ClaudeService      |
# +-------------------------+     +-------------------------+
# | +generate_response()    |<|-- | +__init__()            |
# +-------------------------+     | +generate_response()   |
#                                 +-------------------------+
#
# Dependencies:
# - os
# - typing
# - anthropic
# - models module
# - services.ai_service module
########################################################################
"""
import os
from typing import Dict, Any, Optional
import anthropic
from anthropic import Anthropic
import logging

from src.models import PromptRequest, PromptResponse, AIProvider
from src.services.ai_service import AIService

logger = logging.getLogger(__name__)

class ClaudeService(AIService):
    """Service for interacting with Anthropic's Claude AI."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Claude service with API credentials."""
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable or pass it directly.")
        self.client = Anthropic(api_key=self.api_key)
    
    async def generate_response(self, request: PromptRequest) -> PromptResponse:
        """Generate a response from Claude based on the prompt request."""
        # Set default model if not provided
        model = request.model or "claude-3-sonnet-20240229"
        
        # Prepare parameters
        parameters = request.parameters or {}
        
        # Prepare messages for Claude API
        messages = []
        
        # Add conversation history if provided
        if request.conversation_history:
            for message in request.conversation_history:
                if message.role.lower() in ['user', 'assistant']:
                    messages.append({
                        "role": message.role.lower(),
                        "content": message.content
                    })
                else:
                    logger.warning(f"Unsupported role '{message.role}' in conversation history for Claude, skipping.")
                    continue
        
        # Add the current human input
        messages.append({
            "role": "user",
            "content": request.human_input
        })
        
        # Prepare parameters, ensuring correct types for known numeric fields
        api_params = request.parameters.copy() if request.parameters else {}

        # Cast max_tokens to int
        if 'max_tokens' in api_params and api_params['max_tokens'] is not None:
            try:
                api_params['max_tokens'] = int(api_params['max_tokens'])
            except (ValueError, TypeError):
                logger.warning(f"Could not convert max_tokens '{api_params['max_tokens']}' to int. Raising error.")
                raise ValueError("Invalid value provided for max_tokens")

        # Cast temperature to float
        if 'temperature' in api_params and api_params['temperature'] is not None:
            try:
                api_params['temperature'] = float(api_params['temperature'])
            except (ValueError, TypeError):
                logger.warning(f"Could not convert temperature '{api_params['temperature']}' to float. Raising error.")
                raise ValueError("Invalid value provided for temperature")

        try:
            logger.debug(f"Calling Claude API with model: {model}, system_prompt: {request.system_prompt is not None}, num_messages: {len(messages)}, params: {api_params}")
            response = self.client.messages.create(
                model=model,
                system=request.system_prompt, 
                messages=messages,
                **api_params 
            )
            logger.debug(f"Claude API response received. Usage: {response.usage}")

            # Extract content from response
            content = response.content[0].text if response.content else ""
            
            # Prepare response
            return PromptResponse(
                response=content,
                ai_provider=AIProvider.CLAUDE,
                model=model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                metadata={
                    "message_id": response.id,
                    "model": response.model
                }
            )
        except Exception as e:
            logger.error(f"Error generating response from Claude: {str(e)}")
            raise