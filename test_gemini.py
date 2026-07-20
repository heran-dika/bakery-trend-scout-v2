import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

gemini_key = os.getenv("GEMINI_API_KEY")

if not gemini_key:
    print("ERROR: GEMINI_API_KEY not found in .env")
    exit(1)

print(f"Testing Gemini API...")
print(f"Key present: {'Yes' if gemini_key else 'No'}")

# Test 1: List models
print("\n[1] Listing available models...")
url = f"https://generativelanguage.googleapis.com/v1/models?key={gemini_key}"
response = requests.get(url)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    models = response.json().get("models", [])
    print(f"Available models ({len(models)}):")
    for model in models[:5]:
        print(f"  - {model.get('name')}")
else:
    print(f"Error: {response.text}")

# Test 2: Try simple generate
print("\n[2] Testing generateContent...")
url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={gemini_key}"

payload = {
    "contents": [{"parts": [{"text": "Hello, say 'test ok' only"}]}]
}

response = requests.post(url, json=payload)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    text = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    print(f"Response: {text}")
else:
    print(f"Error: {response.text}")
