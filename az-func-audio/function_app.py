import os
import azure.functions as func
import logging
import json
import re
from datetime import datetime, timedelta
from config import AppConfig
from services.transcription_service import TranscriptionService
from services.analysis_service import AnalysisService
from services.storage_service import StorageService
from services.cosmos_service import CosmosService
from services.file_processing_service import FileProcessingService, SYSTEM_GENERATED_TAG

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = func.FunctionApp()


@app.route(route="analytics/users/{userId}", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def get_user_analytics_http(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger function for retrieving user analytics data."""
    logging.info('User analytics HTTP trigger function processed a request.')
    
    try:
        # Extract userId from route parameters
        user_id = req.route_params.get('userId')
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "User ID is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Extract query parameters
        days = int(req.params.get('days', 30))
        
        # Initialize services
        config = AppConfig()
        cosmos_service = CosmosService(config)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get user analytics data from Cosmos DB
        analytics_data = get_user_analytics_data(cosmos_service, user_id, start_date, end_date, days)
        
        return func.HttpResponse(
            json.dumps(analytics_data),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except ValueError as e:
        logging.error(f"Invalid parameter in user analytics request: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Invalid parameter: {str(e)}"}),
            status_code=400,
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        logging.error(f"User analytics request failed: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Failed to retrieve analytics: {str(e)}"}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


@app.route(route="refine-analysis", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def refine_analysis_http(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger function for analysis refinement using Azure OpenAI."""
    logging.info('Analysis refinement HTTP trigger function processed a request.')
    
    try:
        # Parse request body
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Extract required parameters
        original_text = req_body.get('original_text', '')
        current_analysis = req_body.get('current_analysis', '')
        user_request = req_body.get('user_request', '')
        conversation_history = req_body.get('conversation_history', [])
        
        if not user_request:
            return func.HttpResponse(
                json.dumps({"error": "user_request is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Initialize services
        config = AppConfig()
        analysis_service = AnalysisService(config)
        
        # Create refinement prompt
        refinement_prompt = f"""
Original Content:
{original_text}

Current Analysis:
{current_analysis}

User Request: {user_request}

Please provide a refined response that addresses the user's specific request. You can either:
1. Modify the existing analysis to better meet their needs
2. Provide additional insights they're looking for
3. Focus on specific aspects they've highlighted
4. Answer specific questions about the content

Respond in a helpful, conversational manner as if you're assisting them in understanding the content better.
"""
          # Add conversation history context if available
        if conversation_history:
            context_history = "\n\nPrevious Conversation:\n"
            for entry in conversation_history[-3:]:  # Last 3 exchanges for context
                if 'user_message' in entry and 'ai_response' in entry:
                    context_history += f"User: {entry['user_message']}\n"
                    context_history += f"Assistant: {entry['ai_response']}\n\n"
            refinement_prompt = context_history + refinement_prompt
        
        # Call the analysis service with refinement prompt
        logging.info("Processing analysis refinement request")
        
        # Prepare context and conversation for the analysis service
        system_context = "You are an AI assistant helping to refine and improve analysis of conversations. Provide helpful, accurate refinements based on user requests."
        result = analysis_service.analyze_conversation(refinement_prompt, system_context)
        
        if result.get('status') == 'success':
            response_data = {
                "refined_analysis": result.get('analysis_text', ''),
                "status": "success",
                "usage": result.get('usage', {})
            }
        else:
            response_data = {
                "refined_analysis": f"I apologize, but I encountered an error while processing your refinement request: {result.get('error', 'Unknown error')}",
                "status": "error",
                "error": result.get('error', 'Unknown error')
            }
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logging.error(f"Analysis refinement failed: {str(e)}")
        error_response = {
            "refined_analysis": f"I apologize, but I encountered an error while processing your refinement request: {str(e)}",
            "status": "error",
            "error": str(e)
        }
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )


def is_system_generated_file(blob_name: str) -> bool:
    """Return True if the blob name indicates a system-generated file."""
    return SYSTEM_GENERATED_TAG in blob_name


def get_user_analytics_data(cosmos_service, user_id: str, start_date: datetime, end_date: datetime, days: int) -> dict:
    """Get analytics data for a specific user from Cosmos DB."""
    try:
        # Query jobs for the user within the date range
        # Note: This is a basic implementation. You may need to adjust the query based on your Cosmos DB schema
        query = f"""
        SELECT * FROM c 
        WHERE c.user_id = @user_id 
        AND c.created_at >= @start_date 
        AND c.created_at <= @end_date
        """
        
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@start_date", "value": start_date.isoformat()},
            {"name": "@end_date", "value": end_date.isoformat()}
        ]
        
        # Get user jobs from Cosmos DB
        try:
            items = list(cosmos_service.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
        except Exception as db_error:
            logging.warning(f"Could not query Cosmos DB for user analytics: {str(db_error)}")
            # Return default analytics data if DB query fails
            items = []
        
        # Calculate analytics from the retrieved jobs
        total_jobs = len(items)
        total_minutes = 0
        login_count = 0
        file_upload_count = 0
        text_input_count = 0
        last_activity = None
        
        # Process each job to calculate statistics
        for item in items:
            # Calculate total transcription minutes (if available)
            if 'duration_minutes' in item:
                total_minutes += item.get('duration_minutes', 0)
            
            # Track file vs text uploads
            if item.get('file_name'):
                file_upload_count += 1
            else:
                text_input_count += 1
            
            # Track last activity
            item_date = item.get('created_at')
            if item_date:
                if isinstance(item_date, str):
                    try:
                        item_datetime = datetime.fromisoformat(item_date.replace('Z', '+00:00'))
                        if last_activity is None or item_datetime > last_activity:
                            last_activity = item_datetime
                    except ValueError:
                        pass
        
        # Calculate average job duration
        average_job_duration = total_minutes / total_jobs if total_jobs > 0 else 0
        
        # For login count, we'll use a placeholder since we don't have login tracking in the current schema
        # This could be enhanced by adding a separate analytics table for login events
        login_count = max(1, total_jobs // 5)  # Rough estimate: 1 login per 5 jobs
        
        # Format response according to the expected UserAnalytics interface
        analytics_response = {
            "user_id": user_id,
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "analytics": {
                "transcription_stats": {
                    "total_minutes": total_minutes,
                    "total_jobs": total_jobs,
                    "average_job_duration": round(average_job_duration, 2)
                },
                "activity_stats": {
                    "login_count": login_count,
                    "jobs_created": total_jobs,
                    "last_activity": last_activity.isoformat() if last_activity else None
                },
                "usage_patterns": {
                    "most_active_hours": [],  # Could be calculated from job creation times
                    "most_used_transcription_method": "audio_upload",  # Default value
                    "file_upload_count": file_upload_count,
                    "text_input_count": text_input_count
                }
            }
        }
        
        return analytics_response
        
    except Exception as e:
        logging.error(f"Error calculating user analytics: {str(e)}")
        # Return default analytics structure on error
        return {
            "user_id": user_id,
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "analytics": {
                "transcription_stats": {
                    "total_minutes": 0,
                    "total_jobs": 0,
                    "average_job_duration": 0
                },
                "activity_stats": {
                    "login_count": 0,
                    "jobs_created": 0,
                    "last_activity": None
                },
                "usage_patterns": {
                    "most_active_hours": [],
                    "most_used_transcription_method": None,
                    "file_upload_count": 0,
                    "text_input_count": 0
                }
            }
        }


def is_system_generated_file(blob_name: str) -> bool:
    """Return True if the blob name indicates a system-generated file."""
    return SYSTEM_GENERATED_TAG in blob_name


@app.blob_trigger(
    arg_name="myblob",
    path="%AZURE_STORAGE_RECORDINGS_CONTAINER%/{name}",
    connection="audio",
)
def blob_trigger(myblob: func.InputStream):
    logging.debug("Entered process_media_file function")
    try:
        # Initialize services
        logging.debug("Initializing configuration and services...")

        config = AppConfig()
        blob_path = myblob.name

        # Skip system-generated files
        if is_system_generated_file(blob_path):
            logging.info(f"Skipping system-generated file: {blob_path}")
            return

        # Extract the file extension
        blob_path_without_extension, blob_extension = os.path.splitext(blob_path)

        # Check if the file has a valid extension (audio, text, or document)
        if blob_extension not in config.supported_extensions:
            logging.info(
                f"Skipping file '{myblob.name}' (unsupported extension: {blob_extension})"
            )
            return

        # Initialize services
        cosmos_service = CosmosService(config)
        analysis_service = AnalysisService(config)
        storage_service = StorageService(config)
        file_processing_service = FileProcessingService(config)

        # Determine file type
        file_type = file_processing_service.get_file_type(blob_extension)
        logging.info(
            f"Processing file: {blob_path}",
            extra={
                "file_type": file_type,
                "file_extension": blob_extension,
                "blob_path": blob_path,
            }
        )

        if file_type == "unsupported":
            logging.warning(f"Unsupported file type: {blob_extension}")
            return

        # Remove the container name from the path
        path_without_container = blob_path_without_extension[
            len(config.storage_recordings_container) + 1:
        ]

        # Logging results
        logging.info(f"Full Blob Path: {blob_path}")
        logging.info(f"Blob Path Without Extension: {blob_path_without_extension}")
        logging.info(f"Blob Extension: {blob_extension}")
        logging.info(f"File Type: {file_type}")
        logging.info(f"Path Without Container: {path_without_container}")

        blob_url = f"{config.storage_account_url}/{myblob.name}"

        # Get file document from CosmosDB
        logging.debug("Retrieving file document from CosmosDB...")
        file_doc = cosmos_service.get_file_by_blob_url(blob_url)
        if not file_doc:
            logging.error(f"File document not found for: {blob_path}")
            raise ValueError(f"File document not found: {blob_path}")

        job_id = file_doc["id"]
        logging.debug(f"File document retrieved successfully: Job ID = {job_id}")
        
        # Debug: Log the structure of the file document
        logging.info(f"File document keys: {list(file_doc.keys())}")
        logging.info(f"Prompt subcategory ID: {file_doc.get('prompt_subcategory_id', 'NOT_FOUND')}")
        
        # Check for pre_session_form_data
        if "pre_session_form_data" in file_doc:
            logging.info(f"✅ pre_session_form_data found in file document")
        else:
            logging.info("⚠️ pre_session_form_data NOT found in file document")

        # Process based on file type
        if file_type == "audio":
            formatted_text = process_audio_file(
                config, blob_url, path_without_container, job_id, cosmos_service, storage_service
            )
        elif file_type in ("text", "document"):
            formatted_text = file_processing_service.process_file(blob_url, blob_extension)
            # Save processed/extracted text (for consistency with audio workflow)
            logging.info("Uploading processed/extracted text to storage...")
            processed_text_blob_url = storage_service.upload_text(
                container_name=config.storage_recordings_container,
                blob_name=f"{path_without_container}_{SYSTEM_GENERATED_TAG}_processed_text.txt",
                text_content=formatted_text,
            )
            cosmos_service.update_job_status(
                job_id, f"{file_type}_processed", transcription_file_path=processed_text_blob_url
            )
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Continue with analysis (common for both audio and text)
        logging.info("Retrieving analysis prompts...")
        logging.info(f"Looking for prompts with subcategory ID: {file_doc['prompt_subcategory_id']}")
        
        prompt_text = cosmos_service.get_prompts(file_doc["prompt_subcategory_id"])
        if not prompt_text:
            logging.error(f"No prompts found for analysis with subcategory ID: {file_doc['prompt_subcategory_id']}")
            raise ValueError("No prompts found")
        
        logging.info(f"✅ Analysis prompts retrieved successfully (length: {len(prompt_text)} chars)")
        logging.debug(f"Prompt text preview: {prompt_text[:500]}...")
        logging.debug("Analysis prompts retrieved successfully")

        # Pass pre-session form data as context to the AI (no substitutions in code)
        pre_session_data = file_doc.get("pre_session_form_data", {})
        logging.info(f"Pre-session form data to be sent to AI: {pre_session_data}")
        ai_context = {
            "prompt_text": prompt_text,
            "pre_session_form_data": pre_session_data
        }

        # Analyze the content
        logging.info("Starting analysis of content...")
        logging.info(f"Prompt (with placeholders) being sent to AI (first 500 chars): {prompt_text[:500]}...")
        logging.info(f"Pre-session form data being sent to AI: {pre_session_data}")
        logging.info(f"Transcript/content being analyzed (first 200 chars): {formatted_text[:200]}...")
        logging.info("Note: All placeholder substitutions will be handled by the AI model, not by backend code.")

        # Pass both prompt and form data to the analysis service
        analysis_result = analysis_service.analyze_conversation(
            formatted_text, ai_context
        )
        logging.debug("Analysis completed successfully")

        # Generate and upload DOCX (new jobs) with fallback to PDF for legacy support
        logging.info("Generating and uploading analysis document...")
        try:
            # Use DOCX for new jobs
            docx_blob_url = storage_service.generate_and_upload_docx(
                analysis_result["analysis_text"],
                f"{path_without_container}_{SYSTEM_GENERATED_TAG}_analysis.docx",
            )
            analysis_file_url = docx_blob_url
            logging.debug(f"Analysis DOCX uploaded: {docx_blob_url}")
        except Exception as docx_error:
            # Fallback to PDF if DOCX generation fails
            logging.warning(f"DOCX generation failed, falling back to PDF: {str(docx_error)}")
            pdf_blob_url = storage_service.generate_and_upload_pdf(
                analysis_result["analysis_text"],
                f"{path_without_container}_{SYSTEM_GENERATED_TAG}_analysis.pdf",
            )
            analysis_file_url = pdf_blob_url
            logging.debug(f"Analysis PDF uploaded: {pdf_blob_url}")

        # Final update to job
        cosmos_service.update_job_status(
            job_id,
            "completed",
            analysis_file_path=analysis_file_url,
            analysis_text=analysis_result["analysis_text"],
        )
        logging.info(f"Processing completed successfully for file: {blob_path}")

    except Exception as e:
        logging.error(f"Error processing file: {str(e)}", exc_info=True)
        if "job_id" in locals():
            cosmos_service.update_job_status(job_id, "failed", error_message=str(e))
        raise


def process_audio_file(config, blob_url, path_without_container, job_id, cosmos_service, storage_service):
    """Process audio files through transcription workflow"""
    logging.info("Processing audio file through transcription workflow")
    
    transcription_service = TranscriptionService(config)
    
    # Start transcription
    logging.info("Starting transcription process...")
    transcription_id = transcription_service.submit_transcription_job(blob_url)
    logging.debug(
        f"Transcription job submitted: Transcription ID = {transcription_id}"
    )

    # Update job status to transcribing
    cosmos_service.update_job_status(
        job_id, "transcribing", transcription_id=transcription_id
    )
    logging.debug(f"Job status updated to 'transcribing' for Job ID = {job_id}")

    # Wait for transcription completion
    logging.info("Waiting for transcription to complete...")
    status_data = transcription_service.check_status(transcription_id)
    logging.debug("Transcription status checked successfully")

    formatted_text = transcription_service.get_results(status_data)
    logging.debug("Transcription results retrieved and formatted")

    # Save transcription text
    logging.info("Uploading transcription text to storage...")
    transcription_blob_url = storage_service.upload_text(
        container_name=config.storage_recordings_container,
        blob_name=f"{path_without_container}_{SYSTEM_GENERATED_TAG}_transcription.txt",
        text_content=formatted_text,
    )
    logging.debug(f"Transcription text uploaded: {transcription_blob_url}")

    # Update job with transcription complete
    cosmos_service.update_job_status(
        job_id, "transcribed", transcription_file_path=transcription_blob_url
    )
    logging.debug(f"Job status updated to 'transcribed' for Job ID = {job_id}")
    
    return formatted_text
