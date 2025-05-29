#!/usr/bin/env python3
"""
Test script to verify text processing functionality
"""
import os
import sys
import logging
from unittest.mock import Mock

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import AppConfig
from text_processing_service import TextProcessingService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_file_type_detection():
    """Test file type detection functionality"""
    logger.info("Testing file type detection...")
    
    # Create a mock config
    config = AppConfig()
    service = TextProcessingService(config)
    
    # Test audio files
    audio_extensions = ['.mp3', '.wav', '.m4a', '.webm', '.flac']
    for ext in audio_extensions:
        assert service.is_audio_file(ext), f"Should detect {ext} as audio"
        assert service.get_file_type(ext) == "audio", f"Should classify {ext} as audio"
    
    # Test text files
    text_extensions = ['.txt', '.srt', '.vtt', '.json', '.md']
    for ext in text_extensions:
        assert service.is_text_file(ext), f"Should detect {ext} as text"
        assert service.get_file_type(ext) == "text", f"Should classify {ext} as text"
    
    # Test unsupported files
    unsupported_extensions = ['.pdf', '.doc', '.xlsx', '.png']
    for ext in unsupported_extensions:
        assert not service.is_audio_file(ext), f"Should not detect {ext} as audio"
        assert not service.is_text_file(ext), f"Should not detect {ext} as text"
        assert service.get_file_type(ext) == "unsupported", f"Should classify {ext} as unsupported"
    
    logger.info("✅ File type detection tests passed!")

def test_srt_processing():
    """Test SRT content processing"""
    logger.info("Testing SRT content processing...")
    
    config = AppConfig()
    service = TextProcessingService(config)
    
    # Sample SRT content
    srt_content = """1
00:00:01,000 --> 00:00:05,000
Speaker A: Hello, how are you today?

2
00:00:05,500 --> 00:00:10,000
Speaker B: I'm doing well, thank you for asking.

3
00:00:11,000 --> 00:00:15,000
Speaker A: That's great to hear!
"""
    
    processed = service._process_srt_content(srt_content)
    
    # Check that speakers are extracted
    assert "--- Speaker A ---" in processed
    assert "--- Speaker B ---" in processed
    assert "Hello, how are you today?" in processed
    assert "I'm doing well, thank you for asking." in processed
    
    logger.info("✅ SRT processing tests passed!")

def test_json_processing():
    """Test JSON content processing"""
    logger.info("Testing JSON content processing...")
    
    config = AppConfig()
    service = TextProcessingService(config)
    
    # Sample JSON transcript content
    json_content = """[
    {
        "speaker": "John",
        "text": "Hello everyone, welcome to the meeting."
    },
    {
        "speaker": "Jane",
        "text": "Thank you John, glad to be here."
    }
]"""
    
    processed = service._process_json_content(json_content)
    
    # Check that content is extracted
    assert "John" in processed
    assert "Jane" in processed
    assert "Hello everyone, welcome to the meeting." in processed
    assert "Thank you John, glad to be here." in processed
    
    logger.info("✅ JSON processing tests passed!")

def test_config_extensions():
    """Test that config has the expected extensions"""
    logger.info("Testing config extensions...")
    
    config = AppConfig()
    
    # Check audio extensions
    assert '.mp3' in config.supported_audio_extensions
    assert '.wav' in config.supported_audio_extensions
    assert '.webm' in config.supported_audio_extensions
    
    # Check text extensions
    assert '.txt' in config.supported_text_extensions
    assert '.srt' in config.supported_text_extensions
    assert '.json' in config.supported_text_extensions
    
    # Check combined extensions
    assert '.mp3' in config.supported_extensions
    assert '.txt' in config.supported_extensions
    
    logger.info("✅ Config extensions tests passed!")

def run_all_tests():
    """Run all tests"""
    logger.info("🧪 Starting text processing service tests...")
    
    try:
        test_config_extensions()
        test_file_type_detection()
        test_srt_processing()
        test_json_processing()
        
        logger.info("🎉 All tests passed successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
