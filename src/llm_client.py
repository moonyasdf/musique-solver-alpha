"""OpenAI-compatible LLM client wrapper."""

from __future__ import annotations

import logging
from typing import List, Dict, Optional

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency for testing
    OpenAI = None

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper around the OpenAI client for chat completions."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required to initialize LLMClient")
        if OpenAI is None:
            raise ImportError("openai package is required. Install with `pip install openai`." )

        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or "You are a helpful AI assistant."

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a chat completion request to the LLM."""
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        sys_prompt = system_prompt or self.system_prompt

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temp,
            max_tokens=tokens,
            messages=[{"role": "system", "content": sys_prompt}] + messages,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM response was empty")
        return content.strip()
