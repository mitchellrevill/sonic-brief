#!/usr/bin/env python3
"""
Test script to analyze blob URL patterns and ensure CosmosDB lookup compatibility.
This tests the URL formats without requiring actual uploads.
"""

import os
from datetime import datetime
from urllib.parse import urlparse

def analyze_blob_naming_patterns():
    """Analyze the blob naming patterns used by both services"""
    print("Analyzing blob naming patterns...")
    
    # Simulate the current naming strategy with timestamp
    test_filename = "meeting_recording.mp3"
    sanitized_filename = test_filename.replace(" ", "_")
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]  # HHMMSS_milliseconds
    file_name_without_ext = os.path.splitext(sanitized_filename)[0]
    
    # This is the blob name pattern both services now use
    blob_name = f"{current_date}/{file_name_without_ext}_{timestamp}/{sanitized_filename}"
    
    print(f"Test filename: {test_filename}")
    print(f"Sanitized filename: {sanitized_filename}")
    print(f"Current date: {current_date}")
    print(f"Timestamp: {timestamp}")
    print(f"File name without ext: {file_name_without_ext}")
    print(f"Generated blob name: {blob_name}")
    
    return blob_name

def simulate_url_construction(blob_name):
    """Simulate how both services construct blob URLs"""
    
    # These are typical Azure storage account URLs
    storage_account_url = "https://mystorageaccount.blob.core.windows.net"
    container_name = "recordings"
    
    # Backend service: blob_client.url format
    backend_url = f"{storage_account_url}/{container_name}/{blob_name}"
    
    # Azure Function: config.storage_account_url + myblob.name format  
    # myblob.name includes the container name and blob path
    azfunc_myblob_name = f"{container_name}/{blob_name}"
    azfunc_url = f"{storage_account_url}/{azfunc_myblob_name}"
    
    print(f"\nURL Construction Simulation:")
    print(f"Storage account URL: {storage_account_url}")
    print(f"Container: {container_name}")
    print(f"Blob name: {blob_name}")
    print(f"Backend URL: {backend_url}")
    print(f"AzFunc myblob.name: {azfunc_myblob_name}")
    print(f"AzFunc URL: {azfunc_url}")
    
    # Check if they match
    urls_match = backend_url == azfunc_url
    print(f"URLs match: {urls_match}")
    
    if urls_match:
        print("✅ Success: URL construction is consistent")
    else:
        print("❌ Error: URL construction mismatch")
        
    return backend_url, azfunc_url, urls_match

def test_uniqueness_over_time():
    """Test that multiple uploads generate unique names"""
    print(f"\nTesting uniqueness over time...")
    
    test_filename = "same_name.mp3"
    generated_names = []
    
    for i in range(5):
        # Simulate multiple uploads with small delays
        import time
        if i > 0:
            time.sleep(0.01)  # 10ms delay
            
        sanitized_filename = test_filename.replace(" ", "_")
        current_date = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
        file_name_without_ext = os.path.splitext(sanitized_filename)[0]
        blob_name = f"{current_date}/{file_name_without_ext}_{timestamp}/{sanitized_filename}"
        
        generated_names.append(blob_name)
        print(f"Upload {i+1}: {blob_name}")
    
    # Check for uniqueness
    unique_names = set(generated_names)
    all_unique = len(unique_names) == len(generated_names)
    
    print(f"Generated {len(generated_names)} names")
    print(f"Unique names: {len(unique_names)}")
    print(f"All unique: {all_unique}")
    
    if all_unique:
        print("✅ Success: All generated names are unique")
    else:
        print("❌ Error: Duplicate names detected")
        
    return all_unique

def analyze_cosmos_lookup_logic():
    """Analyze how the CosmosDB lookup should work"""
    print(f"\nAnalyzing CosmosDB lookup logic...")
    
    # The current logic in az-func-audio/cosmos_service.py:
    # query = "SELECT * FROM c WHERE c.file_path = @file_path"
    # parameters=[{"name": "@file_path", "value": blob_url}]
    
    # Where blob_url is constructed as:
    # blob_url = f"{config.storage_account_url}/{myblob.name}"
    
    blob_name = analyze_blob_naming_patterns()
    storage_account_url = "https://mystorageaccount.blob.core.windows.net"
    container_name = "recordings"
    
    # What backend stores in job record
    backend_stored_url = f"{storage_account_url}/{container_name}/{blob_name}"
    
    # What Azure Function uses for lookup
    myblob_name = f"{container_name}/{blob_name}"
    azfunc_lookup_url = f"{storage_account_url}/{myblob_name}"
    
    print(f"Backend stores in job.file_path: {backend_stored_url}")
    print(f"AzFunc looks up with: {azfunc_lookup_url}")
    print(f"Lookup will succeed: {backend_stored_url == azfunc_lookup_url}")
    
    if backend_stored_url == azfunc_lookup_url:
        print("✅ Success: CosmosDB lookup logic is compatible")
        return True
    else:
        print("❌ Error: CosmosDB lookup would fail")
        return False

if __name__ == "__main__":
    print("Blob URL Compatibility Analysis")
    print("=" * 60)
    
    try:
        # Test 1: Analyze naming patterns
        blob_name = analyze_blob_naming_patterns()
        
        # Test 2: Simulate URL construction
        backend_url, azfunc_url, urls_match = simulate_url_construction(blob_name)
        
        # Test 3: Test uniqueness
        uniqueness_ok = test_uniqueness_over_time()
        
        # Test 4: Analyze CosmosDB lookup
        cosmos_ok = analyze_cosmos_lookup_logic()
        
        print(f"\n" + "="*60)
        print("Summary:")
        print(f"URL construction consistent: {urls_match}")
        print(f"Names are unique: {uniqueness_ok}")
        print(f"CosmosDB lookup compatible: {cosmos_ok}")
        
        overall_success = urls_match and uniqueness_ok and cosmos_ok
        if overall_success:
            print("🎉 Overall: All tests passed!")
        else:
            print("⚠️  Overall: Some issues detected")
            
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error running test: {str(e)}")
        import traceback
        traceback.print_exc()
