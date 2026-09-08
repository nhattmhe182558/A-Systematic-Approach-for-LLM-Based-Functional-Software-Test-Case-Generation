"""
Baseline 1 — Augusto et al.
"Software System Testing assisted by Large Language Models: An Exploratory
Study" (ICTSS 2024).

Python port of the original Java replication package (``retorch-llm-rp``). The
original ran two Java scripts; this reproduces both stages and their VERBATIM
prompts, routed through a ``Provider`` so they run on Gemini or DeepSeek.

Two stages:
  RQ1 — Generate test SCENARIOS from the user requirements, using a
        Few-Shot + Chain-of-Thought prompt and a scenario example.
  RQ2 — Generate system test CASES. Scenario titles are extracted from the RQ1
        output; for each, a leave-one-out cross-validation is done over the
        example system test cases (split on "//TC", the example at index
        ``i % 5 + 1`` is removed), using a Few-Shot + CoT prompt.

Inputs (in ``input/``):
  inputUserRequirements_en.txt, inputTestScenarioExample.txt,
  inputTestScenarios.txt (RQ1 output, consumed by RQ2), inputSystemTestCases.txt.

Usage:
    python main.py --stage rq1 --provider gemini
    python main.py --stage rq2 --provider gemini
    python main.py --stage all --provider deepseek
"""

import os
import re
import argparse

from dotenv import load_dotenv

from provider import Provider
from logger_utils import ExperimentLogger

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DOCUMENT_NAME = "4LV"


# --------------------------------------------------------------------------
# resource loading (ports ExperimentationHelper)
# --------------------------------------------------------------------------
def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


def get_user_requirements() -> str:
    return _read(os.path.join(INPUT_DIR, "inputUserRequirements_en.txt"))


def get_test_scenario_example() -> str:
    return _read(os.path.join(INPUT_DIR, "inputTestScenarioExample.txt"))


def get_test_scenarios() -> str:
    return _read(os.path.join(INPUT_DIR, "inputTestScenarios.txt"))


def get_test_cases_cross_validation(pos: int) -> str:
    """Leave-one-out over examples split by '//TC' (verbatim logic)."""
    raw_test_cases = _read(os.path.join(INPUT_DIR, "inputSystemTestCases.txt")).split("//TC")
    content_list = list(raw_test_cases)
    if 0 <= pos < len(content_list):
        content_list.pop(pos)
    return "".join(content_list)


def put_output_to_file(sub_dir: str, name_prompt: str, output: str) -> None:
    directory = os.path.join(OUTPUT_DIR, sub_dir)
    os.makedirs(directory, exist_ok=True)
    sanitized = re.sub(r"[^a-zA-Z0-9.-]", "_", name_prompt)
    with open(os.path.join(directory, sanitized + ".txt"), "w", encoding="utf-8") as f:
        f.write(output)


# --------------------------------------------------------------------------
# RQ1 prompts (verbatim from RQ1Experimentation.java)
# --------------------------------------------------------------------------
def prompt_test_scenarios_few_shot(user_requirements: str, test_scenarios_examples: str) -> str:
    return ("I would like to generate test scenarios for system testing\n"
            + "I know that I need to fulfill the user requirements:\n \"\"\" " + user_requirements + "\"\"\",\n "
            + "Provide a complete sequence of steps for each scenario and the expected outputs. Don't write too long, but condense it a bit.\n"
            + "Fill in any missing steps\n"
            + "Identify any unnecessary steps.\n"
            + "Examples of a test scenario: \n \"\"\" " + test_scenarios_examples + " \"\"\" \n")


def prompt_test_scenarios_few_shot_cot(user_requirements: str, test_scenarios_examples: str) -> str:
    return ("Generate test scenarios based on the user requirements and examples provided.\n"
            + "Be concise and direct. Provide only the final test scenarios without extra explanations or step-by-step thinking.\n"
            + "Your output should be immediately usable.\n"
            + prompt_test_scenarios_few_shot(user_requirements, test_scenarios_examples))


# --------------------------------------------------------------------------
# RQ2 prompts (verbatim from RQ2Experimentation.java)
# --------------------------------------------------------------------------
def prompt_test_cases_few_shot(test_scenarios: str, examples: str, name_functionality: str) -> str:
    return ("When generating System test that covers \"\"\"" + name_functionality + "\"\"\" functionality.\n"
            + "Please consider the following test scenarios: :\n \"\"\" " + test_scenarios + " \"\"\" \n"
            + " and the following system test examples: \"\"\"" + examples + "\"\"\"\n"
            + "Don’t generate the whole test suite, only the required test case.")


