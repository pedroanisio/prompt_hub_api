"""
########################################################################
# AI Prompt Service - services/ai_service.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Build a FastAPI that will use Claude and Gemini, with endpoints for prompts
# Version: 1.0.0
# Created: 2025-04-27
# 
# UML Representation:
# +-------------------------+
# |       AIService         |
# +-------------------------+
# | +generate_response()    |
# +-------------------------+
#
# Dependencies:
# - abc (Abstract Base Class)
# - typing
# - models module
########################################################################
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from src.models import PromptRequest, PromptResponse


class AIService(ABC):
    """Abstract base class for AI service integration."""
    
    @abstractmethod
    async def generate_response(self, request: PromptRequest) -> PromptResponse:
        """Generate a response from the AI service based on the prompt request."""
        pass