#!/usr/bin/env python3
"""
Test script to verify the analysis document update functionality.
"""

import requests
import json
from typing import Dict, Any

# Configuration
BACKEND_URL = "http://localhost:8000"
TEST_JOB_ID = "test-job-123"  # Replace with actual job ID for testing

def test_update_analysis_document():
    """Test updating an analysis document."""
    
    # Sample analysis content
    test_content = """
    # Analysis Report

    ## Executive Summary
    This is a test analysis with markdown formatting.

    ## Key Findings
    - Finding 1: Important discovery
    - Finding 2: Another insight
    - Finding 3: Critical information

    ## Recommendations
    1. **Action Item 1**: Immediate priority
    2. **Action Item 2**: Medium priority
    3. **Action Item 3**: Long-term goal

    ## Conclusion
    This analysis demonstrates the system's ability to handle markdown content and convert it to DOCX format.
    """
    
    # Convert to HTML (simulating frontend processing)
    html_content = convert_markdown_to_html(test_content)
    
    # Request payload
    payload = {
        "html_content": html_content,
        "format": "docx"
    }
    
    # Headers (you would need a real auth token)
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_TOKEN_HERE"  # Replace with actual token
    }
    
    # Make the request
    url = f"{BACKEND_URL}/api/jobs/{TEST_JOB_ID}/analysis-document"
    
    try:
        response = requests.put(url, json=payload, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success! Document URL: {result.get('document_url')}")
            return True
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception occurred: {e}")
        return False

def convert_markdown_to_html(markdown_text: str) -> str:
    """Convert markdown text to HTML (simplified version)."""
    html_parts = []
    
    sections = markdown_text.split('\n\n')
    for section in sections:
        if not section.strip():
            continue
            
        lines = section.split('\n')
        if not lines:
            continue
            
        first_line = lines[0].strip()
        
        # Check for headers
        if first_line.startswith('#'):
            level = len(first_line) - len(first_line.lstrip('#'))
            header_text = first_line.lstrip('#').strip()
            html_parts.append(f'<h{level}>{header_text}</h{level}>')
            
            # Process remaining lines
            for line in lines[1:]:
                if line.strip():
                    html_parts.append(f'<p>{line.strip()}</p>')
                    
        else:
            # Process as regular content
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith(('-', '*', '•')):
                    # List item
                    text = line[1:].strip()
                    html_parts.append(f'<li>{text}</li>')
                elif line.startswith(tuple(f'{i}.' for i in range(1, 10))):
                    # Numbered list item
                    text = line.split('.', 1)[1].strip()
                    html_parts.append(f'<li>{text}</li>')
                else:
                    # Regular paragraph
                    html_parts.append(f'<p>{line}</p>')
    
    return ''.join(html_parts)

if __name__ == "__main__":
    print("Testing Analysis Document Update API...")
    test_update_analysis_document()
