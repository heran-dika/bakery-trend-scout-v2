import os
import json
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

def call_gemini(prompt: str, timeout: int = 20):
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return None, "GEMINI_KEY_MISSING"

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-lite:generateContent?key={gemini_key}"
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
            print(f"[LLM][Gemini] HTTP {response.status_code}: {response.text[:300]}")
            return None, f"GEMINI_ERROR_{response.status_code}"
    except Exception as e:
        print(f"[LLM][Gemini] EXCEPTION: {e}")
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
                if text:
                    return text, f"openrouter_{model.split('/')[-1]}"
                print(f"[LLM][OpenRouter/{model}] Status 200 tapi content kosong: {json.dumps(data)[:300]}")
                continue
            elif response.status_code == 429:
                print(f"[LLM][OpenRouter/{model}] RATE_LIMIT (429), coba model berikutnya...")
                continue
            else:
                print(f"[LLM][OpenRouter/{model}] HTTP {response.status_code}: {response.text[:300]}")
                continue
        except Exception as e:
            print(f"[LLM][OpenRouter/{model}] EXCEPTION: {e}")
            continue

    return None, "OPENROUTER_ALL_FAILED"

def _parse_and_validate(text: str, response_schema):
    clean = text.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError as e:
        return None, f"JSON_PARSE_ERROR: {e}"

    if response_schema is None:
        return parsed, None

    if not isinstance(parsed, dict):
        return None, f"SCHEMA_INPUT_NOT_DICT: got {type(parsed).__name__} instead of object. Raw: {str(parsed)[:200]}"

    try:
        validated = response_schema(**parsed)
        return validated.model_dump(), None
    except ValidationError as e:
        return None, f"SCHEMA_VALIDATION_ERROR: {e}"
    except TypeError as e:
        return None, f"SCHEMA_TYPE_ERROR: {e}"

def call_llm_with_fallback(prompt: str, response_type: str = "text", response_schema=None):
    if response_schema is not None:
        response_type = "json"

    strict_suffix = "\n\nPENTING: Balas HANYA JSON valid sesuai skema yang diminta. Jangan tambah field lain, jangan pakai nilai di luar opsi enum yang disebutkan."

    print("[LLM] Layer 1 (Gemini)...")
    text, layer = call_gemini(prompt)
    if text:
        if response_type == "json":
            data, err = _parse_and_validate(text, response_schema)
            if data is not None:
                print("[LLM] OK (Gemini)")
                return data, layer
            print(f"[LLM] Gemini output invalid ({err}), retry dengan prompt lebih tegas...")
            text2, layer2 = call_gemini(prompt + strict_suffix)
            if text2:
                data2, err2 = _parse_and_validate(text2, response_schema)
                if data2 is not None:
                    print("[LLM] OK (Gemini, retry)")
                    return data2, layer2
                print(f"[LLM] Gemini retry masih invalid ({err2})")
        else:
            print("[LLM] OK (Gemini)")
            return text, layer
    else:
        print(f"[LLM] Gemini failed: {layer}")

    print("[LLM] Layer 2 (OpenRouter)...")
    text, layer = call_openrouter(prompt)
    if text:
        if response_type == "json":
            data, err = _parse_and_validate(text, response_schema)
            if data is not None:
                print(f"[LLM] OK ({layer})")
                return data, layer
            print(f"[LLM] OpenRouter output invalid ({err})")
        else:
            print(f"[LLM] OK ({layer})")
            return text, layer
    else:
        print(f"[LLM] OpenRouter failed: {layer}")

    print("[LLM] All failed")
    return None, None

if __name__ == "__main__":
    from typing import Literal

    class TestSchema(BaseModel):
        product: str
        type: Literal["bread", "cake", "pastry", "donut", "other"]

    prompt = """Extract the specific bakery product name mentioned. Return JSON only:
{"product": "...", "type": "bread/cake/pastry/donut/other"}

Article:
Title: Roti Kukus Srikaya viral di TikTok
Snippet: Roti kukus srikaya jadi tren baru di kalangan anak muda Jakarta."""

    result, layer = call_llm_with_fallback(prompt, response_schema=TestSchema)
    print(f"\nResult: {result}")
    print(f"Layer: {layer}")
