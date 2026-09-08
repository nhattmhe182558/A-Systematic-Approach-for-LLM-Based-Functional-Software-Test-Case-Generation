"""
provider.py  (Baseline 3 — Bhatia et al.)
=========================================

Baseline 3 is a *conversational* approach: the model is first familiarised with
the whole SRS (Prompt 1), then asked for test cases per use case (Prompt 2)
within the SAME chat session, so earlier turns stay in context.

This module abstracts that chat session over two backends:

  * ``GeminiChat``   — ``google.generativeai`` ``start_chat`` (native multi-turn).
  * ``DeepSeekChat`` — OpenAI-compatible; multi-turn is emulated by keeping the
    running ``messages`` list and appending each turn.

Both expose ``send_message(text) -> (text, usage_dict)`` where ``usage_dict``
has ``prompt_tokens`` / ``completion_tokens`` for billing.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple


def _usage_from_gemini(response) -> Dict[str, int]:
    um = getattr(response, "usage_metadata", None)
    if not um:
        return {"prompt_tokens": 0, "completion_tokens": 0}
    return {
        "prompt_tokens": getattr(um, "prompt_token_count", 0) or 0,
        "completion_tokens": getattr(um, "candidates_token_count", 0) or 0,
    }


class ChatProvider:
    """Common interface for a multi-turn chat session."""

    provider_name = "base"

    def send_message(self, text: str) -> Tuple[str, Dict[str, int]]:
        raise NotImplementedError

    @staticmethod
    def create(provider: Optional[str] = None, *, model: str, generation_config: dict) -> "ChatProvider":
        provider = (provider or os.getenv("LLM_PROVIDER") or "gemini").lower()
        if provider == "gemini":
            return GeminiChat(model=model, generation_config=generation_config)
        if provider == "deepseek":
            return DeepSeekChat(model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                                generation_config=generation_config)
        raise ValueError(f"Unknown provider '{provider}'. Use 'gemini' or 'deepseek'.")


class GeminiChat(ChatProvider):
    provider_name = "gemini"

    def __init__(self, model: str, generation_config: dict):
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set. Add it to your .env file.")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name=model, generation_config=generation_config)
        self._chat = self._model.start_chat(history=[])

    def send_message(self, text: str) -> Tuple[str, Dict[str, int]]:
        response = self._chat.send_message(text)
        usage = _usage_from_gemini(response)
        out = response.text if getattr(response, "parts", None) else ""
        return out, usage


class DeepSeekChat(ChatProvider):
    provider_name = "deepseek"

    def __init__(self, model: str, generation_config: dict):
        from openai import OpenAI
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set. Add it to your .env file.")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._temperature = float(generation_config.get("temperature", 0.7))
        self._max_tokens = int(generation_config.get("max_output_tokens", 16384))
        self._messages: List[Dict[str, str]] = []

    def send_message(self, text: str) -> Tuple[str, Dict[str, int]]:
        self._messages.append({"role": "user", "content": text})
        response = self._client.chat.completions.create(
            model=self._model,
            messages=self._messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        out = response.choices[0].message.content or ""
        self._messages.append({"role": "assistant", "content": out})
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if getattr(response, "usage", None):
            usage = {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
            }
        return out, usage
