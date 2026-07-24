import os
import requests
from dotenv import load_dotenv

load_dotenv()

gemini_key = os.getenv("GEMINI_API_KEY")

if not gemini_key:
    print("ERROR: GEMINI_API_KEY not found in .env")
    exit(1)

print("Testing Gemini API...")
print(f"Key present: {'Yes' if gemini_key else 'No'}")

# Test model yang BENERAN dipakai di llm_fallback.py
MODEL = "gemini-2.0-flash"

print(f"\n[1] Testing {MODEL} generateContent...")
url = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={gemini_key}"
payload = {"contents": [{"parts": [{"text": "Hello, say 'test ok' only"}]}]}

response = requests.post(url, json=payload, timeout=20)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    text = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    print(f"Response: {text}")
    print("\n>>> GEMINI 2.0 FLASH OK <<<")
elif response.status_code == 429:
    print(f"Error body: {response.text}")
    print("\n>>> MASIH RATE LIMITED (429) <<<")
elif response.status_code == 404:
    print(f"Error body: {response.text}")
    print("\n>>> MODEL NAME SALAH / TIDAK DITEMUKAN (404) <<<")
else:
    print(f"Error body: {response.text}")
    print(f"\n>>> ERROR STATUS {response.status_code} <<<")
