def call_llm_with_fallback(prompt: str, response_type: str = "text"):
    """3-layer LLM fallback: Gemini -> Cerebras -> OpenRouter"""
    
    print("[LLM] Trying Layer 1 (Gemini)...")
    text, layer = call_gemini(prompt)
    if text:
        print(f"[LLM] ✓ Gemini responded")
        if response_type == "json":
            try:
                clean_text = text.replace('`json', '').replace('`', '').strip()
                return json.loads(clean_text), layer
            except json.JSONDecodeError:
                return None, layer
        return text, layer
    else:
        print(f"[LLM] ✗ Gemini failed: {layer}")
    
    print("[LLM] Trying Layer 2 (Cerebras)...")
    text, layer = call_cerebras(prompt)
    if text:
        print(f"[LLM] ✓ Cerebras responded")
        if response_type == "json":
            try:
                clean_text = text.replace('`json', '').replace('`', '').strip()
                return json.loads(clean_text), layer
            except json.JSONDecodeError:
                return None, layer
        return text, layer
    else:
        print(f"[LLM] ✗ Cerebras failed: {layer}")
    
    print("[LLM] Trying Layer 3 (OpenRouter)...")
    text, layer = call_openrouter(prompt)
    if text:
        print(f"[LLM] ✓ OpenRouter responded ({layer})")
        if response_type == "json":
            try:
                clean_text = text.replace('`json', '').replace('`', '').strip()
                return json.loads(clean_text), layer
            except json.JSONDecodeError:
                print(f"[LLM] JSON parse failed, returning raw: {text[:100]}")
                return None, layer
        return text, layer
    else:
        print(f"[LLM] ✗ OpenRouter failed: {layer}")
    
    print("[LLM] ✗ All layers failed")
    return None, None
