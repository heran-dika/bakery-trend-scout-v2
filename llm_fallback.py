import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def call_llm_with_fallback(prompt: str, response_type: str = "text"):
    """Call Gemini API via HTTP request."""
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("ERROR: GEMINI_API_KEY not found")
        return None, None
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": gemini_key
    }
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"API Error: {response.status_code} - {response.text}")
            return None, None
        
        data = response.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        if response_type == "json":
            try:
                return json.loads(text), "gemini"
            except json.JSONDecodeError:
                return None, "gemini"
        
        return text, "gemini"
    
    except Exception as e:
        print(f"[LLM Fallback] Error: {e}")
        return None, None

if __name__ == "__main__":
    test_prompt = 'Extract product name. Return JSON: {"product": "value"}'
    result, layer = call_llm_with_fallback(test_prompt, response_type="json")
    print(f"Result: {result}")
