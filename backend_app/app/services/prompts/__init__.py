"""
    Content Processing Services
    
    This module contains services related to: 
    Prompts management and talking points generation
    """
    
from .talking_points_service import TalkingPointsService
from .prompt_service import PromptService
    
__all__ = [
        'TalkingPointsService',
        'PromptService',
    ]