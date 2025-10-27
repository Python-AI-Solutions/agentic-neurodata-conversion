#!/usr/bin/env python3
"""
Test script to verify the upload and metadata workflow.
Tests the infinite loop bug fix.
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_upload():
    """Test file upload."""
    print("=" * 60)
    print("Testing File Upload...")
    print("=" * 60)

    # Upload file
    with open("test_data/spikeglx/Noise4Sam_g0_t0.imec0.ap.bin", "rb") as f:
        files = {"file": ("Noise4Sam_g0_t0.imec0.ap.bin", f, "application/octet-stream")}
        response = requests.post(f"{API_BASE}/api/upload", files=files)

    print(f"Upload Response Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Upload Response: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"Upload Failed: {response.text}")
        return False

def check_status():
    """Check current status."""
    response = requests.get(f"{API_BASE}/api/status")
    if response.status_code == 200:
        data = response.json()
        print(f"\nStatus: {data['status']}")
        print(f"Conversation Type: {data.get('conversation_type')}")
        print(f"Message: {data.get('message', 'None')[:100]}")
        return data
    return None

def test_metadata_response(message):
    """Test responding to metadata request."""
    print(f"\nSending message: '{message}'")
    response = requests.post(
        f"{API_BASE}/api/chat",
        data={"message": message}  # Use form data, not JSON
    )

    print(f"Response Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data.get('response', 'No response')[:200]}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def main():
    print("\n" + "="*60)
    print("COMPREHENSIVE WORKFLOW TEST")
    print("="*60)

    # Reset state
    print("\n1. Resetting system...")
    requests.post(f"{API_BASE}/api/reset")
    time.sleep(1)

    # Upload file
    print("\n2. Uploading file...")
    if not test_upload():
        print("❌ Upload failed")
        return

    # Wait for processing
    print("\n3. Waiting for initial processing...")
    time.sleep(3)

    # Check status
    print("\n4. Checking status...")
    status = check_status()

    if status and status.get('conversation_type') == 'required_metadata':
        print("\n✅ System is asking for metadata (expected)")

        # Test 1: Try "skip for now" - should trigger global skip
        print("\n5. Testing 'skip for now' (should skip all)...")
        test_metadata_response("skip for now")
        time.sleep(2)
        status2 = check_status()

        if status2['status'] != 'awaiting_user_input':
            print("✅ 'skip for now' worked - system proceeded")
        else:
            print("❌ BUG: System is still asking for metadata")
            print(f"   Conversation Type: {status2.get('conversation_type')}")
            print(f"   Message: {status2.get('message', '')[:200]}")

    elif status:
        print(f"\n⚠️  Unexpected state: {status['status']}")
        print(f"   Conversation Type: {status.get('conversation_type')}")

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
