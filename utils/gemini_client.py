"""
Thin wrapper around Gemini via langchain-google-genai.

Includes an extract_text() helper because Gemini responses sometimes come
back as a list of typed content blocks instead of a plain string — the
same issue from the blog-writer pipeline (Gemini 2.5 returning typed
blocks rather than str). Every agent that calls the LLM should route its
response through extract_text()/extract_json() rather than assuming
response.content is a plain string.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def get_llm(temperature: float = 0.2, model: str = DEFAULT_MODEL) -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY not set. Copy .env.example to .env and add your "
            "key from https://aistudio.google.com/apikey"
        )
    return ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=api_key)


def extract_text(response: Any) -> str:
    """Normalises a Gemini/LangChain response into a plain string, handling
    the case where .content is a list of typed blocks
    (e.g. [{'type': 'text', 'text': '...'}]) rather than a plain str."""
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text", ""))
        return "\n".join(p for p in parts if p)
    return str(content)


def extract_json(response: Any) -> dict:
    """Parses JSON out of a Gemini response, stripping markdown code fences
    if the model wraps its output in ```json ... ``` despite instructions
    not to."""
    text = extract_text(response).strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini did not return valid JSON: {exc}\nRaw text: {text[:500]}") from exc
