"""
########################################################################
# AI Prompt Service - services/__init__.py
# 
# Origin: Created as part of the AI Prompt Service project
# Request: Build a FastAPI that will use Claude and Gemini, with endpoints for prompts
# Version: 1.0.0
# Created: 2025-04-27
# 
# Purpose: Services package initialization
#
# Dependencies: None
########################################################################
"""
# Import services to make them available when importing the package
from src.services.ai_service import AIService
from src.services.claude_service import ClaudeService
from src.services.gemini_service import GeminiService

__all__ = ['AIService', 'ClaudeService', 'GeminiService']