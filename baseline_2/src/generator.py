"""
generator.py (Baseline 2 — Milchevski et al.)
=============================================

Faithful port of the original ``src/generator.TestGenerationSystem``. Same
method names and multi-step agentic logic (test design → scenarios → purposes →
generation agent → reflection agent), with the two Gemini models replaced by a
``Provider`` (Gemini or DeepSeek) exposing ``generate_text`` / ``generate_json``.
"""

import json
import re
import time

from . import config
from . import prompts
from . import utils
from provider import Provider


def _parse_json_from_response(text: str) -> dict:
    """Extract and parse a JSON object from the LLM response (verbatim logic)."""
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if match:
        text = match.group(1)
    text = text.replace('\\', '\\\\').replace('\\\\n', '\\n').replace('\\\\t', '\\t').replace('\\\\"', '\\"').replace('\\\\r', '\\r')
    return json.loads(text)


class TestGenerationSystem:
    """Full generation system including Generation and Reflection agents."""

    def __init__(self, provider=None, logger=None):
        self.logger = logger
        self.provider = provider or Provider.create(
            config.LLM_PROVIDER,
            model_text=config.GENERATION_MODEL_TEXT,
            model_json=config.GENERATION_MODEL_JSON,
        )

    def _log(self, usage, module_name):
        if self.logger:
            self.logger.log_api_call(usage, module_name)

    def generate_test_design(self, requirements, technique="Decision Table") -> str:
        """Step 3a: generate the Test Design as a Markdown table."""
        prompt = prompts.create_prompt_for_test_design(requirements, technique)
        text, usage = self.provider.generate_text(prompt)
        self._log(usage, "test_design_generator")
        return text

    def extract_test_scenarios(self, markdown_table: str) -> list:
        """Step 3b: extract Test Scenarios from the Markdown table."""
        headers, records = utils._parse_markdown_table_to_records(markdown_table)
        return records

    def generate_test_purposes(self, requirements, scenarios) -> list:
        """Step 3c: generate a Test Purpose per scenario."""
        if not scenarios:
            return []
        prompt = prompts.create_prompt_for_test_purposes(requirements, scenarios)
        text, usage = self.provider.generate_text(prompt)
        self._log(usage, "test_purpose_generator")
        cleaned_purposes = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if line and line[0].isdigit() and ". " in line:
                cleaned_purposes.append(line.split(". ", 1)[-1])
        return cleaned_purposes

    def generate_initial_test_spec(self, requirements, test_purpose, test_scenario, few_shot_examples) -> dict:
        """Step 4a: Generation Agent produces the initial Test Specification."""
        prompt = prompts.create_prompt_for_test_specification(
            test_purpose, test_scenario, requirements, few_shot_examples
        )
        for attempt in range(3):
            try:
                text, usage = self.provider.generate_json(prompt)
                self._log(usage, "generation_agent")
                return _parse_json_from_response(text)
            except (json.JSONDecodeError, AttributeError, ValueError) as e:
                print(f"  JSON parse error (attempt {attempt + 1}): {e}. Retrying in 2s...")
                time.sleep(2)
            except Exception as e:  # noqa: BLE001
                print(f"  Unknown error creating Test Spec (attempt {attempt + 1}): {e}. Retrying in 2s...")
                time.sleep(2)
        print("ERROR: Could not create a valid Test Spec after 3 attempts.")
        raise ValueError("Could not create a valid Test Spec from the API.")

    def extract_requirements_with_ai(self, raw_doc_content: str, rules: str) -> list:
        """Optional: use the model to extract User Requirements from raw content."""
        prompt = prompts.create_prompt_for_requirement_extraction(raw_doc_content, rules)
        text, usage = self.provider.generate_text(prompt)
        self._log(usage, "requirement_extractor")
        requirements = []
        for line in text.split("\n"):
            line = line.strip()
            if line and line[0].isdigit() and ". " in line:
                requirements.append(line.split(". ", 1)[1])
            elif line:
                requirements.append(line)
        return sorted(list(set(requirements)))

    def refine_test_spec(self, requirements, initial_spec) -> dict:
        """Step 4b: Reflection Agent reviews and improves the Test Specification."""
        prompt = prompts.create_prompt_for_reflection(requirements, initial_spec)
        for attempt in range(3):
            try:
                text, usage = self.provider.generate_json(prompt)
                self._log(usage, "reflection_agent")
                return _parse_json_from_response(text)
            except (json.JSONDecodeError, AttributeError, ValueError) as e:
                print(f"  JSON parse error (attempt {attempt + 1}): {e}. Retrying in 2s...")
                time.sleep(2)
            except Exception as e:  # noqa: BLE001
                print(f"  Unknown error refining Test Spec (attempt {attempt + 1}): {e}. Retrying in 2s...")
                time.sleep(2)
        print("ERROR: Could not refine a valid Test Spec after 3 attempts.")
        raise ValueError("Could not refine a valid Test Spec from the API.")
