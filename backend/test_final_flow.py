import requests
import os
import sys
import time
import random

# Production Backend URL
BASE_URL = "https://verificai-code-quality-system-i9im.onrender.com"
LOGIN_URL = f"{BASE_URL}/api/v1/login/json"
REGISTER_URL = f"{BASE_URL}/api/v1/file-paths/"
LIST_URL = f"{BASE_URL}/api/v1/file-paths/"

# Credentials
USERNAME = "admin"
PASSWORD = "Admin@2024"

def test_full_flow():
    print("=== VERIFICAI FINAL PRODUCTION FLOW TEST ===")
    ts = int(time.time())
    
    # 1. Login
    print("\n[1] Testing Login...")
    login_payload = {"username": USERNAME, "password": PASSWORD}
    try:
        response = requests.post(LOGIN_URL, json=login_payload)
        if response.status_code != 200:
            print(f"❌ Login Failed: {response.status_code} - {response.text}")
            return
        
        token = response.json().get("access_token")
        if not token:
            print("❌ No token in response")
            return
        print("✅ Login Successful")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register File
    print("\n[2] Testing File Registration...")
    unique_path = f"K:\\Trabalho\\test_upload_{ts}.py"
    reg_payload = {
        "full_path": unique_path,
        "file_name": os.path.basename(unique_path),
        "folder_path": os.path.dirname(unique_path)
    }
    
    response = requests.post(REGISTER_URL, json=reg_payload, headers=headers)
    if response.status_code != 200:
        print(f"❌ Registration Failed: {response.status_code} - {response.text}")
        return
    
    # IMPORTANT: Use file_id (string) for API interaction, not internal id (int)
    file_id = response.json().get("file_id")
    print(f"✅ Registered File. Public ID: {file_id}")

    # 3. List and Verify
    print("\n[3] Verifying Listing...")
    response = requests.get(LIST_URL, headers=headers)
    if response.status_code != 200:
        print(f"❌ Listing Failed: {response.status_code}")
    else:
        files = response.json().get("file_paths", [])
        found = any(f.get("file_id") == file_id for f in files)
        if found:
            print("✅ File found in list")
        else:
            print("❌ File NOT found in list")

    # 4. Deletion
    print(f"\n[4] Testing Individual Deletion (ID: {file_id})...")
    delete_url = f"{REGISTER_URL}{file_id}"
    response = requests.delete(delete_url, headers=headers)
    if response.status_code == 200:
        print("✅ Single deletion successful")
    else:
        print(f"❌ Deletion failed: {response.status_code} - {response.text}")

    # 5. Bulk Deletion Test
    print("\n[5] Testing Bulk Deletion...")
    bulk_file_ids = []
    for i in range(2):
        p = {
            "full_path": f"bulk_test_{ts}_{i}.py",
            "file_name": f"bulk_test_{ts}_{i}.py",
            "folder_path": "."
        }
        r = requests.post(REGISTER_URL, json=p, headers=headers)
        if r.status_code == 200:
            bulk_file_ids.append(r.json().get("file_id"))
        else:
            print(f"   - Failed to register bulk file {i}: {r.text}")

    if len(bulk_file_ids) == 2:
        print(f"✅ Registered two files for bulk test: {bulk_file_ids}")
        # Note: Bulk delete expects a JSON list of file_id strings
        response = requests.delete(REGISTER_URL, json=bulk_file_ids, headers=headers)
        if response.status_code == 200:
            print("✅ Bulk deletion successful")
        else:
            print(f"❌ Bulk deletion failed: {response.status_code} - {response.text}")
    else:
        print("❌ Could not prepare bulk test")

    print("\n=== FLOW TEST COMPLETE ===")

if __name__ == "__main__":
    test_full_flow()
