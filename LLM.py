import os
import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "meta-llama/llama-3-8b-instruct" 

def call_llama(prompt: str, max_tokens: int = 300, temperature: float = 0.3) -> str:
    """
    Call a chat-style LLM (Llama 8B via OpenRouter) and return the assistant text.
    Expects OPENROUTER_API_KEY in env.
    Raises requests.HTTPError on non-200 responses.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that summarizes and plans from short documents."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        if "choices" in data and len(data["choices"]) > 0:
            c = data["choices"][0]
            if isinstance(c, dict) and "text" in c:
                return c["text"]
        raise RuntimeError("Unexpected LLM response format: %s" % (data,))

