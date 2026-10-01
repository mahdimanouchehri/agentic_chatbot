import os
import json
import ast
import re
from functools import lru_cache
from typing import Any, Dict
from pydantic import SecretStr

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from config import DEFAULT_MODEL, DEFAULT_BASE_URL

@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required in .env file.")

    model_name = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
    base_url = os.getenv("OPENROUTER_BASE_URL", DEFAULT_BASE_URL)

    return ChatOpenAI(
        model=model_name,
        openai_api_key=SecretStr(api_key),
        openai_api_base=base_url,
        temperature=0,
        timeout=120,
        max_retries=2,
    )

def _message_text(content: Any) -> str:
    if isinstance(content, str): return content
    if isinstance(content, list):
        return "\n".join([str(p.get("text", p.get("content", ""))) if isinstance(p, dict) else str(p) for p in content if p]).strip()
    return str(content)

def extract_json_object(text: str) -> Dict[str, Any]:
    if not text: return {}
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence_match: text = fence_match.group(1).strip()
    try: return json.loads(text)
    except json.JSONDecodeError: pass
    
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start:end + 1]
        try: return json.loads(snippet)
        except json.JSONDecodeError:
            try: return ast.literal_eval(snippet)
            except Exception: pass
    try: return ast.literal_eval(text)
    except Exception: return {}

def ask_llm_text(system_prompt: str, user_prompt: str) -> str:
    response = get_llm().invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    return _message_text(response.content).strip()

def ask_llm_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    raw = ask_llm_text(system_prompt, user_prompt)
    return extract_json_object(raw)