"""
########################################################################
# AI Prompt Service - services/gemini_service.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Build a FastAPI that will use Claude and Gemini, with endpoints for prompts
# Version: 1.0.0
# Created: 2025-04-27
# 
# UML Representation:
# +-------------------------+     +-------------------------+
# |       AIService         |     |     GeminiService      |
# +-------------------------+     +-------------------------+
# | +generate_response()    |<|-- | +__init__()            |
# +-------------------------+     | +generate_response()   |
#                                 +-------------------------+
#
# Dependencies:
# - os
# - typing
# - google.generativeai
# - models module
# - services.ai_service module
########################################################################
"""
import os
from typing import Dict, Any, Optional
import google.generativeai as genai
import logging

from src.models import PromptRequest, PromptResponse, AIProvider
from src.services.ai_service import AIService

logger = logging.getLogger(__name__)

class GeminiService(AIService):
    """Service for interacting with Google's Gemini AI."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Gemini service with API credentials."""
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable or pass it directly.")
        genai.configure(api_key=self.api_key)
    
    async def generate_response(self, request: PromptRequest) -> PromptResponse:
        """Generate a response from Gemini based on the prompt request."""
        # Set default model if not provided
        model = request.model or "gemini-pro"
        
        # Prepare parameters
        parameters = request.parameters or {}
        
        # Get the model
        gemini_model = genai.GenerativeModel(model_name=model)
        
        # Prepare chat session
        chat = gemini_model.start_chat()
        
        # Add system prompt as the first message
        chat.send_message(f"System: {request.system_prompt}")
        
        # Add conversation history if provided
        if request.conversation_history:
            for message in request.conversation_history:
                role_prefix = "Human: " if message.role == "human" else "Assistant: "
                chat.send_message(f"{role_prefix}{message.content}")
        
        # Prepare generation config from parameters, ensuring max_tokens is int
        generation_config = {}
        safety_settings = {}
        if request.parameters:
            # Separate standard GenerationConfig fields from others like safety_settings
            allowed_gen_config_keys = {"temperature", "top_p", "top_k", "max_output_tokens", "candidate_count", "stop_sequences"}
            gen_config_params = {k: v for k, v in request.parameters.items() if k in allowed_gen_config_keys}

            # Cast temperature to float
            if 'temperature' in gen_config_params and gen_config_params['temperature'] is not None:
                try:
                    gen_config_params['temperature'] = float(gen_config_params['temperature'])
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert temperature '{gen_config_params['temperature']}' to float for Gemini. Raising error.")
                    # Optionally remove it or raise error
                    # del gen_config_params['temperature']
                    raise ValueError("Invalid value provided for temperature")

            # Rename max_tokens to max_output_tokens for Gemini and cast to int
            if 'max_tokens' in request.parameters:
                # Check if max_tokens value is suitable for conversion
                max_tokens_val = request.parameters['max_tokens']
                if max_tokens_val is not None:
                    try:
                        gen_config_params['max_output_tokens'] = int(max_tokens_val)
                    except (ValueError, TypeError):
                         logger.warning(f"Could not convert max_tokens '{max_tokens_val}' to int for Gemini. Raising error.")
                         # Optionally remove it or raise error
                         # del gen_config_params['max_output_tokens']
                         raise ValueError("Invalid value provided for max_tokens")
                elif 'max_output_tokens' in gen_config_params: # remove if None was passed
                     del gen_config_params['max_output_tokens']

            # Remove max_tokens if it exists after potential rename
            if 'max_tokens' in gen_config_params:
                del gen_config_params['max_tokens']

            logger.debug(f"Processed Gemini GenConfig params: {gen_config_params}")
            generation_config = genai.types.GenerationConfig(**gen_config_params)

            # Handle safety settings if provided
            if "safety_settings" in request.parameters and isinstance(request.parameters["safety_settings"], list):
                safety_settings = request.parameters["safety_settings"]
                logger.debug(f"Using custom safety settings: {safety_settings}")

        # Send the current human input and get response
        response = chat.send_message(f"Human: {request.human_input}", generation_config=generation_config, safety_settings=safety_settings)
        
        # Check for blocked response due to safety
        if not response.candidates:
            logger.warning(f"Gemini response blocked. Prompt feedback: {response.prompt_feedback}")
            # Attempt to find the reason for blockage
            block_reason = "Unknown safety block"
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                block_reason = response.prompt_feedback.block_reason.name
            raise Exception(
                f"Request blocked by Gemini safety filters. Reason: {block_reason}"
            )

        # Extract content from response
        content = response.text if hasattr(response, 'text') else str(response)
        
        # Prepare response
        return PromptResponse(
            response=content,
            ai_provider=AIProvider.GEMINI,
            model=model,
            usage={},  # Gemini might not provide token counts in the same way
            metadata={
                "model": model
            }
        )