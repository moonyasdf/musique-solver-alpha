"""OpenAI-compatible LLM client wrapper."""

from __future__ import annotations

import logging
from typing import List, Dict, Optional, Iterator

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
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
        streaming: bool = False,
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
        self.streaming = streaming

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: Optional[bool] = None,
    ) -> str:
        """Send a chat completion request to the LLM."""
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        sys_prompt = system_prompt or self.system_prompt
        use_stream = stream if stream is not None else self.streaming

        if use_stream:
            return self._chat_streaming(messages, sys_prompt, temp, tokens)
        else:
            return self._chat_regular(messages, sys_prompt, temp, tokens)

    def _chat_regular(
        self,
        messages: List[Dict[str, str]],
        sys_prompt: str,
        temp: float,
        tokens: int,
    ) -> str:
        """Non-streaming chat completion."""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temp,
            max_tokens=tokens,
            messages=[{"role": "system", "content": sys_prompt}] + messages,
            stream=False,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM response was empty")
        return content.strip()

    def _chat_streaming(
        self,
        messages: List[Dict[str, str]],
        sys_prompt: str,
        temp: float,
        tokens: int,
    ) -> str:
        """Streaming chat completion - collects all chunks and returns full response."""
        response_stream = self.client.chat.completions.create(
            model=self.model,
            temperature=temp,
            max_tokens=tokens,
            messages=[{"role": "system", "content": sys_prompt}] + messages,
            stream=True,
        )

        full_response = ""
        for chunk in response_stream:
            content = chunk.choices[0].delta.content
            if content:
                full_response += content

        if not full_response:
            raise ValueError("LLM streaming response was empty")
        return full_response.strip()
