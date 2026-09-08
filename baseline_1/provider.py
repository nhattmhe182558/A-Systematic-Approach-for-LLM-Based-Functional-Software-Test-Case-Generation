"""
provider.py  (Baseline 1 — Augusto et al.)
==========================================

Baseline 1 is a two-stage, single-turn approach (no chat memory). The original
Java used raw HTTP to Gemini with generationConfig temperature=0.1, topP=1.0,
maxOutputTokens=32768. This abstraction replicates that single-shot generation
over Gemini or DeepSeek.

``generate(prompt) -> (text, usage_dict)``.
"""

from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

# generationConfig from the original Java ExperimentationHelper
GENERATION_CONFIG = {"temperature": 0.1, "top_p": 1.0, "max_output_tokens": 32768}


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

    def generate(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        raise NotImplementedError

    @staticmethod
    def create(provider: Optional[str] = None, *, model: str) -> "Provider":
        provider = (provider or os.getenv("LLM_PROVIDER") or "gemini").lower()
        if provider == "gemini":
            return GeminiProvider(model=model)
        if provider == "deepseek":
            return DeepSeekProvider(model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
        raise ValueError(f"Unknown provider '{provider}'. Use 'gemini' or 'deepseek'.")


class GeminiProvider(Provider):
    provider_name = "gemini"

    def __init__(self, model: str):
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set. Add it to your .env file.")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": GENERATION_CONFIG["temperature"],
                "top_p": GENERATION_CONFIG["top_p"],
                "max_output_tokens": GENERATION_CONFIG["max_output_tokens"],
            },
        )

    def generate(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        response = self._model.generate_content(prompt)
        text = response.text if getattr(response, "parts", None) else ""
        return text, _usage_from_gemini(response)


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

    def generate(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=GENERATION_CONFIG["temperature"],
            top_p=GENERATION_CONFIG["top_p"],
            max_tokens=GENERATION_CONFIG["max_output_tokens"],
        )
        out = response.choices[0].message.content or ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if getattr(response, "usage", None):
            usage = {"prompt_tokens": response.usage.prompt_tokens or 0,
                     "completion_tokens": response.usage.completion_tokens or 0}
        return out, usage
