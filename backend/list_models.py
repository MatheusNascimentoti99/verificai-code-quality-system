import httpx
import asyncio

async def list_models():
    api_key = "AIzaSyD2ODMUTWXtb0sVtVlY_9T0uxxywd6Hi_0"
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    print(f"Listing available models for API key...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                models = response.json().get('models', [])
                print(f"Found {len(models)} models.")
                for m in models:
                    print(f" - {m['name']}")
            else:
                print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
