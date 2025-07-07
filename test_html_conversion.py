#!/usr/bin/env python3
"""
Test script to validate HTML to markdown conversion.
"""

import re
from html import unescape

def html_to_markdown(html_content: str) -> str:
    """Convert HTML to markdown-like text preserving structure."""
    # Unescape HTML entities first
    text = unescape(html_content)
    
    # Replace headers with markdown headers
    text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n\n', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n\n', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n\n', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n\n', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h5[^>]*>(.*?)</h5>', r'##### \1\n\n', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<h6[^>]*>(.*?)</h6>', r'###### \1\n\n', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Convert bold and italic
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Convert lists
    text = re.sub(r'<ul[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</ul>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<ol[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</ol>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'• \1\n', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Convert paragraphs
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Convert line breaks
    text = re.sub(r'<br[^>]*/?>', '\n', text, flags=re.IGNORECASE)
    
    # Remove any remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up whitespace but preserve structure
    # Split into lines and process each
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            processed_lines.append(line)
        else:
            # Preserve empty lines for structure
            processed_lines.append('')
    
    # Join lines back and clean up excessive empty lines
    text = '\n'.join(processed_lines)
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
    
    return text.strip()

# Test cases
test_cases = [
    # Test with headings and lists
    '''<h3>CS LAC Statutory Visit</h3>
    <ul>
        <li>Name of Social Worker: No Information Provided</li>
        <li>POMS: Adoksadosadosakdsa</li>
        <li>Who was present at the home: No Information Provided</li>
    </ul>
    <p>Summary of the Discussion with the Child/Young Person, including his/her wishes and feelings: No information provided from the transcript to indicate any detailed discussion with the child/young person or their wishes and feelings.</p>''',
    
    # Test with mixed content
    '''<h3>Meeting Summary</h3>
    <p>This is a test paragraph.</p>
    <ul>
        <li>First item</li>
        <li>Second item</li>
        <li>Third item</li>
    </ul>
    <p>Another paragraph with <strong>bold text</strong> and <em>italic text</em>.</p>''',
]

if __name__ == "__main__":
    print("Testing HTML to Markdown conversion...")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print("Original HTML:")
        print(test_case)
        print("\nConverted Markdown:")
        result = html_to_markdown(test_case)
        print(result)
        print("-" * 50)
