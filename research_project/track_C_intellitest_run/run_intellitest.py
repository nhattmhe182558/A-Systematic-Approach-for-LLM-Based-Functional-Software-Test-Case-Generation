"""
run_intellitest.py  (Track C)
=============================

Runs the IntelliTest GENERATION pipeline (intellitest/main.py) on the BytePlus
backend by pointing the existing DeepSeek (OpenAI-compatible) provider at the
BytePlus endpoint. No prompt or pipeline-logic changes -- only env wiring, which
is the faithful "Option A" verified by Track B.

For each requested model, this:
  * sets DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL from the root .env
  * runs the full pipeline on the given SRS PDF
  * lets intellitest write its own artifacts + billing logs under
    intellitest/output/<doc>/
  * records a per-model manifest (model id, doc, elapsed, artifact counts) into
    this track's logs so Track F can aggregate.

Usage (from research_project/track_C_intellitest_run/):
  python run_intellitest.py --model DEEPSEEK_V4_FLASH --pdf <path-to-srs.pdf>
  python run_intellitest.py --model DEEPSEEK_V4_PRO  --pdf <path-to-srs.pdf>
  python run_intellitest.py --model DOLA_SEED_2_1    --pdf <path-to-srs.pdf>
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Paths
TRACK_DIR = Path(__file__).resolve().parent
RESEARCH_ROOT = TRACK_DIR.parent
PROJECT_ROOT = RESEARCH_ROOT.parent
INTELLITEST_DIR = PROJECT_ROOT / "intellitest"
ENV_PATH = PROJECT_ROOT / ".env"
PYTHON = str(PROJECT_ROOT / "env" / "Scripts" / "python.exe")

load_dotenv(ENV_PATH)

MODELS = {
    "DOLA_SEED_2_1": os.getenv("DOLA_SEED_2_1", "dola-seed-2-1-turbo-260628"),
    "DEEPSEEK_V4_PRO": os.getenv("DEEPSEEK_V4_PRO", "deepseek-v4-pro-ga-260813"),
    "DEEPSEEK_V4_FLASH": os.getenv("DEEPSEEK_V4_FLASH", "deepseek-v4-flash-ga-260731"),
}
BASE_URL = os.getenv("BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3")
API_KEY = os.getenv("BYTEPLUST_API_KEY", "")


def log_line(msg: str) -> None:
    (TRACK_DIR / "logs").mkdir(parents=True, exist_ok=True)
    with open(TRACK_DIR / "logs" / "track_C.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    print(msg)


def run(model_key: str, pdf: str) -> dict:
    if model_key not in MODELS:
        raise SystemExit(f"Unknown model '{model_key}'. Choose {list(MODELS)}.")
    if not API_KEY:
        raise SystemExit("BYTEPLUST_API_KEY missing from root .env")
    model_id = MODELS[model_key]
    pdf_path = Path(pdf).resolve()
    if not pdf_path.exists():
        raise SystemExit(f"SRS PDF not found: {pdf_path}")

    # Wire the DeepSeek provider to BytePlus (Option A, no code change).
    env = os.environ.copy()
    env["LLM_PROVIDER"] = "deepseek"
    env["DEEPSEEK_API_KEY"] = API_KEY
    env["DEEPSEEK_BASE_URL"] = BASE_URL
    env["DEEPSEEK_MODEL"] = model_id
    env["PDF_DOCUMENT_PATH"] = str(pdf_path)
    # Per-call usage log (tokens/cost/latency) written by the instrumented DeepSeekProvider.
    usage_log = TRACK_DIR / "logs" / f"usage_{model_key}.jsonl"
    env["DEEPSEEK_USAGE_LOG"] = str(usage_log)
    env["DEEPSEEK_MAX_TOKENS"] = "16384"

    log_line(f"=== Track C run: model_key={model_key} model_id={model_id} pdf={pdf_path.name} ===")
    start = time.time()
    proc = subprocess.run(
        [PYTHON, "main.py", "--pdf", str(pdf_path), "--provider", "deepseek"],
        cwd=str(INTELLITEST_DIR), env=env, capture_output=True, text=True,
    )
    elapsed = time.time() - start
    (TRACK_DIR / "logs").mkdir(parents=True, exist_ok=True)
    (TRACK_DIR / "logs" / f"stdout_{model_key}.txt").write_text(proc.stdout, encoding="utf-8")
    (TRACK_DIR / "logs" / f"stderr_{model_key}.txt").write_text(proc.stderr, encoding="utf-8")

    doc_stem = pdf_path.stem
    out_dir = INTELLITEST_DIR / "output" / doc_stem
    # Snapshot artifacts into this track under a per-model dir.
    dest = TRACK_DIR / "runs" / f"{model_key}__{doc_stem}"
    if out_dir.exists():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(out_dir, dest)

    def count(glob):
        return len(list(dest.rglob(glob))) if dest.exists() else 0

    manifest = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model_key": model_key,
        "model_id": model_id,
        "pdf": str(pdf_path),
        "doc_stem": doc_stem,
        "returncode": proc.returncode,
        "elapsed_s": round(elapsed, 2),
        "artifacts": {
            "screens_json": count("screens.json"),
            "business_processes_json": count("business_processes.json"),
            "screen_graph_json": count("screen_graph.json"),
            "screen_variables_json": count("screen_variables.json"),
            "pairwise_csv": count("*.csv"),
            "testcase_json": count("TC-*_batch_*.json"),
            "mutation_json": count("mutation_tc_*.json"),
        },
        "snapshot_dir": str(dest),
    }
    (TRACK_DIR / "logs" / f"manifest_{model_key}.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    log_line(f"Completed {model_key} rc={proc.returncode} in {elapsed:.1f}s. "
             f"Artifacts: {manifest['artifacts']}")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(MODELS))
    ap.add_argument("--pdf", required=True)
    args = ap.parse_args()
    run(args.model, args.pdf)
