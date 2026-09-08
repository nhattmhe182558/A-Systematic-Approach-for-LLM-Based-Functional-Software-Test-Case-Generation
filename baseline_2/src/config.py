"""config.py (Baseline 2) — ported from the original src/config.py."""

import os
from dotenv import load_dotenv

load_dotenv()

# Provider selection
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

# --- Gemini ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GENERATION_MODEL_JSON = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GENERATION_MODEL_TEXT = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = "models/text-embedding-004"

# --- DeepSeek ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

HISTORICAL_DATA_PATH = "data/historical_data.csv"
