#!/usr/bin/env python3
"""
Simple test to check text processing without requiring environment variables
"""
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_simple_extensions():
    """Test just the extensions without full config"""
    print("🧪 Testing basic file extension detection...")
    
    # Define extensions directly
    supported_audio_extensions = {
        ".wav", ".pcm", ".mp3", ".ogg", ".opus", ".flac", 
        ".alaw", ".mulaw", ".mp4", ".wma", ".aac", ".amr", 
        ".webm", ".m4a", ".spx"
    }
    
    supported_text_extensions = {
        ".txt", ".srt", ".vtt", ".json", ".md", ".rtf", ".csv"
    }
    
    supported_extensions = supported_audio_extensions | supported_text_extensions
    
    def get_file_type(file_extension: str) -> str:
        """Determine the file type based on extension"""
        if file_extension.lower() in supported_audio_extensions:
            return "audio"
        elif file_extension.lower() in supported_text_extensions:
            return "text"
        else:
            return "unsupported"
    
    # Test audio files
    audio_tests = ['.mp3', '.wav', '.m4a', '.webm', '.flac']
    for ext in audio_tests:
        file_type = get_file_type(ext)
        print(f"✅ {ext} -> {file_type}")
        assert file_type == "audio", f"Should classify {ext} as audio"
    
    # Test text files
    text_tests = ['.txt', '.srt', '.vtt', '.json', '.md']
    for ext in text_tests:
        file_type = get_file_type(ext)
        print(f"✅ {ext} -> {file_type}")
        assert file_type == "text", f"Should classify {ext} as text"
    
    # Test unsupported files
    unsupported_tests = ['.pdf', '.doc', '.xlsx', '.png']
    for ext in unsupported_tests:
        file_type = get_file_type(ext)
        print(f"✅ {ext} -> {file_type}")
        assert file_type == "unsupported", f"Should classify {ext} as unsupported"
    
    print("🎉 All basic extension tests passed!")

def test_srt_processing():
    """Test SRT content processing without full service"""
    print("🧪 Testing SRT content processing...")
    
    def process_srt_content(content: str) -> str:
        """Simple SRT processing function"""
        lines = content.strip().split('\n')
        text_lines = []
        current_speaker = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip sequence numbers
            if line.isdigit():
                i += 1
                continue
            
            # Skip timestamp lines (contain --> )
            if '-->' in line:
                i += 1
                continue
            
            # Empty lines separate subtitle blocks
            if not line:
                i += 1
                continue
            
            # This should be subtitle text
            if line:
                # Check if line contains speaker information
                if ':' in line and len(line.split(':', 1)) == 2:
                    speaker, text = line.split(':', 1)
                    speaker = speaker.strip()
                    text = text.strip()
                    
                    if speaker != current_speaker:
                        text_lines.append(f"\n--- {speaker} ---")
                        current_speaker = speaker
                    text_lines.append(f"  {text}")
                else:
                    text_lines.append(f"  {line}")
            
            i += 1
        
        return '\n'.join(text_lines)
    
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
    
    processed = process_srt_content(srt_content)
    print("Processed SRT content:")
    print(processed)
    
    # Check that speakers are extracted
    assert "--- Speaker A ---" in processed
    assert "--- Speaker B ---" in processed
    assert "Hello, how are you today?" in processed
    assert "I'm doing well, thank you for asking." in processed
    
    print("✅ SRT processing test passed!")

if __name__ == "__main__":
    print("🚀 Starting simple text processing tests...")
    try:
        test_simple_extensions()
        test_srt_processing()
        print("🎉 All tests completed successfully!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
