"""
shared/llm_client.py
====================

Unified BytePlus (OpenAI-compatible) LLM client with full call logging.

Design goals (from the professor's hard rules):
  * Everything must be logged: model input, output, token usage, USD cost,
    wall-clock time. Nothing hidden.
  * Multiple models must be selectable (dola-seed, deepseek-v4-pro,
    deepseek-v4-flash) so tracks can run per-model comparisons.
  * The API key is read ONLY from the environment (.env at project root). It is
    never hardcoded and never written to logs.

Log outputs (per track, under research_project/<track>/logs/):
  * calls.jsonl        -- one JSON object per LLM call (machine-readable)
  * calls.log          -- human-readable one-line-per-call summary
  * running_totals.json-- cumulative tokens + USD + call count for the track

Usage:
    from shared.llm_client import LLMClient, MODELS
    client = LLMClient(track="track_C_intellitest_run", model_key="DEEPSEEK_V4_FLASH")
    text, meta = client.chat("your prompt", system="optional system prompt")
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from dotenv import load_dotenv

# --- Locate project root and load .env -------------------------------------
# This file lives at research_project/shared/llm_client.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

API_KEY_ENV = "BYTEPLUST_API_KEY"
BASE_URL = os.getenv("BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3")

# Model registry: friendly env-var name -> actual model id string.
MODELS: Dict[str, str] = {
    "DOLA_SEED_2_1": os.getenv("DOLA_SEED_2_1", "dola-seed-2-1-turbo-260628"),
    "DEEPSEEK_V4_PRO": os.getenv("DEEPSEEK_V4_PRO", "deepseek-v4-pro-ga-260813"),
    "DEEPSEEK_V4_FLASH": os.getenv("DEEPSEEK_V4_FLASH", "deepseek-v4-flash-ga-260731"),
}

# ---------------------------------------------------------------------------
# Pricing (USD per 1M tokens).
#
# NOTE: BytePlus/ark public pricing for these preview model IDs is not
# documented at the time of writing. These are PLACEHOLDER rates so that cost
# accounting is transparent and adjustable in ONE place. Update as real prices
# become known. The raw token counts are always logged, so USD can be
# recomputed later without re-running anything.
# ---------------------------------------------------------------------------
PRICING_USD_PER_1M: Dict[str, Dict[str, float]] = {
    "dola-seed-2-1-turbo-260628":  {"input": 0.30, "output": 1.20},
    "deepseek-v4-pro-ga-260813":   {"input": 0.55, "output": 2.20},
    "deepseek-v4-flash-ga-260731": {"input": 0.15, "output": 0.60},
}
PRICING_PLACEHOLDER = True  # flag surfaced in logs so no one mistakes these for official rates

_write_lock = threading.Lock()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def compute_cost(model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = PRICING_USD_PER_1M.get(model_id)
    if not rates:
        return 0.0
    return (prompt_tokens / 1_000_000.0) * rates["input"] + \
           (completion_tokens / 1_000_000.0) * rates["output"]


class LLMClient:
    """A logged, OpenAI-compatible chat client bound to one track + one model."""

    def __init__(self, track: str, model_key: str = "DEEPSEEK_V4_FLASH",
                 logs_dir: Optional[Path] = None):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("openai package required: pip install openai") from exc

        api_key = os.getenv(API_KEY_ENV)
        if not api_key:
            raise RuntimeError(
                f"{API_KEY_ENV} not found in environment. Ensure {PROJECT_ROOT/'.env'} exists."
            )
        if model_key not in MODELS:
            raise ValueError(f"Unknown model_key '{model_key}'. Choose from {list(MODELS)}.")

        self.track = track
        self.model_key = model_key
        self.model_id = MODELS[model_key]
        self._client = OpenAI(api_key=api_key, base_url=BASE_URL)

        self.logs_dir = logs_dir or (RESEARCH_ROOT / track / "logs")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.logs_dir / "calls.jsonl"
        self.human_path = self.logs_dir / "calls.log"
        self.totals_path = self.logs_dir / "running_totals.json"

    # -- internal ------------------------------------------------------------
    def _update_totals(self, pt: int, ct: int, cost: float) -> None:
        totals = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
                  "total_tokens": 0, "usd_cost": 0.0}
        if self.totals_path.exists():
            try:
                totals = json.loads(self.totals_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        totals["calls"] += 1
        totals["prompt_tokens"] += pt
        totals["completion_tokens"] += ct
        totals["total_tokens"] += pt + ct
        totals["usd_cost"] = round(totals["usd_cost"] + cost, 6)
        totals["pricing_placeholder"] = PRICING_PLACEHOLDER
        self.totals_path.write_text(json.dumps(totals, indent=2), encoding="utf-8")

    def _log(self, record: dict) -> None:
        with _write_lock:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            with open(self.human_path, "a", encoding="utf-8") as f:
                f.write(
                    f"[{record['timestamp']}] {record['track']:24} | {record['model_id']:28} "
                    f"| in={record['prompt_tokens']:>6} out={record['completion_tokens']:>6} "
                    f"tot={record['total_tokens']:>6} | ${record['usd_cost']:.6f} "
                    f"| {record['latency_s']:.2f}s | {record['status']}\n"
                )
            self._update_totals(record["prompt_tokens"], record["completion_tokens"],
                                 record["usd_cost"])

    # -- public --------------------------------------------------------------
    def chat(self, prompt: str, system: Optional[str] = None,
             temperature: float = 0.0, max_tokens: int = 4096,
             response_json: bool = False, tag: str = "") -> Tuple[str, dict]:
        """Send a chat request; log everything; return (text, metadata)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = dict(model=self.model_id, messages=messages,
                      temperature=temperature, max_tokens=max_tokens)
        if response_json:
            kwargs["response_format"] = {"type": "json_object"}

        start = time.time()
        status = "SUCCESS"
        text = ""
        pt = ct = tt = 0
        error = None
        try:
            resp = self._client.chat.completions.create(**kwargs)
            text = resp.choices[0].message.content or ""
            if resp.usage:
                pt = resp.usage.prompt_tokens or 0
                ct = resp.usage.completion_tokens or 0
                tt = resp.usage.total_tokens or (pt + ct)
        except Exception as exc:  # noqa: BLE001
            status = "FAILED"
            error = str(exc)
        latency = time.time() - start
        cost = compute_cost(self.model_id, pt, ct)

        record = {
            "timestamp": _now(),
            "track": self.track,
            "tag": tag,
            "model_key": self.model_key,
            "model_id": self.model_id,
            "status": status,
            "error": error,
            "latency_s": round(latency, 3),
            "prompt_tokens": pt,
            "completion_tokens": ct,
            "total_tokens": tt,
            "usd_cost": round(cost, 6),
            "pricing_placeholder": PRICING_PLACEHOLDER,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "prompt": prompt,
            "system": system,
            "response": text,
        }
        self._log(record)
        if status == "FAILED":
            raise RuntimeError(f"LLM call failed: {error}")
        return text, record


def append_channel(channel_file: str, line: str) -> None:
    """Append a dated line to a channel .txt (thread-safe-ish)."""
    path = RESEARCH_ROOT / "channels" / channel_file
    path.parent.mkdir(parents=True, exist_ok=True)
    with _write_lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{_now()}] {line}\n")


if __name__ == "__main__":
    # Smoke test: one cheap call on the flash model.
    c = LLMClient(track="_smoke_test", model_key="DEEPSEEK_V4_FLASH")
    out, meta = c.chat("Reply with exactly: OK", tag="smoke")
    print("Response:", out)
    print("Tokens:", meta["total_tokens"], "Cost $:", meta["usd_cost"],
          "Latency:", meta["latency_s"], "s")
    print("Logs written to:", c.logs_dir)
