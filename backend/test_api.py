import httpx
import asyncio

async def test_gemini():
    api_key = "AIzaSyD2ODMUTWXtb0sVtVlY_9T0uxxywd6Hi_0"
    # Using 1.5-flash as it's the most common stable one
    model = "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "Diga 'Olá Mundo' para testar a API."}]
            }
        ]
    }
    
    print(f"Testing Gemini API with model {model}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Success!")
                print(f"Response: {response.json()['candidates'][0]['content']['parts'][0]['text']}")
            else:
                print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini())
