from typing import Dict, Any
import logging
import aiohttp
import asyncio
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from ...core.config import AppConfig

logger = logging.getLogger(__name__)


class AnalysisRefinementService:
    """Service for handling AI-powered analysis refinement via Azure Functions."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        # Azure Functions configuration from config
        self.functions_base_url = config.azure_functions["base_url"]
        self.functions_key = config.azure_functions["key"]
    
    async def refine_analysis(
        self, 
        original_text: str, 
        current_analysis: str, 
        user_request: str,
        conversation_history: list = None
    ) -> Dict[str, Any]:
        """
        Refine analysis based on user request by calling Azure Functions.
        
        Args:
            original_text: The original transcribed/input text
            current_analysis: The current analysis to be refined
            user_request: The user's refinement request
            conversation_history: Previous refinement conversation history
            
        Returns:
            Dict containing the refined analysis results
        """
        try:
            logger.info("Calling Azure Functions for analysis refinement...")
              # Prepare request data
            request_data = {
                "original_text": original_text,
                "current_analysis": current_analysis,
                "user_request": user_request,
                "conversation_history": conversation_history or []
            }
            
            # Call Azure Functions endpoint (now properly awaited)
            result = await self._call_functions_api(request_data)
            return result
            
        except Exception as e:
            logger.error(f"Analysis refinement failed: {str(e)}")
            return {
                "refined_analysis": f"I apologize, but I encountered an error while processing your refinement request: {str(e)}",
                "status": "error",
                "error": str(e)
            }
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)))
    async def _call_functions_api(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call the Azure Functions API for refinement with retry logic."""
        url = f"{self.functions_base_url}/api/refine-analysis"
        
        logger.info(f"Making request to Azure Functions URL: {url}")
        logger.info(f"Request data keys: {list(request_data.keys())}")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add function key if available  
        if self.functions_key:
            headers["x-functions-key"] = self.functions_key
            logger.info("Function key added to headers")
        else:
            logger.warning("No function key available")
        
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=request_data, headers=headers) as response:
                    logger.info(f"Response status: {response.status}")
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info("Analysis refinement completed successfully via Azure Functions")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Azure Functions call failed with status {response.status}: {error_text}")
                        raise aiohttp.ClientError(f"Azure Functions returned status {response.status}: {error_text}")
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout error when calling Azure Functions: {str(e)}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error when calling Azure Functions: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Azure Functions: {str(e)}")
            raise Exception(f"Failed to call Azure Functions: {str(e)}")
    
    def generate_refinement_suggestions(self, analysis_text: str) -> list:
        """
        Generate suggestions for how users might want to refine their analysis.
        
        Args:
            analysis_text: The current analysis text
            
        Returns:
            List of suggested refinement questions/requests
        """
        suggestions = [
            "Give 2–3 specific examples from the conversation.",
            "List the key action items or next steps, briefly.",
            "Summarize the emotional tone in one sentence.",
            "Give the top 3 themes or topics discussed.",
            "Provide a 3–5 bullet point summary.",
            "List any questions or concerns raised, as bullet points.",
            "Make this analysis more detailed (2–3 extra points).",
            "Make this analysis concise (one short paragraph).",
        ]
        
        return suggestions
