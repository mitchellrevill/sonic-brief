import os
import logging
import ast

# dotenv is used to load local .env files during development. In some container
# builds the package may not be installed which would cause the Functions
# worker to fail indexing (ModuleNotFoundError). Guard the import so the
# app can still start; dependencies should still be installed via
# requirements.txt in production/containers.
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - defensive fallback
    load_dotenv = lambda *a, **k: None

# Load environment variables (no-op when dotenv isn't available)
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_required_env_var(var_name: str) -> str:
    """Get a required environment variable or raise an error with a helpful message"""
    value = os.getenv(var_name)
    if not value:
        logger.error(f"Required environment variable {var_name} is not set")
        raise ValueError(f"Required environment variable {var_name} is not set")
    return value


class AppConfig:
    def __init__(self):
        try:
            prefix = os.getenv("AZURE_COSMOS_DB_PREFIX", "voice_")

            # Cosmos DB settings
            self.cosmos_endpoint: str = get_required_env_var("AZURE_COSMOS_ENDPOINT")
            self.cosmos_database: str = os.getenv("AZURE_COSMOS_DB_NAME", "VoiceDB")
            self.cosmos_jobs_container: str = f"{prefix}jobs"
            self.cosmos_prompts_container: str = f"{prefix}prompts"            # Supported Audio Extensions List
            # Sessions container (prefix + 'user_sessions' to match existing default)
            self.cosmos_sessions_container: str = f"{prefix}user_sessions"
            self.supported_audio_extensions = {
                ".wav",  # Default audio streaming format
                ".pcm",  # PCM (Pulse Code Modulation)
                ".mp3",  # MPEG-1 Audio Layer 3
                ".ogg",  # Ogg Vorbis
                ".opus",  # Opus Codec
                ".flac",  # Free Lossless Audio Codec
                ".alaw",  # A-Law in WAV container
                ".mulaw",  # μ-Law in WAV container
                ".mp4",  # MP4 container (ANY format)
                ".wma",  # Windows Media Audio
                ".aac",  # Advanced Audio Codec
                ".amr",  # Adaptive Multi-Rate
                ".webm",  # WebM audio
                ".m4a",  # MPEG-4 Audio
                ".spx",  # Speex Codec
            }            # Supported Text Extensions List
            self.supported_text_extensions = {
                ".txt",   # Plain text files
                ".srt",   # SubRip subtitle files
                ".vtt",   # WebVTT subtitle files
                ".json",  # JSON files (for structured transcripts)
                ".md",    # Markdown files
                ".rtf",   # Rich Text Format
                ".csv",   # Comma-separated values (for structured data)
            }

            # Document Extensions (for future implementation)
            self.supported_document_extensions = {
                ".pdf",   # Portable Document Format
                ".doc",   # Microsoft Word (legacy)
                ".docx",  # Microsoft Word (modern)
            }

            # Image Extensions (for future OCR implementation)
            self.supported_image_extensions = {
                ".jpg", ".jpeg",  # JPEG images
                ".png",           # PNG images
                ".gif",           # GIF images
                ".bmp",           # Bitmap images
                ".tiff", ".tif",  # TIFF images
                ".webp",          # WebP images
            }            # All supported file extensions (currently processable)
            self.supported_extensions = self.supported_audio_extensions | self.supported_text_extensions | self.supported_document_extensions

            # All known extensions (including future implementations)
            self.all_known_extensions = (
                self.supported_audio_extensions | 
                self.supported_text_extensions | 
                self.supported_document_extensions | 
                self.supported_image_extensions
            )

            # Storage settings
            self.storage_account_url: str = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
            self.storage_recordings_container: str = os.getenv(
                "AZURE_STORAGE_RECORDINGS_CONTAINER"
            )

            # Speech settings
            self.speech_max_speakers: int = int(os.getenv("AZURE_SPEECH_MAX_SPEAKERS", "10"))
            self.speech_transcription_locale: str = os.getenv(
                "AZURE_SPEECH_TRANSCRIPTION_LOCALE", "en-US"
            )

            self.speech_deployment: str = os.getenv("AZURE_SPEECH_DEPLOYMENT")

            # Azure OpenAI settings
            self.azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT")
            self.azure_openai_deployment: str = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            self.azure_openai_version: str = os.getenv("AZURE_OPENAI_API_VERSION")
            self.speech_candidate_locales: str = os.getenv(
                "AZURE_SPEECH_CANDIDATE_LOCALES"
            )

            logger.debug("AppConfig initialization completed successfully")
        except Exception as e:
            logger.error(f"Error initializing AppConfig: {str(e)}")
            raise
