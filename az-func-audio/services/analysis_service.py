from typing import Dict, Any
import requests
import logging
from config import AppConfig
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

logger = logging.getLogger(__name__)

class AnalysisServiceError(Exception):
    """Custom exception for analysis service errors."""
    pass

class AnalysisService:
    def __init__(self, config: AppConfig, credential: DefaultAzureCredential = None) -> None:
        """Initialize the AnalysisService with config and optional credential."""
        self.config = config
        self.credential = credential if credential is not None else DefaultAzureCredential()

    def analyze_conversation(self, conversation: str, context: str) -> Dict[str, Any]:
        """Analyze conversation using Azure OpenAI and return analysis results."""
        try:
            logger.info("Getting Bearer Token...")
            token_provider = get_bearer_token_provider(
                self.credential, "https://cognitiveservices.azure.com/.default"
            )
            logger.info("Bearer Token obtained successfully :")
            logger.info("Creating AzureOpenAI client...")
            client = AzureOpenAI(
                azure_endpoint=self.config.azure_openai_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=self.config.azure_openai_version
            )
            logger.info("AzureOpenAI client created successfully: ")  

            prompt = f"{context}\n\n{conversation}"
            logger.info("Prompt created successfully: "+ prompt)
            messages = [
                {"role": "system", "content": """You are an AI assistant designed to help adult social care workers evaluate the progress of their service users. 

IMPORTANT FORMATTING REQUIREMENTS:
- Do NOT use markdown formatting (no #, ##, *, -, etc.)
- Use clear section headers followed by a colon
- Use plain text with proper paragraph breaks
- For lists, use simple bullet points (•) or numbered lists without markdown
- Structure your response with clear sections for easy document formatting
- Write in a professional, clear style suitable for Word documents

Provide concise and accurate summaries of conversations in this format."""},
                {"role": "user", "content": prompt}
                ]
            logger.info("Sending analysis request to AzureOpenAI")
            response = client.chat.completions.create(
                model=self.config.azure_openai_deployment,  # deployment/model name
                messages=messages            
            )
            logger.info("Response received from AzureOpenAI")
            # Validate and extract analysis_text from response
            if not response.choices or not hasattr(response.choices[0], "message"):
                logger.error("Response missing expected message content. Full response: %s", response)
                raise ValueError("Missing message content in response from AzureOpenAI")
            analysis_text = response.choices[0].message.content
            logger.info("Analysis completed successfully:" + analysis_text)

            return {
                "analysis_text": analysis_text,
                "raw_response": response,
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise AnalysisServiceError(f"Analysis failed: {str(e)}") from e

    def process_transcription_results(
        self, transcription_result: Dict[str, Any], context: str
    ) -> Dict[str, Any]:
        """Process transcription results and perform analysis."""
        try:
            # Extract conversation text from transcription
            conversation_text = transcription_result.get(
                "combinedRecognizedPhrases", [{}]
            )[0].get("display", "")
            if not conversation_text:
                raise ValueError("No conversation text found in transcription results")

            # Perform analysis
            analysis_result = self.analyze_conversation(conversation_text, context)

            return {
                "transcription": conversation_text,
                "analysis": analysis_result,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Failed to process transcription results: {str(e)}")
            raise AnalysisServiceError(f"Failed to process transcription results: {str(e)}") from e
# Move this file to az-func-audio/services/analysis_service.py
