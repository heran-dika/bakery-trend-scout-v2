import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def call_openrouter(prompt: str):
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    data = response.json()
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return text

test_prompt = "Return JSON only: {\"product\": \"test\", \"type\": \"bread\"}"
result = call_openrouter(test_prompt)
print("Raw response:")
print(result)
print("\nTrying to parse as JSON...")
try:
    parsed = json.loads(result)
    print(f"Success: {parsed}")
except json.JSONDecodeError as e:
    print(f"Failed: {e}")
