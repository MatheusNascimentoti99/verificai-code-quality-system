import httpx
import asyncio
import json
import time

BASE_URL = "https://verificai-code-quality-system-i9im.onrender.com/api/v1"
LOCAL_URL = "http://localhost:8000/api/v1"

async def run_audit():
    print("=== VERIFICAI SYSTEM AUDIT ===")
    
    # Try production first
    url = BASE_URL
    print(f"Testing PROD URL: {url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Version Check & Wait for Deploy
        print("\n--- Verifying Deployment ---")
        max_retries = 5
        deployed = False
        for i in range(max_retries):
            try:
                resp = await client.get("https://verificai-code-quality-system-i9im.onrender.com/public/version")
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"✅ Version Check: {data.get('version')} - {data.get('status')}")
                    print(f"   Last Updated: {data.get('last_updated')}")
                    print(f"   Features: {', '.join(data.get('features', []))}")
                    deployed = True
                    break
                else:
                    print(f"⏳ Waiting for deploy... (Attempt {i+1}/{max_retries})")
                    await asyncio.sleep(60) # Wait 1 minute between checks
            except Exception as e:
                print(f"⏳ Waiting for deploy... ({str(e)})")
                await asyncio.sleep(60)
        
        if not deployed:
            print("⚠️ Deploy check timed out, but proceeding with other tests...")

        # 2. Login Check
        print("\n--- Testing Authentication ---")
        login_data = {"username": "admin", "password": "Admin@2024"}
        try:
            # Note: /api/v1/login is the standard path
            resp = await client.post(f"{url}/login", data=login_data)
            if resp.status_code == 200:
                token = resp.json().get("access_token")
                print("✅ Login Successful")
                headers = {"Authorization": f"Bearer {token}"}
            else:
                print(f"❌ Login Failed: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
            print(f"❌ Login Error: {str(e)}")
            return

        # 3. Path IDs Fix Check
        print("\n--- Testing Path IDs Fix ---")
        try:
            resp = await client.get(f"{url}/file-paths/public", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                paths = data.get('file_paths', [])
                print(f"✅ Found {len(paths)} public paths")
                # Check for path_ prefix mismatch
                if paths:
                    has_mismatch = any(not p.get('file_id', '').startswith('path_') for p in paths[:5])
                    if has_mismatch:
                        print("⚠️ Note: Some IDs do not have path_ prefix (this is expected if normalized)")
                    else:
                        print("✅ Path IDs correctly prefixed with 'path_'")
            else:
                print(f"❌ Path Fetch Error: {resp.status_code}")
        except Exception as e:
            print(f"❌ Path Error: {str(e)}")

        # 4. Analysis History
        print("\n--- Testing Analysis History ---")
        try:
            # Correcting URL: canonical / and explicit params to avoid validation side-effects
            resp = await client.get(f"{url}/analysis/?skip=0&limit=10", headers=headers)
            if resp.status_code == 200:
                analyses = resp.json().get("items", [])
                print(f"✅ Analysis History found {len(analyses)} entries")
                if analyses:
                    print(f"   Latest: {analyses[0].get('name')} - {analyses[0].get('status')}")
            else:
                print(f"❌ Analysis Fetch Failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"❌ Analysis Error: {str(e)}")

    print("\n=== AUDIT COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(run_audit())
