from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
import aiohttp
import asyncio
import uuid
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, RetryError
import traceback

from ...core.config import get_app_config, get_cosmos_db_cached, DatabaseError

logger = logging.getLogger(__name__)


class AnalysisRefinementService:
    """Service for handling AI-powered analysis refinement via Azure Functions."""
    
    def __init__(self, cosmos_db=None):
        cfg = get_app_config()
        if cosmos_db is None:
            cosmos_db = get_cosmos_db_cached(cfg)
        self.cosmos = cosmos_db
        self.config = cfg
        
        # Azure Functions configuration
        self.functions_base_url = cfg.azure_functions.get("base_url") if hasattr(cfg, 'azure_functions') else None
        self.functions_key = cfg.azure_functions.get("key") if hasattr(cfg, 'azure_functions') else None
    
    async def refine_analysis(
        self, 
        job_id: str,
        user_id: str,
        user_request: str
    ) -> Dict[str, Any]:
        """
        Refine analysis based on user request by calling Azure Functions.
        
        Args:
            job_id: ID of the job to refine
            user_id: ID of the user requesting refinement
            user_request: The user's refinement request
            
        Returns:
            Dict containing the refined analysis results
        """
        try:
            # Get the job
            job = await self.cosmos.get_job_by_id_async(job_id)
            if not job:
                return {"status": "error", "message": "Job not found"}
            
            # Check access
            if job.get("user_id") != user_id:
                return {"status": "error", "message": "Access denied"}
            
            # Get conversation history
            refinement_history = job.get("refinement_history", [])
            
            # Prepare request data
            request_data = {
                "original_text": job.get("text_content", ""),
                "current_analysis": job.get("analysis_content", ""),
                "user_request": user_request,
                "conversation_history": refinement_history
            }
            
            # Call Azure Functions endpoint. If the functions host is unreachable
            # (network/DNS errors, timeouts) provide a concise assistant-style
            # fallback so the API still returns a useful response to the client
            # instead of failing with a 400 caused by an internal ClientError.
            try:
                # Prefer direct model provider call from the web app for low-latency
                # streaming and fewer cross-host hops. If environment is configured
                # to use Azure OpenAI directly, call that; otherwise fall back to
                # calling the functions API as before.
                if getattr(self.config, 'azure', None) and getattr(self.config.azure, 'openai_endpoint', None):
                    # Direct call to model provider (non-streaming helper)
                    result = await self._call_model_provider(request_data)
                else:
                    result = await self._call_functions_api(request_data)
            except (aiohttp.ClientError, asyncio.TimeoutError, RetryError) as e:
                logger.error(f"Unable to reach Azure Functions for refinement: {str(e)}")
                logger.debug(traceback.format_exc())
                # Provide a short assistant-formatted fallback response
                result = {
                    "refined_analysis": (
                        f"Assistant: I understand you'd like me to {user_request}. "
                        "I couldn't reach the configured refinement service, but here is a concise suggestion you can use as a starting point."
                    ),
                    "status": "fallback"
                }
            
            # Save refinement to history
            refinement_entry = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_request": user_request,
                "ai_response": result.get("refined_analysis", ""),
                "status": result.get("status", "success")
            }
            
            # Update job with new refinement
            if "refinement_history" not in job:
                job["refinement_history"] = []
            
            job["refinement_history"].append(refinement_entry)
            job["last_refined_at"] = datetime.now(timezone.utc).isoformat()
            
            await self.cosmos.update_job_async(job_id, job)
            
            return {
                "status": "success",
                "refinement_id": refinement_entry["id"],
                "ai_response": result.get("refined_analysis", ""),
                "timestamp": refinement_entry["timestamp"]
            }
            
        except DatabaseError as e:
            logger.error(f"Database error refining analysis for job {job_id}: {str(e)}")
            return {"status": "error", "message": "Database service unavailable"}
        except Exception as e:
            logger.error(f"Error refining analysis for job {job_id}: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)))
    async def _call_functions_api(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call the Azure Functions API for refinement with retry logic.

        This method logs request/response details at debug level and converts
        unexpected errors into a controlled fallback object so callers can
        update job state instead of failing outright.
        """
        if not self.functions_base_url:
            # Fallback for when Azure Functions is not configured
            # Return a small assistant-style response that the frontend floating agent can display
            return {
                "refined_analysis": (
                    f"Assistant: I understand you'd like me to {request_data.get('user_request', '')}. "
                    "I couldn't reach the configured refinement service, but here is a concise suggestion you can use as a starting point."
                ),
                "status": "fallback"
            }
        
        url = f"{self.functions_base_url}/api/refine-analysis"

        logger.info(f"Making request to Azure Functions URL: {url}")
        logger.info(f"Functions request payload keys: {list(request_data.keys())}")

        headers = {
            "Content-Type": "application/json"
        }
        
        # Add function key if available  
        if self.functions_key:
            headers["x-functions-key"] = self.functions_key

        # Log header keys (safe) so we can see whether the function key was attached
        logger.info(f"Functions request headers keys: {list(headers.keys())}")

        timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=request_data, headers=headers) as response:
                    logger.info(f"Response status: {response.status}")
                    text = await response.text()
                    logger.debug(f"Functions response text: {text}")

                    if response.status == 200:
                        try:
                            result = await response.json()
                        except Exception:
                            logger.warning("Failed to parse JSON from functions response; returning text as refined_analysis")
                            result = {"refined_analysis": text, "status": "fallback"}

                        logger.info("Analysis refinement completed successfully via Azure Functions")
                        return result
                    else:
                        logger.error(f"Azure Functions call failed with status {response.status}: {text}")
                        # Convert non-200 into a controlled fallback rather than raising raw ClientError
                        return {"refined_analysis": f"Assistant: refinement service returned status {response.status}", "status": "fallback"}
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout error when calling Azure Functions: {str(e)}")
            logger.debug(traceback.format_exc())
            return {"refined_analysis": "Assistant: refinement service timed out.", "status": "fallback"}
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error when calling Azure Functions: {str(e)}")
            logger.debug(traceback.format_exc())
            return {"refined_analysis": "Assistant: refinement service unreachable.", "status": "fallback"}
        except Exception as e:
            # Catch any other unexpected exceptions from aiohttp or json parsing
            logger.error(f"Unexpected error calling Azure Functions: {str(e)}")
            logger.debug(traceback.format_exc())
            return {"refined_analysis": "Assistant: an unexpected error occurred while contacting the refinement service.", "status": "fallback"}

    async def _call_model_provider(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call Azure OpenAI (or configured OpenAI endpoint) for a single-shot refinement.
        This method is used when the web app is responsible for contacting the model provider
        directly (preferred for streaming and fewer network hops).
        """
        # Load settings
        cfg = get_app_config()
        openai_endpoint = getattr(cfg.azure, 'openai_endpoint', None) if getattr(cfg, 'azure', None) else None
        openai_key = getattr(cfg.azure, 'openai_key', None) if getattr(cfg, 'azure', None) else None
        deployment = getattr(cfg.azure, 'openai_deployment_name', None) if getattr(cfg, 'azure', None) else None

        if not openai_endpoint or not openai_key:
            logger.warning("OpenAI endpoint/key not configured; cannot call model provider directly")
            return {"refined_analysis": "Assistant: model provider not configured.", "status": "fallback"}

        # Construct request payload for Azure OpenAI Chat Completions
        messages = [
            {"role": "system", "content": "You are a concise assistant. Answer in 2-3 short sentences or bullet points when requested."},
            {"role": "user", "content": request_data.get('user_request', '')}
        ]

        url = f"{openai_endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-10-21"
        headers = {
            "Content-Type": "application/json",
            "api-key": openai_key
        }

        payload = {
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.2,
        }

        timeout = aiohttp.ClientTimeout(total=300)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    text = await resp.text()
                    if resp.status != 200:
                        logger.error(f"Model provider returned status {resp.status}: {text}")
                        return {"refined_analysis": f"Assistant: model provider returned status {resp.status}", "status": "fallback"}

                    try:
                        data = await resp.json()
                        # Azure OpenAI chat/completions shape: choices[0].message.content
                        content = ""
                        if isinstance(data, dict):
                            choices = data.get('choices') or []
                            if choices and isinstance(choices[0], dict):
                                message = choices[0].get('message') or {}
                                content = message.get('content') or ''
                        return {"refined_analysis": content, "status": "success"}
                    except Exception:
                        logger.warning("Failed to parse JSON from model provider; returning raw text")
                        return {"refined_analysis": text, "status": "fallback"}

        except Exception as e:
            logger.error(f"Error calling model provider: {str(e)}")
            logger.debug(traceback.format_exc())
            return {"refined_analysis": "Assistant: an error occurred contacting the model provider.", "status": "fallback"}

    async def stream_model_provider(self, request_data: Dict[str, Any]):
        """
        Returns an async generator that yields SSE-compatible chunks from Azure OpenAI streaming API.
        The generator yields raw strings which the router will wrap as Server-Sent Events.
        """
        cfg = get_app_config()
        openai_endpoint = getattr(cfg.azure, 'openai_endpoint', None) if getattr(cfg, 'azure', None) else None
        openai_key = getattr(cfg.azure, 'openai_key', None) if getattr(cfg, 'azure', None) else None
        deployment = getattr(cfg.azure, 'openai_deployment_name', None) if getattr(cfg, 'azure', None) else None

        if not openai_endpoint or not openai_key:
            yield "ERROR: OpenAI not configured"
            return

        url = f"{openai_endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-10-21"
        headers = {
            "Content-Type": "application/json",
            "api-key": openai_key
        }

        messages = [
            {"role": "system", "content": "You are a concise assistant. Reply in short, direct sentences or bullets."},
            {"role": "user", "content": request_data.get('user_request', '')}
        ]

        payload = {
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.2,
            "stream": True
        }

        timeout = aiohttp.ClientTimeout(total=0)  # rely on streaming connection

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        yield f"ERROR: model returned status {resp.status}: {text}"
                        return

                    async for line in resp.content:
                        # Each chunk may contain newline-delimited events; forward as-is
                        try:
                            chunk = line.decode(errors='ignore')
                        except Exception:
                            chunk = str(line)
                        if not chunk:
                            continue
                        # The Azure streaming payload often prefixes 'data: ' lines; pass them through
                        yield chunk

        except Exception as e:
            yield f"ERROR: streaming failed: {str(e)}"
            return

    async def get_refinement_history(self, job_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get the refinement history for a job.
        
        Args:
            job_id: ID of the job
            user_id: ID of the user requesting history
            
        Returns:
            Dict containing refinement history
        """
        try:
            # Get the job
            job = await self.cosmos.get_job_by_id_async(job_id)
            if not job:
                return {"status": "error", "message": "Job not found"}
            
            # Check access
            if job.get("user_id") != user_id:
                return {"status": "error", "message": "Access denied"}
            
            refinement_history = job.get("refinement_history", [])
            
            return {
                "status": "success",
                "job_id": job_id,
                "refinement_history": refinement_history,
                "total_refinements": len(refinement_history)
            }
            
        except DatabaseError as e:
            logger.error(f"Database error getting refinement history for job {job_id}: {str(e)}")
            return {"status": "error", "message": "Database service unavailable"}
        except Exception as e:
            logger.error(f"Error getting refinement history for job {job_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_refinement_suggestions(self, job_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get suggested refinement questions for a job's analysis.
        
        Args:
            job_id: ID of the job
            user_id: ID of the user requesting suggestions
            
        Returns:
            Dict containing refinement suggestions
        """
        try:
            # Get the job
            job = await self.cosmos.get_job_by_id_async(job_id)
            if not job:
                return {"status": "error", "message": "Job not found"}
            
            # Check access
            if job.get("user_id") != user_id:
                return {"status": "error", "message": "Access denied"}
            
            # Generate context-based suggestions
            suggestions = [
                "Can you provide more specific recommendations?",
                "What are the key action items from this analysis?",
                "Can you summarize the main themes?",
                "What are the potential risks or concerns mentioned?",
                "Can you expand on the conclusions?",
                "Are there any follow-up questions I should consider?"
            ]
            
            # Could enhance this with AI-generated suggestions based on content
            
            return {
                "status": "success",
                "job_id": job_id,
                "suggestions": suggestions
            }
            
        except DatabaseError as e:
            logger.error(f"Database error getting suggestions for job {job_id}: {str(e)}")
            return {"status": "error", "message": "Database service unavailable"}
        except Exception as e:
            logger.error(f"Error getting suggestions for job {job_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def update_analysis_document(self, job_id: str, user_id: str, new_content: str, format_type: str = "docx") -> Dict[str, Any]:
        """
        Update the analysis document for a job with new content.
        
        Args:
            job_id: ID of the job
            user_id: ID of the user updating the document
            new_content: New content for the analysis
            format_type: Format of the document (docx, pdf, etc.)
            
        Returns:
            Dict containing update result
        """
        try:
            # Get the job
            job = await self.cosmos.get_job_by_id_async(job_id)
            if not job:
                return {"status": "error", "message": "Job not found"}
            
            # Check access
            if job.get("user_id") != user_id:
                return {"status": "error", "message": "Access denied"}
            
            # Update analysis content
            job["analysis_content"] = new_content
            job["analysis_format"] = format_type
            job["analysis_updated_at"] = datetime.now(timezone.utc).isoformat()
            job["analysis_updated_by"] = user_id
            
            await self.cosmos.update_job_async(job_id, job)
            
            return {
                "status": "success",
                "message": "Analysis document updated successfully",
                "job_id": job_id,
                "updated_at": job["analysis_updated_at"]
            }
            
        except DatabaseError as e:
            logger.error(f"Database error updating analysis document for job {job_id}: {str(e)}")
            return {"status": "error", "message": "Database service unavailable"}
        except Exception as e:
            logger.error(f"Error updating analysis document for job {job_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    def close(self):
        """Close any resources - placeholder for consistency"""
        logger.info("AnalysisRefinementService.close: no resources to close")
