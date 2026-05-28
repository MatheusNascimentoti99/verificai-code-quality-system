
import requests
import json

BASE_URL = "http://localhost:3011/api/v1"
TOKEN = "dummy_token" # We'll try to get a real one or just check the logs

def test_analyze_selected():
    # We'll check the backend logs instead of making a real request if we don't have a token,
    # but let's try to see if we can find a token in the logs or env.
    
    payload = {
        "criteria_ids": ["1", "2"],
        "file_paths": ["k:\\Dev\\Projetos\\ProjetoFastApi\\main.py"],
        "analysis_name": "Test Fix",
        "use_code_entry": False
    }
    
    print(f"Sending payload: {json.dumps(payload, indent=2)}")
    # This might fail with 401, but we can check if it reaches the logic before 401 
    # or if we can run it inside the container.
    
if __name__ == "__main__":
    test_analyze_selected()
