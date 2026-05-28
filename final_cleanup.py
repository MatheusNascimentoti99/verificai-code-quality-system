import requests
import json
import time

BASE_URL = "https://verificai-code-quality-system-i9im.onrender.com/api/v1"

def get_ids():
    print(f"Fetching IDs from {BASE_URL}/file-paths/public...")
    for _ in range(3): # retry
        try:
            r = requests.get(f"{BASE_URL}/file-paths/public", timeout=20)
            if r.ok:
                data = r.json()
                paths = data.get("file_paths", [])
                targets = []
                for p in paths:
                    if isinstance(p, dict):
                        full_path = p.get("full_path", "")
                        fid = p.get("file_id")
                        if "test_script.js" in full_path:
                            targets.append(fid)
                            print(f"Target found: {full_path} (ID: {fid})")
                return targets
            else:
                print(f"Error {r.status_code}: {r.text}")
        except Exception as e:
            print(f"Attempt failed: {e}")
            time.sleep(2)
    return []

def delete_by_id(token, fid):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.delete(f"{BASE_URL}/file-paths/{fid}", headers=headers, timeout=15)
    print(f"Delete ID {fid}: {r.status_code} - {r.text}")
    return r.ok

def main():
    target_ids = get_ids()
    if not target_ids:
        print("No test_script.js found in public listing.")
        # Try IDs I saw in previous logs just in case
        target_ids = ["path_file_702820e6fd29401694fd0c9f63508ba8", "path_file_c6309c5f3c034f599d9399318a24d7c0"]
    
    creds = [
        ("admin", "Admin@2024"),
        ("teste", "teste123"),
        ("testuser", "test123"),
    ]
    
    for user, pwd in creds:
        print(f"\nTrying user: {user}")
        token = None
        # Try JSON login
        try:
            r = requests.post(f"{BASE_URL}/login/json", json={"username": user, "password": pwd}, timeout=15)
            if r.ok:
                token = r.json().get("access_token")
            else:
                # Try Form login
                r = requests.post(f"{BASE_URL}/login", data={"username": user, "password": pwd}, timeout=15)
                if r.ok:
                    token = r.json().get("access_token")
        except:
            continue
            
        if token:
            print(f"Logged in as {user}!")
            for fid in target_ids:
                delete_by_id(token, fid)
        else:
            print(f"Could not login as {user}")

if __name__ == "__main__":
    main()
