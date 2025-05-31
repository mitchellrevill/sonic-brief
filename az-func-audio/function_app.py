import os
import azure.functions as func
import logging
import json
from datetime import datetime
from config import AppConfig
from transcription_service import TranscriptionService
from text_processing_service import TextProcessingService
from analysis_service import AnalysisService
from storage_service import StorageService
from cosmos_service import CosmosService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = func.FunctionApp()


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

        # Extract the file extension
        blob_path_without_extension, blob_extension = os.path.splitext(blob_path)

        # Check if the file has a valid extension (audio or text)
        if blob_extension not in config.supported_extensions:
            logging.info(
                f"Skipping file '{myblob.name}' (unsupported extension: {blob_extension})"
            )
            return

        # Initialize services
        cosmos_service = CosmosService(config)
        text_processing_service = TextProcessingService(config)
        analysis_service = AnalysisService(config)
        storage_service = StorageService(config)

        # Determine file type
        file_type = text_processing_service.get_file_type(blob_extension)
        
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

        # Process based on file type
        if file_type == "audio":
            formatted_text = process_audio_file(
                config, blob_url, path_without_container, job_id, cosmos_service, storage_service
            )
        elif file_type == "text":
            formatted_text = process_text_file(
                config, blob_url, blob_extension, path_without_container, job_id, 
                cosmos_service, storage_service, text_processing_service
            )
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Continue with analysis (common for both audio and text)
        logging.info("Retrieving analysis prompts...")
        prompt_text = cosmos_service.get_prompts(file_doc["prompt_subcategory_id"])
        if not prompt_text:
            logging.error("No prompts found for analysis")
            raise ValueError("No prompts found")
        logging.debug("Analysis prompts retrieved successfully")

        # Analyze the content
        logging.info("Starting analysis of content...")
        analysis_result = analysis_service.analyze_conversation(
            formatted_text, prompt_text
        )
        logging.debug("Analysis completed successfully")

        # Generate and upload PDF
        logging.info("Generating and uploading analysis PDF...")
        pdf_blob_url = storage_service.generate_and_upload_pdf(
            analysis_result["analysis_text"],
            f"{path_without_container}_analysis.pdf",
        )
        logging.debug(f"Analysis PDF uploaded: {pdf_blob_url}")

        # Final update to job
        cosmos_service.update_job_status(
            job_id,
            "completed",
            analysis_file_path=pdf_blob_url,
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
        blob_name=f"{path_without_container}_transcription.txt",
        text_content=formatted_text,
    )
    logging.debug(f"Transcription text uploaded: {transcription_blob_url}")

    # Update job with transcription complete
    cosmos_service.update_job_status(
        job_id, "transcribed", transcription_file_path=transcription_blob_url
    )
    logging.debug(f"Job status updated to 'transcribed' for Job ID = {job_id}")
    
    return formatted_text


def process_text_file(config, blob_url, blob_extension, path_without_container, job_id, cosmos_service, storage_service, text_processing_service):
    """Process text files directly without transcription"""
    logging.info("Processing text file directly (skipping transcription)")
    
    # Update job status to processing
    cosmos_service.update_job_status(job_id, "processing_text")
    logging.debug(f"Job status updated to 'processing_text' for Job ID = {job_id}")

    # Process the text file
    logging.info("Processing text file content...")
    formatted_text = text_processing_service.process_text_file(blob_url, blob_extension)
    logging.debug("Text file content processed successfully")

    # Save processed text (for consistency with audio workflow)
    logging.info("Uploading processed text to storage...")
    processed_text_blob_url = storage_service.upload_text(
        container_name=config.storage_recordings_container,
        blob_name=f"{path_without_container}_processed_text.txt",
        text_content=formatted_text,
    )
    logging.debug(f"Processed text uploaded: {processed_text_blob_url}")

    # Update job with text processing complete
    cosmos_service.update_job_status(
        job_id, "text_processed", transcription_file_path=processed_text_blob_url
    )
    logging.debug(f"Job status updated to 'text_processed' for Job ID = {job_id}")
    
    return formatted_text
