"""
Baseline 3 — Bhatia et al.
"System test case design from requirements specifications: insights and
challenges of using ChatGPT" (S. Bhatia, T. Gandhi, D. Kumar, P. Jalote, 2024).

Faithful port of the original ``llm_functional_test-baseline_3/main.py``.

Approach (conversational / specification-based):
  1. Prompt 1 familiarises the model with the full SRS (JSON) in a chat session.
  2. For each use case, Prompt 2 asks for specification-based test cases in a
     6-column Markdown table, generated within the same chat session.
  3. The Markdown table rows are parsed into structured JSON records.

Prompts are kept verbatim. The only change vs. the original is that the LLM
call goes through ``ChatProvider`` so it runs on Gemini OR DeepSeek.

Usage:
    python main.py --provider gemini
    python main.py --provider deepseek
"""

import os
import json
import time
import re
import argparse

from dotenv import load_dotenv

from provider import ChatProvider
from logger_utils import ExperimentLogger

load_dotenv()

# --- CONFIG ---
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
generation_config = {
    "temperature": 0.7,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 16384,
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Documents to run (mirrors the original DOCUMENTS_CONFIG).
DOCUMENTS_CONFIG = [
    {
        "name": "4LV",
        "input_path": "input/srs_extracted_4lv.json",
        "output_path": "output/4LV/generated_test_cases_4LV.json",
        "project_name": "Training Request Approval System",
    }
]


def extract_use_cases_from_json(filepath, logger=None):
    """Read the SRS JSON and safely extract use cases (any format)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        msg = f"Error reading JSON file: {e}"
        (logger.log if logger else print)(msg)
        return []

    extracted_use_cases = []
    if "use_cases" in data and isinstance(data["use_cases"], list):
        for uc in data["use_cases"]:
            uc_id = uc.get("id", "N/A")
            name = uc.get("name", "N/A")
            desc = uc.get("description") or "N/A"

            uc_text = f"Use Case ID: {uc_id}\n"
            uc_text += f"Use Case Name: {name}\n"
            uc_text += f"Description: {desc}\n"

            def format_field(field_data):
                if isinstance(field_data, list):
                    return "\n".join([f"- {item}" for item in field_data])
                return str(field_data) if field_data else "None"

            uc_text += f"Preconditions: {format_field(uc.get('preconditions'))}\n"
            uc_text += f"Postconditions: {format_field(uc.get('postconditions'))}\n"
            uc_text += f"Expected Results: {uc.get('expected_results', 'N/A')}\n"
            uc_text += f"Normal Flow:\n{format_field(uc.get('normal_flow'))}\n"
            uc_text += f"Alternative Flows:\n{format_field(uc.get('alternative_flows'))}\n"
            uc_text += f"Exceptions:\n{format_field(uc.get('exceptions'))}\n"

            extracted_use_cases.append({"id": uc_id, "text": uc_text.strip()})
    return extracted_use_cases


def parse_llm_response(response_text):
    """Parse the Markdown table returned by the LLM into records (verbatim logic)."""
    all_parsed_cases = []
    for line in response_text.split("\n"):
        row = line.strip()
        if row.count("|") < 2:
            continue
        if re.search(r"\|[:\s]*-+[:\s]*\|", row):
            continue
        header_pattern = r"^\|?\s*(ID|No\.?|Testcase\s*ID)\s*\|"
        if re.match(header_pattern, row, re.IGNORECASE) and "summary" in row.lower():
            continue
        columns = [col.strip() for col in row.split("|")]
        if columns and columns[0] == "":
            columns.pop(0)
        if columns and columns[-1] == "":
            columns.pop()
        if len(columns) >= 3:
            while len(columns) < 6:
                columns.append("")
            all_parsed_cases.append({
                "ID": columns[0],
                "summary description": columns[1],
                "Functionality/Condition to be tested": columns[2],
                "Input Action/Input Values": columns[3],
                "Expected Output/Behavior": columns[4],
                "Additional Comments": columns[5],
            })
    return all_parsed_cases


def run_experiment(doc_config, provider_name):
    input_path = os.path.join(BASE_DIR, doc_config["input_path"])
    output_path = os.path.join(BASE_DIR, doc_config["output_path"])
    project_name = doc_config["project_name"]
    doc_name = doc_config["name"]

    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    logger = ExperimentLogger(output_dir, doc_name, MODEL_NAME)
    logger.log(f"--- Starting test case generation for document: {doc_name} (provider={provider_name}) ---")
    logger.log(f"Input file: {input_path}")
    logger.log(f"Output file: {output_path}")

    try:
        chat = ChatProvider.create(provider_name, model=MODEL_NAME, generation_config=generation_config)
    except Exception as e:
        logger.log(f"Provider configuration error: {e}")
        return

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            raw_doc_content = json.dumps(json.load(f), indent=2, ensure_ascii=False)
    except Exception as e:
        logger.log(f"Error reading JSON file: {e}")
        return

    use_cases = extract_use_cases_from_json(input_path, logger)
    logger.log(f"Read document and extracted {len(use_cases)} use cases.")

    # Prompt 1 — Familiarization (verbatim)
    prompt1 = f"You are a software engineer. You are in the first stage of the Software Development Life Cycle, where you are provided with the System Requirements Specification (SRS) of a {project_name}. The SRS is provided below in triple quotes as a JSON document. Go through it, and you will refer to it for answering the questions in upcoming prompts.\nSRS (JSON): \"\"\"{raw_doc_content}\"\"\""

    logger.log("\nSending Prompt 1 (Familiarization)...")
    logger.start_module("familiarization")
    try:
        _, usage1 = chat.send_message(prompt1)
        logger.log_api_call(0, 0, usage1, "familiarization")
        logger.end_module("familiarization")
        logger.log("Model received and processed the SRS.")
    except Exception as e:
        logger.end_module("familiarization", "FAILED")
        logger.log(f"Error sending prompt 1: {e}")
        return

    all_test_cases = []
    for i, uc_obj in enumerate(use_cases):
        use_case_id = uc_obj["id"]
        use_case_text = uc_obj["text"]
        logger.log(f"\nProcessing Use Case {i+1}/{len(use_cases)}: {use_case_id}...")
        uc_module_name = f"use_case_{i+1}"
        logger.start_module(uc_module_name)

        # Prompt 2 — Test case generation (verbatim)
        prompt2 = f"Using the SRS of the {project_name} that was provided earlier, generate all possible test case designs, using Specification-Based technique, for each possible use case in a tabular format having the following 6 columns: ID, summary description, functionality/condition to be tested, input action/input values, expected output/behavior, and additional comments.\nUse case: \"{use_case_text}\""

        try:
            text, usage = chat.send_message(prompt2)
            logger.log_api_call(0, 0, usage, "test_case_generation")
            if not text:
                logger.log(f" -> Model returned no text for {use_case_id}.")
                logger.end_module(uc_module_name, "FAILED")
                continue
            parsed_data = parse_llm_response(text)
            for j, item in enumerate(parsed_data):
                tc_id_prefix = use_case_id.replace("UC-", "TC-") if use_case_id.startswith("UC-") else f"TC-{use_case_id}"
                testcase_id = f"{tc_id_prefix}-{j+1:02d}"
                all_test_cases.append({
                    "TestcaseId": testcase_id,
                    "UsecaseId": use_case_id,
                    **item,
                    "Source Use Case": use_case_text,
                })
            logger.log(f" -> Generated {len(parsed_data)} test cases for {use_case_id}.")
            logger.end_module(uc_module_name)
        except Exception as e:
            logger.log(f" -> Error calling API for {use_case_id}: {e}")
            logger.end_module(uc_module_name, "FAILED")
        time.sleep(2)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_test_cases, f, indent=4, ensure_ascii=False)
    logger.log(f"\n--- DOCUMENT {doc_name} COMPLETE ---")
    logger.log(f"Saved {len(all_test_cases)} test cases to '{output_path}'")
    logger.close()


def main():
    parser = argparse.ArgumentParser(description="Baseline 3 (Bhatia et al.) — conversational test case generation.")
    parser.add_argument("--provider", choices=["gemini", "deepseek"], default=None,
                        help="LLM provider (defaults to LLM_PROVIDER env var, then 'gemini').")
    args = parser.parse_args()
    provider_name = (args.provider or os.getenv("LLM_PROVIDER") or "gemini").lower()

    print(f"Starting experiment (provider={provider_name})...")
    for doc_config in DOCUMENTS_CONFIG:
        run_experiment(doc_config, provider_name)
    print("All documents processed.")


if __name__ == "__main__":
    main()
