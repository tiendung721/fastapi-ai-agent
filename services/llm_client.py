# services/llm_client.py
import os
import json
from typing import Dict, Any, List, Optional

# Mặc định dùng OpenAI official SDK v1 (pip install openai>=1.40)
from openai import OpenAI, APIError, RateLimitError, APITimeoutError

# ENV:
# OPENAI_API_KEY=<...>
# OPENAI_BASE_URL (tuỳ chọn, nếu dùng proxy/gateway)
# OPENAI_MODEL=gpt-4o-mini (hoặc gpt-4o, gpt-4.1, v.v.)
# LLM_PROVIDER=openai (tương lai có thể thêm azure/openrouter)

_DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
_BASE_URL = os.getenv("OPENAI_BASE_URL", None)

_client: Optional[OpenAI] = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if _BASE_URL:
            _client = OpenAI(base_url=_BASE_URL, api_key=os.getenv("OPENAI_API_KEY"))
        else:
            _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def call_llm_json(messages: List[Dict[str, str]], model: Optional[str] = None, timeout: int = 20) -> Dict[str, Any]:
    """
    Gọi LLM và kỳ vọng trả JSON. Dùng response_format={"type":"json_object"} để ép JSON.
    Trả dict đã parse. Nếu lỗi → {"intent":"unknown","arguments":{}}.
    """
    client = _get_client()
    try:
        resp = client.chat.completions.create(
            model=model or _DEFAULT_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
            timeout=timeout,
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
    except (APIError, RateLimitError, APITimeoutError, ValueError, json.JSONDecodeError):
        return {"intent": "unknown", "arguments": {}}
