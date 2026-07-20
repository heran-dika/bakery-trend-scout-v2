import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def call_gemini(prompt: str, timeout: int = 20):
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return None, "GEMINI_KEY_MISSING"
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={gemini_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return text, "gemini"
        elif response.status_code == 429:
            return None, "GEMINI_RATE_LIMIT"
        else:
            return None, f"GEMINI_ERROR_{response.status_code}"
    except Exception as e:
        return None, "GEMINI_EXCEPTION"

def call_openrouter(prompt: str, timeout: int = 20):
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        return None, "OPENROUTER_KEY_MISSING"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    models = ["deepseek/deepseek-chat", "meta-llama/llama-3.3-70b-instruct", "qwen/qwen-2.5-72b-instruct"]
    
    for model in models:
        headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1000}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return text, f"openrouter_{model.split('/')[-1]}"
            elif response.status_code == 429:
                continue
            else:
                continue
        except Exception as e:
            continue
    
    return None, "OPENROUTER_ALL_FAILED"

def call_llm_with_fallback(prompt: str, response_type: str = "text"):
    print("[LLM] Layer 1 (Gemini)...")
    text, layer = call_gemini(prompt)
    if text:
        print(f"[LLM] OK (Gemini)")
        if response_type == "json":
            clean = text.replace("```json", "").replace("```", "").strip()
            try:
                return json.loads(clean), layer
            except:
                return None, layer
        return text, layer
    
    print("[LLM] Layer 2 (OpenRouter)...")
    text, layer = call_openrouter(prompt)
    if text:
        print(f"[LLM] OK ({layer})")
        if response_type == "json":
            clean = text.replace("```json", "").replace("```", "").strip()
            try:
                return json.loads(clean), layer
            except:
                return None, layer
        return text, layer
    
    print("[LLM] All failed")
    return None, None

if __name__ == "__main__":
    prompt = "Extract: Roti Kukus Srikaya viral. JSON: {product, type}"
    result, layer = call_llm_with_fallback(prompt, response_type="json")
    print(f"\nResult: {result}")
    print(f"Layer: {layer}")