def prompt_test_cases_few_shot_cot(test_scenarios: str, examples: str, name_functionality: str) -> str:
    return ("Let’s think step by step, describe the solution by breaking it down into a task list for then generate the code. \n"
            + prompt_test_cases_few_shot(test_scenarios, examples, name_functionality))


def load_test_scenarios_from_rq1_output() -> list:
    """Extract scenario titles from the RQ1 output (verbatim regex)."""
    all_scenarios = get_test_scenarios()
    pattern = re.compile(
        r"^(?:\*\*|#+\s*|Test Scenario\s*\d*:|Scenario:)\s*(.*?)(?:\*\*|\n|$)",
        re.MULTILINE | re.IGNORECASE,
    )
    titles = []
    for m in pattern.finditer(all_scenarios):
        title = m.group(1).strip()
        if title:
            titles.append(re.sub(r":$", "", title))
    return titles


# --------------------------------------------------------------------------
# stages
# --------------------------------------------------------------------------
def run_rq1(provider, logger):
    logger.log("--- RQ1: Generating test scenarios (Few-Shot + CoT) ---")
    logger.start_module("RQ1_GenerateTestScenarios")
    prompt = prompt_test_scenarios_few_shot_cot(get_user_requirements(), get_test_scenario_example())
    put_output_to_file("RQ1", "few-shot-CoT-prompt", prompt)
    try:
        text, usage = provider.generate(prompt)
        logger.log_api_call(usage, "RQ1_GenerateTestScenarios")
        put_output_to_file("RQ1", "RQ1_GenerateTestScenarios", text)
        logger.end_module("RQ1_GenerateTestScenarios")
        logger.log("RQ1 complete. NOTE: copy the chosen scenarios into input/inputTestScenarios.txt before running RQ2.")
    except Exception as e:  # noqa: BLE001
        logger.end_module("RQ1_GenerateTestScenarios", "FAILED")
        logger.log(f"RQ1 error: {e}")


def run_rq2(provider, logger):
    logger.log("--- RQ2: Generating system test cases (Few-Shot + CoT) ---")
    test_cases = load_test_scenarios_from_rq1_output()
    logger.log(f"Loaded {len(test_cases)} scenario titles from RQ1 output.")
    test_scenarios = get_test_scenarios()
    for i, test_case_required in enumerate(test_cases):
        cross_validation_index = (i % 5) + 1  # cycles 1..5
        module = f"RQ2_{test_case_required}"
        logger.start_module(module)
        examples = get_test_cases_cross_validation(cross_validation_index)
        prompt = prompt_test_cases_few_shot_cot(test_scenarios, examples, test_case_required)
        put_output_to_file("RQ2", "few-shot-prompt-cot-" + test_case_required, prompt)
        try:
            text, usage = provider.generate(prompt)
            logger.log_api_call(usage, module)
            put_output_to_file("RQ2", module.replace("-", "_"), text)
            logger.end_module(module)
            logger.log(f" -> Generated test case for '{test_case_required}'.")
        except Exception as e:  # noqa: BLE001
            logger.end_module(module, "FAILED")
            logger.log(f" -> Error for '{test_case_required}': {e}")


def main():
    parser = argparse.ArgumentParser(description="Baseline 1 (Augusto et al.) — scenario + test case generation.")
    parser.add_argument("--stage", choices=["rq1", "rq2", "all"], default="all",
                        help="Which stage to run.")
    parser.add_argument("--provider", choices=["gemini", "deepseek"], default=None,
                        help="LLM provider (defaults to LLM_PROVIDER env var, then 'gemini').")
    args = parser.parse_args()
    provider_name = (args.provider or os.getenv("LLM_PROVIDER") or "gemini").lower()

    logger = ExperimentLogger(OUTPUT_DIR, DOCUMENT_NAME, MODEL_NAME)
    provider = Provider.create(provider_name, model=MODEL_NAME)

    if args.stage in ("rq1", "all"):
        run_rq1(provider, logger)
    if args.stage in ("rq2", "all"):
        run_rq2(provider, logger)

    logger.close()
    print("=" * 70)
    print("Baseline 1 experimentation complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
