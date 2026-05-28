
import httpx
import time
import os
import json
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "saimon"
PASSWORD = "password123"

async def run_test():
    print(f"--- Starting E2E Test Analysis ---")
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Login
        print(f"Logging in as {USERNAME}...")
        login_data = {"username": USERNAME, "password": PASSWORD}
        # Correct path is /api/v1/login based on main.py registration
        response = await client.post(f"{BASE_URL}/login", data=login_data)
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"Login successful!")

        # 2. Upload file
        print(f"Uploading file...")
        target_file = Path("k:/Trabalho/Hitss/VerificAI/verificai-code-quality-system/backend/app/main.py")
        file_id = f"test_{int(time.time())}"
        
        with open(target_file, "rb") as f:
            files = {"file": (target_file.name, f, "text/plain")}
            data = {
                "file_id": file_id,
                "original_name": target_file.name,
                "relative_path": target_file.name
            }
            upload_response = await client.post(f"{BASE_URL}/upload/", headers=headers, files=files, data=data)
        
        if upload_response.status_code not in [200, 201]:
            print(f"Upload failed: {upload_response.text}")
            return
        
        file_path = upload_response.json()["file_path"]
        print(f"Upload successful: {file_path}")

        # 3. Get criteria
        print(f"Getting criteria...")
        criteria_response = await client.get(f"{BASE_URL}/general-analysis/criteria", headers=headers)
        if criteria_response.status_code != 200:
            print(f"Failed to get criteria: {criteria_response.text}")
            return
        
        criteria_list = [c["text"] for c in criteria_response.json()[:3]] # Select first 3
        print(f"Selected criteria: {criteria_list}")

        # 4. Start analysis
        print(f"Starting analysis...")
        analysis_request = {
            "name": "E2E Test Analysis",
            "description": "Verification of LLM fix",
            "file_paths": [file_path],
            "llm_provider": "openrouter",
            "temperature": 0.7,
            "max_tokens": 1000,
            "criteria": criteria_list
        }
        
        # Note: endpoint is /general-analysis/create
        analysis_response = await client.post(f"{BASE_URL}/general-analysis/create", headers=headers, json=analysis_request)
        if analysis_response.status_code not in [200, 201]:
            print(f"Analysis start failed: {analysis_response.text}")
            return
        
        analysis_id = analysis_response.json()["id"]
        print(f"Analysis started! ID: {analysis_id}")

        # 5. Poll for completion
        print(f"Polling for completion (max 120s)...")
        start_time = time.time()
        while time.time() - start_time < 120:
            status_response = await client.get(f"{BASE_URL}/analysis/{analysis_id}", headers=headers)
            if status_response.status_code != 200:
                print(f"Failed to get status: {status_response.text}")
                break
            
            data = status_response.json()
            status_val = data["status"]
            print(f"Current status: {status_val} ({data.get('progress', 0)}%)")
            
            if status_val == "completed":
                print(f"COMPLETED! Results received.")
                print(f"--- Analysis Results Summary ---")
                print(str(data.get("results", ""))[:500] + "...")
                return True
            elif status_val == "failed":
                print(f"FAILED! Error: {data.get('error')}")
                return False
            
            await asyncio.sleep(5)
        
        print(f"TIMED OUT after 120s.")
        return False

import asyncio
if __name__ == "__main__":
    asyncio.run(run_test())
