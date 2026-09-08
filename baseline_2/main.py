"""
Baseline 2 — Milchevski et al.
"Multi-Step Generation of Test Specifications using Large Language Models for
System-Level Requirements" (ACL 2025, Industry Track).

Faithful port of the original ``llm_functional_test-baseline_2/main.py``.

Multi-step agentic workflow:
  Step 1  Read user requirements (one per line).
  Step 3a Generate Test Design (Decision Table, Markdown).
  Step 3b Extract Test Scenarios (parse the Markdown table).
  Step 3c Generate a Test Purpose per scenario.
  Step 4  For each scenario: Generation Agent -> initial JSON spec, then
          Reflection Agent -> refined JSON spec.
  Step 5  Write artifacts (Markdown report + Decision Table CSV).

The LLM calls go through a ``Provider`` (Gemini or DeepSeek). Prompts are
verbatim from the original.

Usage:
    python main.py --provider gemini  --requirements input/requirements.txt
    python main.py --provider deepseek --requirements input/requirements.txt
"""

import sys
import os
import json
import argparse

from dotenv import load_dotenv

from src.config import LLM_PROVIDER, GENERATION_MODEL_TEXT
from src.generator import TestGenerationSystem
from src.utils import write_test_artifacts_to_file, convert_markdown_table_to_df
from src.logger_utils import ExperimentLogger
from provider import Provider

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MIN_SPECS_TO_GENERATE = 15
MAX_SPECS_TO_GENERATE = 40


def run_full_workflow(requirement_file_path, provider_name):
    print("=====================================================")
    print(" MULTI-STEP TEST SPECIFICATION GENERATION (Baseline 2) ")
    print("=====================================================\n")

    doc_name = os.path.basename(requirement_file_path).split(".")[0]
    log_dir = os.path.join(BASE_DIR, "output")
    logger = ExperimentLogger(log_dir, doc_name, GENERATION_MODEL_TEXT)

    # --- STEP 1: Input ---
    try:
        with open(requirement_file_path, "r", encoding="utf-8") as f:
            user_requirements = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"ERROR: requirements file not found: {requirement_file_path}")
        sys.exit(1)
    if not user_requirements:
        print("ERROR: requirements file is empty.")
        sys.exit(1)
    print(f"STEP 1: Input requirements from '{requirement_file_path}':\n{json.dumps(user_requirements, indent=2)}\n")

    provider = Provider.create(provider_name, model_text=GENERATION_MODEL_TEXT,
                               model_json=GENERATION_MODEL_TEXT)
    generator = TestGenerationSystem(provider=provider, logger=logger)

    # Step 2: no retrieval / few-shot (disabled in the original)
    similar_examples = []

    # Step 3a: Test Design
    print("  3a. Generating Test Design (Decision Table)...")
    logger.start_module("test_design_generator")
    test_design_md = generator.generate_test_design(user_requirements)
    logger.end_module("test_design_generator")
    print(f"-> Test Design:\n{test_design_md}\n")

    decision_table_df = convert_markdown_table_to_df(test_design_md)
    if decision_table_df.empty:
        print("ERROR: Could not convert Decision Table to DataFrame. Stopping.")
        return

    # Step 3b: Extract Scenarios
    print("  3b. Extracting Test Scenarios...")
    test_scenarios = generator.extract_test_scenarios(test_design_md)
    print(f"-> Extracted {len(test_scenarios)} scenarios.\n")
    if not test_scenarios:
        print("ERROR: Could not extract scenarios. Stopping.")
        return

    num_available_scenarios = len(test_scenarios)
    num_to_process = min(num_available_scenarios, MAX_SPECS_TO_GENERATE)
    if num_available_scenarios < MIN_SPECS_TO_GENERATE:
        print(f"WARNING: only {num_available_scenarios} scenarios (< min {MIN_SPECS_TO_GENERATE}). Processing all.")
    test_scenarios = test_scenarios[:num_to_process]
    print(f"-> Will process {len(test_scenarios)} scenarios (max {MAX_SPECS_TO_GENERATE}).\n")

    # Step 3c: Test Purposes
    print("  3c. Generating Test Purposes...")
    logger.start_module("test_purpose_generator")
    test_purposes = generator.generate_test_purposes(user_requirements, test_scenarios)
    logger.end_module("test_purpose_generator")
    print(f"-> Test Purposes:\n{json.dumps(test_purposes, indent=2)}\n")
    if len(test_purposes) != len(test_scenarios):
        print("Warning: number of purposes does not match number of scenarios.")

    # Step 4: Agentic generation + reflection per scenario
    print(f"STEP 4: Agentic generation for {len(test_scenarios)} scenarios...")
    all_refined_specs = []
    for i, (scenario, purpose) in enumerate(zip(test_scenarios, test_purposes)):
        print(f"\n-> Scenario {i + 1}/{len(test_scenarios)}: {scenario}")
        scenario_module_name = f"scenario_{i+1}"
        logger.start_module(scenario_module_name)
        print(f"  4a. Generation Agent working on Scenario {i + 1}...")
        initial_spec = generator.generate_initial_test_spec(
            user_requirements, purpose, scenario, similar_examples
        )
        print(f"  4b. Reflection Agent reviewing Scenario {i + 1}...")
        refined_spec = generator.refine_test_spec(user_requirements, initial_spec)
        logger.end_module(scenario_module_name)
        all_refined_specs.append({
            "scenario_index": i + 1, "scenario": scenario,
            "purpose": purpose, "test_specification": refined_spec,
        })

    print("\n--- COMPLETE: Final Test Specifications for ALL scenarios ---")

    # Step 5: Write artifacts
    out_dir = os.path.join(BASE_DIR, "output", doc_name)
    os.makedirs(out_dir, exist_ok=True)
    output_md_file = os.path.join(out_dir, "test_artifacts_report.md")
    output_csv_file = os.path.join(out_dir, "decision_table.csv")
    write_test_artifacts_to_file(output_md_file, output_csv_file, decision_table_df,
                                 test_scenarios, test_purposes, all_refined_specs)
    logger.close()


def main():
    parser = argparse.ArgumentParser(description="Baseline 2 (Milchevski et al.) — multi-step test spec generation.")
    parser.add_argument("--provider", choices=["gemini", "deepseek"], default=None,
                        help="LLM provider (defaults to LLM_PROVIDER env var, then 'gemini').")
    parser.add_argument("--requirements", default=os.path.join(BASE_DIR, "input", "requirements.txt"),
                        help="Path to the requirements file (one requirement per line).")
    args = parser.parse_args()
    provider_name = (args.provider or LLM_PROVIDER or "gemini").lower()
    run_full_workflow(args.requirements, provider_name)


if __name__ == "__main__":
    main()
