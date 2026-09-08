"""
provider.py  (Baseline 2 — Milchevski et al.)
=============================================

Baseline 2 uses two model roles:
  * a **text** model (decision table, test purposes) and
  * a **JSON** model (initial spec + reflection), which the original ran with
    ``response_mime_type="application/json"``.

This abstraction exposes ``generate_text(prompt)`` and ``generate_json(prompt)``
over Gemini or DeepSeek. Both return ``(text, usage_dict)`` where ``usage_dict``
carries ``prompt_tokens`` / ``completion_tokens`` for the logger.
"""

from __future__ import annotations

import os
from typing import Dict, Optional, Tuple


def _usage_from_gemini(response) -> Dict[str, int]:
    um = getattr(response, "usage_metadata", None)
    if not um:
        return {"prompt_tokens": 0, "completion_tokens": 0}
    return {
        "prompt_tokens": getattr(um, "prompt_token_count", 0) or 0,
        "completion_tokens": getattr(um, "candidates_token_count", 0) or 0,
    }


class Provider:
    provider_name = "base"

    def generate_text(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        raise NotImplementedError

    def generate_json(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        raise NotImplementedError

    @staticmethod
    def create(provider: Optional[str] = None, *, model_text: str, model_json: str) -> "Provider":
        provider = (provider or os.getenv("LLM_PROVIDER") or "gemini").lower()
        if provider == "gemini":
            return GeminiProvider(model_text=model_text, model_json=model_json)
        if provider == "deepseek":
            return DeepSeekProvider(model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
        raise ValueError(f"Unknown provider '{provider}'. Use 'gemini' or 'deepseek'.")


class GeminiProvider(Provider):
    provider_name = "gemini"

    def __init__(self, model_text: str, model_json: str):
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set. Add it to your .env file.")
        genai.configure(api_key=api_key)
        self._json_model = genai.GenerativeModel(
            model_json, generation_config={"response_mime_type": "application/json"}
        )
        self._text_model = genai.GenerativeModel(model_text)

    def generate_text(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        response = self._text_model.generate_content(prompt)
        return response.text, _usage_from_gemini(response)

    def generate_json(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        response = self._json_model.generate_content(prompt)
        return response.text, _usage_from_gemini(response)


class DeepSeekProvider(Provider):
    provider_name = "deepseek"

    def __init__(self, model: str):
        from openai import OpenAI
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set. Add it to your .env file.")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def _chat(self, prompt: str, json_mode: bool) -> Tuple[str, Dict[str, int]]:
        kwargs = {"model": self._model, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.2}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self._client.chat.completions.create(**kwargs)
        out = response.choices[0].message.content or ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if getattr(response, "usage", None):
            usage = {"prompt_tokens": response.usage.prompt_tokens or 0,
                     "completion_tokens": response.usage.completion_tokens or 0}
        return out, usage

    def generate_text(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        return self._chat(prompt, json_mode=False)

    def generate_json(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        return self._chat(prompt, json_mode=True)
