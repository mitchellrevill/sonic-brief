#!/usr/bin/env python3
"""
Test script to verify document processing functionality works correctly
"""
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import AppConfig
from document_processing_service import DocumentProcessingService

def test_document_processing_availability():
    """Test that document processing libraries are available"""
    print("Testing document processing availability...")
    
    try:
        # Test the imports
        import docx2txt
        from docx import Document
        import PyPDF2
        print("✅ All document processing libraries are available")
        
        # Test service initialization
        config = AppConfig()
        service = DocumentProcessingService(config)
        print("✅ DocumentProcessingService initialized successfully")
        
        # Test file type detection
        test_extensions = ['.pdf', '.docx', '.doc', '.rtf', '.txt']
        for ext in test_extensions:
            is_doc = service.is_document_file(ext)
            expected = ext in ['.pdf', '.docx', '.doc', '.rtf']
            if is_doc == expected:
                print(f"✅ {ext}: correctly identified as {'document' if expected else 'non-document'}")
            else:
                print(f"❌ {ext}: incorrectly identified")
                return False
        
        # Test configuration
        supported_exts = config.supported_extensions
        document_exts = config.supported_document_extensions
        
        print(f"\nConfiguration check:")
        print(f"Document extensions: {sorted(document_exts)}")
        print(f"Supported extensions include documents: {document_exts.issubset(supported_exts)}")
        
        if document_exts.issubset(supported_exts):
            print("✅ Document extensions are included in supported extensions")
        else:
            print("❌ Document extensions are NOT included in supported extensions")
            missing = document_exts - supported_exts
            print(f"Missing extensions: {missing}")
            return False
        
        print("\n🎉 Document processing setup is correct!")
        return True
        
    except ImportError as e:
        print(f"❌ Missing library: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

def test_file_type_routing():
    """Test that file types are correctly routed"""
    print("\nTesting file type routing...")
    
    try:
        from text_processing_service import TextProcessingService
        
        config = AppConfig()
        text_service = TextProcessingService(config)
        
        # Test document file type detection
        test_cases = [
            ('.pdf', 'document'),
            ('.docx', 'document'),
            ('.doc', 'document'),
            ('.txt', 'text'),
            ('.mp3', 'audio'),
            ('.unknown', 'unsupported')
        ]
        
        for ext, expected_type in test_cases:
            actual_type = text_service.get_file_type(ext)
            if actual_type == expected_type:
                print(f"✅ {ext}: correctly routed to {expected_type}")
            else:
                print(f"❌ {ext}: expected {expected_type}, got {actual_type}")
                return False
        
        print("✅ File type routing is correct!")
        return True
        
    except Exception as e:
        print(f"❌ Error during file type routing test: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing Document Processing Setup\n")
    
    success = True
    success &= test_document_processing_availability()
    success &= test_file_type_routing()
    
    print(f"\n{'🎉 All tests passed!' if success else '❌ Some tests failed!'}")
    sys.exit(0 if success else 1)
