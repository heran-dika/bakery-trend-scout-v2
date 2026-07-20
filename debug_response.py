import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

openrouter_key = os.getenv("OPENROUTER_API_KEY")
url = "https://openrouter.ai/api/v1/chat/completions"
headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}

prompt = "Extract product name from: Roti Kukus Srikaya viral di TikTok. Output ONLY valid JSON with fields: product, type. No explanation."

payload = {"model": "deepseek/deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 200}

response = requests.post(url, json=payload, headers=headers, timeout=30)
data = response.json()
text = data["choices"][0]["message"]["content"]

print("Raw response:")
print(repr(text[:80]))

print("\nStripping backticks...")
clean = text.replace("```json", "").replace("```", "").strip()
print(f"After strip: {repr(clean[:80])}")

print("\nParsing JSON...")
try:
    parsed = json.loads(clean)
    print(f"Success: {parsed}")
except Exception as e:
    print(f"Failed: {e}")
