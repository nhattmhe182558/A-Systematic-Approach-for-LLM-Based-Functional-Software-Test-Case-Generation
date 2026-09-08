"""
config.py
=========

Centralized configuration for the IntelliTest pipeline. This mirrors the
original ``back_end/cores/configs/variables.py`` as closely as possible: the
same constant names, the same values, and the same derived output-path layout.

Two things differ from the original, by design:

  1. **Provider settings** were added (Gemini + DeepSeek) so the same pipeline
     can run on either backend. The original was Gemini-only.
  2. Output paths are computed **relative to a configurable document** instead of
     a single hard-coded PDF, but the *structure* under ``output/<doc>/`` is
     identical to the original.

The pipeline always runs **full mode** (end-to-end, all stages), so there are no
per-stage feature flags to toggle a partial run.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# CORE CONFIGURATION
# ============================================================================
# Project root (this file lives at the project root next to main.py).
PROJECT_ROOT = Path(__file__).resolve().parent

# Document Configuration
#   Original default: BACK_END_ROOT / "documents/pdfs/4lv-ieee830-lastest.pdf"
#   Here the document lives in ./input and can be overridden via PDF_DOCUMENT_PATH.
INPUT_DIR = PROJECT_ROOT / "input"
PDF_DOCUMENT_PATH = Path(
    os.getenv("PDF_DOCUMENT_PATH", str(INPUT_DIR / "4lv-ieee830-lastest.pdf"))
)
DOCUMENT_NAME = PDF_DOCUMENT_PATH.stem  # filename without extension

# ============================================================================
# PROVIDER / LLM CONFIGURATION
# ============================================================================
# "gemini" or "deepseek". CLI --provider overrides this.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

# --- Gemini ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_FLASH_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- DeepSeek (OpenAI-compatible) ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# API Request Settings
REQUEST_DELAY_SECONDS = 1.0  # Delay between API requests (seconds)
RESPONSE_FORMAT = "application/json"  # LLM response format

# ============================================================================
# THREAD & PROCESSING CONFIGURATION
# ============================================================================
MAX_WORKERS = 3  # Number of concurrent threads
BATCH_SIZE = 50  # Items processed per batch
THREAD_TIMEOUT = 0  # Thread timeout (0 = disabled, rely on API timeout)
MAX_RETRIES = 1  # Retry attempts for failed operations

# Thread Safety Settings
USE_LOCK_FOR_FILE_WRITING = True
USE_LOCK_FOR_CONTEXT_UPDATE = True

# Batch Processing Settings
CLEAR_OLD_BATCH_FILES = True
BACKUP_FAILED_CASES = True
SAVE_PROMPTS_TO_TXT = True
SHOW_PROGRESS = True
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# Screen-graph specific parallelism (original used 4 workers here)
SCREEN_GRAPH_MAX_WORKERS = 4

# ============================================================================
# MODULE-SPECIFIC CONFIGURATION
# ============================================================================
# --- Business Process Detector ---
BUSINESS_PROCESS_MAX_PROCESSES = 10
BUSINESS_PROCESS_MIN_STEPS = 2

# --- Screen Variable Detector ---
SCREEN_VARIABLE_MAX_GROUPS = 50
SCREEN_VARIABLE_MAX_ELEMENTS = 20

# --- Screen Graph Detector ---
SCREEN_GRAPH_MAX_CONNECTIONS = 100
SCREEN_GRAPH_CONNECTION_SCORE_THRESHOLD = 5

# --- Path Processor ---
PATH_MAX_LENGTH = 10
PATH_MIN_SCORE = 1

# --- Pairwise Generator ---
PAIRWISE_MAX_COMBINATIONS = 1000
PAIRWISE_USE_BUSINESS_PROCESS_GROUPING = True

# --- Test Case Generator ---
ENABLE_CONTEXT_UPDATE = True
SUCCESS_OUTCOME_THRESHOLD = "true"
GENERATE_NAVIGATION_ONLY = True

# --- Mutation Test Case Generator ---
MUTATION_MAX_VARIATIONS = 10
MUTATION_INCLUDE_BOUNDARY_VALUES = True
MUTATION_INCLUDE_NEGATIVE_TESTING = True

# ============================================================================
# OUTPUT DIRECTORY STRUCTURE
# ============================================================================
# Original wrote under BACK_END_ROOT/output/<doc>/. Here we write under
# PROJECT_ROOT/output/<doc>/ so artifacts sit next to output/output.md.
OUTPUT_PATH = PROJECT_ROOT / "output"
DOCUMENT_OUTPUT_PATH = OUTPUT_PATH / DOCUMENT_NAME

# Module Output Directories
GENERAL_OUTPUT_DIRECTORY = DOCUMENT_OUTPUT_PATH / "general"
PAIRWISE_OUTPUT_DIRECTORY = DOCUMENT_OUTPUT_PATH / "pairwise"
PATH_OUTPUT_DIRECTORY = DOCUMENT_OUTPUT_PATH / "path"
TESTCASE_OUTPUT_DIRECTORY = DOCUMENT_OUTPUT_PATH / "testcase"
MUTATION_OUTPUT_DIRECTORY = DOCUMENT_OUTPUT_PATH / "mutation_test_case"

# Logs Directory Structure
LOGS_OUTPUT_DIRECTORY = DOCUMENT_OUTPUT_PATH / "logs"
API_BILLING_OUTPUT_DIRECTORY = LOGS_OUTPUT_DIRECTORY / "api_billing"
BUSINESS_PROCESS_PROMPTS_DIRECTORY = LOGS_OUTPUT_DIRECTORY / "business_process_prompts"
SCREEN_VARIABLE_PROMPTS_DIRECTORY = LOGS_OUTPUT_DIRECTORY / "screen_variable_prompts"
SCREEN_GRAPH_PROMPTS_DIRECTORY = LOGS_OUTPUT_DIRECTORY / "screen_graph_prompts"
TEST_CASE_PROMPTS_DIRECTORY = LOGS_OUTPUT_DIRECTORY / "test_case_prompts"
TEST_CASE_RETRY_PROMPTS_DIRECTORY = LOGS_OUTPUT_DIRECTORY / "test_case_retry_prompts"

# ============================================================================
# SPECIFIC FILE PATHS
# ============================================================================
SCREENS_OUTPUT_PATH = GENERAL_OUTPUT_DIRECTORY / "screens.json"
BUSINESS_PROCESSES_OUTPUT_PATH = GENERAL_OUTPUT_DIRECTORY / "business_processes.json"
SCREEN_GRAPH_OUTPUT_PATH = GENERAL_OUTPUT_DIRECTORY / "screen_graph.json"
SCREEN_VARIABLES_OUTPUT_PATH = GENERAL_OUTPUT_DIRECTORY / "screen_variables.json"
PATHS_OUTPUT_PATH = GENERAL_OUTPUT_DIRECTORY / "paths.json"
TEST_CASE_CONTEXT_PATH = GENERAL_OUTPUT_DIRECTORY / "test_case_context.json"

# Legacy Aliases (kept for parity with the original)
SCREEN_VARIABLES_FILE = SCREEN_VARIABLES_OUTPUT_PATH
BUSINESS_PROCESS_OUTPUT_PATH = GENERAL_OUTPUT_DIRECTORY
BUSINESS_EMBEDDINGS_FILE_PATH = GENERAL_OUTPUT_DIRECTORY / "business_function_embeddings.json"

# ============================================================================
# PERFORMANCE CONFIGURATION
# ============================================================================
ENABLE_PERFORMANCE_LOGGING = True
PERFORMANCE_LOG_PATH = LOGS_OUTPUT_DIRECTORY / "execution_timing.log"


# ============================================================================
# HELPERS
# ============================================================================
def all_output_directories() -> List[Path]:
    """All directories the pipeline may write to (used to pre-create them)."""
    return [
        GENERAL_OUTPUT_DIRECTORY,
        PAIRWISE_OUTPUT_DIRECTORY,
        PATH_OUTPUT_DIRECTORY,
        TESTCASE_OUTPUT_DIRECTORY,
        MUTATION_OUTPUT_DIRECTORY,
        LOGS_OUTPUT_DIRECTORY,
        API_BILLING_OUTPUT_DIRECTORY,
        BUSINESS_PROCESS_PROMPTS_DIRECTORY,
        SCREEN_VARIABLE_PROMPTS_DIRECTORY,
        SCREEN_GRAPH_PROMPTS_DIRECTORY,
        TEST_CASE_PROMPTS_DIRECTORY,
        TEST_CASE_RETRY_PROMPTS_DIRECTORY,
    ]


def ensure_output_dirs() -> None:
    for d in all_output_directories():
        d.mkdir(parents=True, exist_ok=True)


def apply_document(pdf_path: str) -> None:
    """Re-point every derived path at a new document at runtime.

    The original updated ``variables.py`` in place by rewriting the file; here
    we simply recompute the module-level path constants. Called by ``main`` when
    the user passes ``--pdf``.
    """
    global PDF_DOCUMENT_PATH, DOCUMENT_NAME
    global DOCUMENT_OUTPUT_PATH, GENERAL_OUTPUT_DIRECTORY, PAIRWISE_OUTPUT_DIRECTORY
    global PATH_OUTPUT_DIRECTORY, TESTCASE_OUTPUT_DIRECTORY, MUTATION_OUTPUT_DIRECTORY
    global LOGS_OUTPUT_DIRECTORY, API_BILLING_OUTPUT_DIRECTORY
    global BUSINESS_PROCESS_PROMPTS_DIRECTORY, SCREEN_VARIABLE_PROMPTS_DIRECTORY
    global SCREEN_GRAPH_PROMPTS_DIRECTORY, TEST_CASE_PROMPTS_DIRECTORY
    global TEST_CASE_RETRY_PROMPTS_DIRECTORY
    global SCREENS_OUTPUT_PATH, BUSINESS_PROCESSES_OUTPUT_PATH, SCREEN_GRAPH_OUTPUT_PATH
    global SCREEN_VARIABLES_OUTPUT_PATH, PATHS_OUTPUT_PATH, TEST_CASE_CONTEXT_PATH
    global SCREEN_VARIABLES_FILE, BUSINESS_PROCESS_OUTPUT_PATH, BUSINESS_EMBEDDINGS_FILE_PATH
    global PERFORMANCE_LOG_PATH

    PDF_DOCUMENT_PATH = Path(pdf_path)
    DOCUMENT_NAME = PDF_DOCUMENT_PATH.stem

    DOCUMENT_OUTPUT_PATH = OUTPUT_PATH / DOCUMENT_NAME
    GENERAL_OUTPUT_DIRECTORY = DOCUMENT_OUTPUT_PATH / "general"
    PAIRWISE_OUTPUT_DIRECTORY = DOCUMENT_OUTPUT_PATH / "pairwise"
    PATH_OUTPUT_DIRECTORY = DOCUMENT_OUTPUT_PATH / "path"
    TESTCASE_OUTPUT_DIRECTORY = DOCUMENT_OUTPUT_PATH / "testcase"
    MUTATION_OUTPUT_DIRECTORY = DOCUMENT_OUTPUT_PATH / "mutation_test_case"

    LOGS_OUTPUT_DIRECTORY = DOCUMENT_OUTPUT_PATH / "logs"
    API_BILLING_OUTPUT_DIRECTORY = LOGS_OUTPUT_DIRECTORY / "api_billing"
    BUSINESS_PROCESS_PROMPTS_DIRECTORY = LOGS_OUTPUT_DIRECTORY / "business_process_prompts"
    SCREEN_VARIABLE_PROMPTS_DIRECTORY = LOGS_OUTPUT_DIRECTORY / "screen_variable_prompts"
    SCREEN_GRAPH_PROMPTS_DIRECTORY = LOGS_OUTPUT_DIRECTORY / "screen_graph_prompts"
    TEST_CASE_PROMPTS_DIRECTORY = LOGS_OUTPUT_DIRECTORY / "test_case_prompts"
    TEST_CASE_RETRY_PROMPTS_DIRECTORY = LOGS_OUTPUT_DIRECTORY / "test_case_retry_prompts"

    SCREENS_OUTPUT_PATH = GENERAL_OUTPUT_DIRECTORY / "screens.json"
    BUSINESS_PROCESSES_OUTPUT_PATH = GENERAL_OUTPUT_DIRECTORY / "business_processes.json"
    SCREEN_GRAPH_OUTPUT_PATH = GENERAL_OUTPUT_DIRECTORY / "screen_graph.json"
    SCREEN_VARIABLES_OUTPUT_PATH = GENERAL_OUTPUT_DIRECTORY / "screen_variables.json"
    PATHS_OUTPUT_PATH = GENERAL_OUTPUT_DIRECTORY / "paths.json"
    TEST_CASE_CONTEXT_PATH = GENERAL_OUTPUT_DIRECTORY / "test_case_context.json"

    SCREEN_VARIABLES_FILE = SCREEN_VARIABLES_OUTPUT_PATH
    BUSINESS_PROCESS_OUTPUT_PATH = GENERAL_OUTPUT_DIRECTORY
    BUSINESS_EMBEDDINGS_FILE_PATH = GENERAL_OUTPUT_DIRECTORY / "business_function_embeddings.json"
    PERFORMANCE_LOG_PATH = LOGS_OUTPUT_DIRECTORY / "execution_timing.log"
