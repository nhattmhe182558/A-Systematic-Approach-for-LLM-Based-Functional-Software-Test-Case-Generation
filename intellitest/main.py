"""
main.py
=======

Faithful port of the original IntelliTest ``llm_functional_test`` pipeline.

Each original module under ``back_end/cores/modules`` is reproduced here as a
class with the same method names and logic:

  * ``extract_all_screens``          (utils/screen_utils.py)
  * ``BusinessProcessDetector``      (modules/business_process_detector.py)
  * ``ScreenGraphDetector``          (modules/screen_graph_detector.py)
  * ``ScreenVariableDetector``       (modules/screen_variable_detector.py)
  * ``PathProcessor``                (modules/path_processor.py)
  * ``PairwiseGenerator``            (modules/pairwise_generator.py)
  * ``TestCaseGenerator``            (modules/test_case_generator.py)
  * ``TestCaseRetry``                (modules/test_case_retry.py)
  * ``MutationTestCaseGenerator``    (modules/mutation_test_case_generator.py)

The ONLY structural change versus the original is that every direct
``client.models.generate_content(...)`` call is routed through an
``LLMProvider`` (``models.LLMProvider``) so the identical pipeline runs on
Gemini or DeepSeek. Constants come from ``config.py`` (== the original
``variables.py``).

The runner always executes the full end-to-end pipeline (all 8 notebook steps).

Usage:
    python main.py --pdf input/spec.pdf --provider gemini
    python main.py --pdf input/spec.pdf --provider deepseek
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from allpairspy import AllPairs

import config
import prompts as prompt_storing
from models import (
    BFSGraph,
    BusinessProcesses,
    GeneratedTestCases,
    LLMProvider,
    ScreenFlowGraph,
    ScreenList,
    ScreenVariablesResponse,
    TestCase,
    ThreadSafeContextUpdater,
    ThreadSafeCounter,
    ThreadSafeFileWriter,
    ThreadSafeGraphWriter,
    build_graph_from_screen_graph,
    calculate_gemini_cost,
    extract_gemini_metadata,
    find_json_files,
    find_path_between_screens,
    load_json_file,
    process_test_case_batch_with_threads,
)


# ===========================================================================
# screen extraction (utils/screen_utils.extract_all_screens)
# ===========================================================================
def extract_all_screens(provider: LLMProvider) -> Optional[ScreenList]:
    """Extract all screens from the document and save to screens.json."""
    try:
        print("Extracting all screens from document...")
        parsed_screens = provider.generate_structured(
            prompt_storing.extract_all_screens_prompt, ScreenList, module_name="screen_extraction"
        )
        if not parsed_screens:
            print("Error extracting screens: no response")
            return None
        print(f"Found {len(parsed_screens.screens)} unique screens")
        screens_output_path = config.GENERAL_OUTPUT_DIRECTORY / "screens.json"
        screens_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(screens_output_path, "w", encoding="utf-8") as f:
            json.dump(parsed_screens.model_dump(), f, ensure_ascii=False, indent=4)
        print(f"Screens saved to {screens_output_path}")
        return parsed_screens
    except Exception as e:  # noqa: BLE001
        print(f"Error extracting screens: {e}")
        return None


# ===========================================================================
# BusinessProcessDetector (modules/business_process_detector.py)
# ===========================================================================
class BusinessProcessDetector:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.model_name = config.MODEL_FLASH_NAME

    def _log_prompt(self, prompt: str, process_name: str = "business_process"):
        log_dir = config.DOCUMENT_OUTPUT_PATH / "logs" / "business_process_prompts"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{process_name}_prompt.txt"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"Prompt logged to {log_file}")

    def extract_business_processes(self, pdf_path: str):
        try:
            # document already prepared by the provider (PDF text extracted)
            print("Extracting all screens for prompt constraint...")
            screens_data = extract_all_screens(self.provider)
            if not screens_data:
                print("Could not extract screens. Proceeding without screen constraints.")
                screen_names = []
            else:
                screen_names = [screen.screen_name for screen in screens_data.screens]

            screens_list_str = "\n".join([f"- {name}" for name in screen_names])
            prompt_with_screens = prompt_storing.gen_business_process_prompt.replace(
                "{screens_list}", screens_list_str
            )
            self._log_prompt(prompt_with_screens, "business_process_generation")

            print("Generating content from the model...")
            parsed_processes = self.provider.generate_structured(
                prompt_with_screens, BusinessProcesses, module_name="business_process_detector"
            )
            if not parsed_processes:
                raise Exception("Business process generation returned no result")
            self._save_processes(parsed_processes)
        except Exception as e:  # noqa: BLE001
            print(f"An error occurred during business process extraction: {e}")
            raise

    def _save_processes(self, parsed_processes: BusinessProcesses):
        print("Saving business processes to files...")
        output_dir = config.GENERAL_OUTPUT_DIRECTORY
        output_dir.mkdir(parents=True, exist_ok=True)
        for i, process in enumerate(parsed_processes.business_processes):
            for step_idx, step in enumerate(process.steps):
                step.step_id = step_idx + 1
            file_path = output_dir / f"business_process_{i+1}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(process.model_dump(), f, ensure_ascii=False, indent=4)
            print(f"Saved {file_path}")


# ===========================================================================
# ScreenGraphDetector (modules/screen_graph_detector.py)
# ===========================================================================
class ScreenGraphDetector:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.model_name = config.MODEL_FLASH_NAME

    def _log_prompt(self, prompt: str, screen_name: str):
        log_dir = config.DOCUMENT_OUTPUT_PATH / "logs" / "screen_graph_prompts"
        log_dir.mkdir(parents=True, exist_ok=True)
        safe_screen_name = screen_name.replace(" ", "_").replace(".", "_").replace("/", "_").replace(":", "_")
        log_file = log_dir / f"{safe_screen_name}_graph_prompt.txt"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"Prompt logged to {log_file}")

    def _call_llm_for_graph_chunk(self, prompt: str, screen_name: str) -> Optional[ScreenFlowGraph]:
        result = self.provider.generate_structured(prompt, ScreenFlowGraph, module_name="screen_graph_detector")
        if result:
            print(f"  ✅ Successfully generated content for screen: {screen_name}")
        else:
            print(f"  ❌ Warning: LLM call failed for screen '{screen_name}'.")
        return result

    def _process_screen(self, screen_name: str) -> Optional[ScreenFlowGraph]:
        print(f"--- Processing screen: {screen_name} ---")
        prompt = prompt_storing.gen_screen_graph_prompt.replace("{screens_list}", f"- {screen_name}")
        self._log_prompt(prompt, screen_name)
        graph_chunk = self._call_llm_for_graph_chunk(prompt, screen_name)
        if graph_chunk:
            print(f"  📊 Received chunk with {len(graph_chunk.nodes)} nodes and {len(graph_chunk.edges)} edges.")
        return graph_chunk

    def generate_screen_graph(self):
        screens_output_path = config.GENERAL_OUTPUT_DIRECTORY / "screens.json"
        try:
            with open(screens_output_path, "r", encoding="utf-8") as f:
                screens_json = json.load(f)
            screen_names = [screen["screen_name"] for screen in screens_json["screens"]]
            print(f"Step 1: Loaded {len(screen_names)} screens for graph generation.")
        except Exception as e:  # noqa: BLE001
            print(f"Error loading screens.json: {e}")
            return

        output_path = config.SCREEN_GRAPH_OUTPUT_PATH
        graph_writer = ThreadSafeGraphWriter(output_path)
        graph_writer.initialize_file()

        max_workers = config.SCREEN_GRAPH_MAX_WORKERS
        print(f"\nStep 2: Starting parallel processing with {max_workers} threads...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_screen = {executor.submit(self._process_screen, name): name for name in screen_names}
            for future in as_completed(future_to_screen):
                screen_name = future_to_screen[future]
                try:
                    result = future.result()
                    if result:
                        graph_writer.write_graph_chunk(result)
                except Exception as exc:  # noqa: BLE001
                    print(f"  ❌ Error processing screen '{screen_name}': {exc}")
        print("\nScreen graph generation completed successfully.")


# ===========================================================================
# ScreenVariableDetector (modules/screen_variable_detector.py)
# ===========================================================================
import threading  # noqa: E402  (kept near the class that uses it, mirroring original)


class ScreenVariableDetector:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.model_name = config.MODEL_FLASH_NAME
        self.lock = threading.Lock()
        self.total_cost = 0.0
        self.total_tokens = 0
        self.request_count = 0

    def _log_prompt(self, prompt: str, uc_id: str, screen_name: str):
        log_dir = config.DOCUMENT_OUTPUT_PATH / "logs" / "screen_variable_prompts"
        log_dir.mkdir(parents=True, exist_ok=True)
        safe_uc_id = uc_id.replace(" ", "_").replace(".", "_").replace("/", "_").replace(":", "_")
        safe_screen_name = screen_name.replace(" ", "_").replace(".", "_").replace("/", "_").replace(":", "_")
        log_file = log_dir / f"{safe_uc_id}_{safe_screen_name}_prompt.txt"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"Prompt logged to {log_file}")

    def _load_business_processes(self):
        bp_path = config.BUSINESS_PROCESS_OUTPUT_PATH
        bp_files = find_json_files(bp_path)
        business_processes = []
        for bp_file in bp_files:
            try:
                with open(bp_file, "r", encoding="utf-8") as f:
                    business_processes.append(json.load(f))
            except Exception as e:  # noqa: BLE001
                print(f"Error loading business process file {bp_file}: {e}")
        return business_processes

    def generate_screen_variables(self):
        business_processes = self._load_business_processes()
        if not business_processes:
            print("No business processes found. Exiting.")
            return
        print(f"Loaded {len(business_processes)} business processes.")

        screen_contexts = {}
        for bp_file in find_json_files(config.BUSINESS_PROCESS_OUTPUT_PATH):
            bp_name = bp_file.stem
            bp_data = load_json_file(bp_file)
            if not bp_data:
                continue
            for step in bp_data.get("steps", []):
                screen_name = step.get("current_screen")
                if screen_name:
                    screen_contexts.setdefault(screen_name, []).append(
                        {"uc_id": step.get("uc_id"), "description": step.get("description"), "bp_name": bp_name}
                    )

        full_response = ScreenVariablesResponse(screens=[])
        processed_screens = {}

        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            future_to_screen = {
                executor.submit(self._process_screen_context, screen_name, contexts, processed_screens, full_response): screen_name
                for screen_name, contexts in screen_contexts.items()
            }
            for future in as_completed(future_to_screen):
                screen_name = future_to_screen[future]
                try:
                    future.result()
                except Exception as exc:  # noqa: BLE001
                    print(f"{screen_name} generated an exception: {exc}")

        print("All screen processing tasks completed. Final variables saved.")

    def _process_screen_context(self, screen_name, contexts, processed_screens, full_response):
        context_str = "\n".join([
            f"Context from {c['bp_name']}:\n- UC ID: {c['uc_id']}\n  Step Description: {c['description']}"
            for c in contexts
        ])
        prompt = prompt_storing.gen_screen_variables_prompt.format(current_screen=screen_name, contexts=context_str)
        self._log_prompt(prompt, "GROUPED", screen_name)
        print(f"Requesting variables for screen: {screen_name} with {len(contexts)} contexts...")

        data_chunk = self.provider.generate_structured(
            prompt, ScreenVariablesResponse, module_name="screen_variable_detector"
        )
        if data_chunk:
            with self.lock:
                self.request_count += 1
            with self.lock:
                for screen in data_chunk.screens:
                    if screen.screen_name == screen_name:
                        processed_screens[screen_name] = screen
                        print(f"Screen '{screen_name}' has been processed and updated.")
                    else:
                        print(f"Warning: LLM returned screen '{screen.screen_name}' which does not match '{screen_name}'.")
                full_response.screens = list(processed_screens.values())
                self._save_variables(full_response)
        else:
            print(f"No valid response returned for {screen_name}.")

    def _save_variables(self, data: ScreenVariablesResponse):
        output_path = config.SCREEN_VARIABLES_OUTPUT_PATH
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            print(f"Saving screen variables to {output_path}...")
            print(f"Total screens: {len(data.screens)}")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data.model_dump(), f, ensure_ascii=False, indent=4)
            print("Screen variables saved successfully.")
        except Exception as e:  # noqa: BLE001
            print(f"Error saving screen variables: {e}")
            raise


# ===========================================================================
# PathProcessor (modules/path_processor.py)  — no LLM, verbatim logic
# ===========================================================================
class PathProcessor:
    def __init__(self):
        self.screen_graph_file = config.SCREEN_GRAPH_OUTPUT_PATH
        self.business_process_dir = config.GENERAL_OUTPUT_DIRECTORY
        self.output_dir = config.PATH_OUTPUT_DIRECTORY

    def load_screen_graph(self) -> Dict[str, Any]:
        with open(self.screen_graph_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded screen graph from {self.screen_graph_file}")
        return data

    def load_business_process(self, file_path: Path) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded business process from {file_path}")
        return data

    def find_business_process_files(self) -> List[Path]:
        business_process_files = list(self.business_process_dir.glob("business_process_*.json"))
        business_process_files.sort(key=lambda x: int(x.stem.split("_")[-1]))
        print(f"Found {len(business_process_files)} business process files")
        return business_process_files

    def generate_paths_for_business_process(self, business_process: Dict[str, Any], graph: BFSGraph,
                                            screen_graph_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        steps = business_process.get("steps", [])
        paths = []
        print(f"🔄 Generating {len(steps)} paths with flow continuity...")
        for i, step in enumerate(steps):
            path_id = i + 1
            step_id = step.get("step_id", path_id)
            current_screen = step.get("current_screen", "")
            next_screen = step.get("next_screen", "")
            step_action = step.get("step", "")
            step_description = step.get("description", "")
            step_element = step.get("element", "UI Element")
            current_role = step.get("role")

            if i == 0:
                path_start_screen = current_screen
                print(f"\n📍 Creating Path {path_id} (FIRST) for Step {step_id}")
            else:
                path_start_screen = paths[-1]["end_screen"]
                print(f"\n📍 Creating Path {path_id} for Step {step_id}")
                print(f"   Flow continuity: start_screen = '{path_start_screen}' (from previous path's end)")

            print(f"   Path: '{path_start_screen}' (start) → '{next_screen}' (end)")
            print(f"   Business action on '{current_screen}': '{step_action}'")

            if current_role:
                print(f"   Role-based filtering: '{current_role}'")
            navigation_steps = find_path_between_screens(graph, path_start_screen, current_screen, current_role)

            complete_path_steps = []
            if path_start_screen == current_screen:
                print(f"   ✅ No navigation needed (already at '{current_screen}')")
            elif navigation_steps is not None and len(navigation_steps) > 0:
                print(f"   ✅ Found navigation path with {len(navigation_steps)} steps")
                complete_path_steps.extend(navigation_steps)
            elif path_start_screen != current_screen:
                print(f"   ❌ No navigation path found from '{path_start_screen}' to '{current_screen}'")
                complete_path_steps.append({
                    "source": path_start_screen, "target": current_screen,
                    "action": f"Navigate to {current_screen}", "element": "Unknown Element",
                    "error": "No navigation path found in screen graph",
                })

            path_obj = {
                "path_id": path_id, "step_id": step_id, "start_screen": path_start_screen,
                "end_screen": next_screen, "total_steps": len(complete_path_steps),
                "description": step_description, "business_action": step_action,
                "business_element": step_element, "steps": complete_path_steps,
            }
            paths.append(path_obj)
            print(f"   ✅ Path {path_id} created: {path_obj['total_steps']} step(s)")
        print(f"\n🎯 Successfully generated {len(paths)} paths")
        return paths

    def process_single_business_process(self, business_process_file: Path, graph: BFSGraph,
                                        screen_graph_data: Dict[str, Any]) -> Optional[str]:
        try:
            business_process = self.load_business_process(business_process_file)
            paths = self.generate_paths_for_business_process(business_process, graph, screen_graph_data)
            output_data = {
                "business_process_name": business_process.get("process_name", ""),
                "business_process_description": business_process.get("process_description", ""),
                "total_paths": len(paths), "paths": paths,
            }
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_filename = f"path_{business_process_file.stem}.json"
            output_path = self.output_dir / output_filename
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
            print(f"✅ Generated path file: {output_path}")
            return str(output_path)
        except Exception as e:  # noqa: BLE001
            print(f"❌ Error processing {business_process_file}: {e}")
            return None

    def process_all_business_processes(self):
        screen_graph_data = self.load_screen_graph()
        graph = build_graph_from_screen_graph(screen_graph_data)
        print(f"Built graph with {len(graph.get_all_screens())} screens")
        business_process_files = self.find_business_process_files()
        if not business_process_files:
            print("No business process files found")
            return []
        generated_files = []
        for business_process_file in business_process_files:
            print(f"\n{'='*50}\nPROCESSING: {business_process_file.name}\n{'='*50}")
            output_path = self.process_single_business_process(business_process_file, graph, screen_graph_data)
            if output_path:
                generated_files.append(output_path)
        print(f"\n✅ Successfully generated {len(generated_files)} path files")
        return generated_files



# ===========================================================================
# PairwiseGenerator (modules/pairwise_generator.py) — no LLM, verbatim logic
# ===========================================================================
class PairwiseGenerator:
    def __init__(self):
        self.processed_group_ids = set()

    def _sanitize_name(self, name: str) -> str:
        name = re.sub(r"\s+", "_", name)
        name = name.replace(".", "_")
        name = re.sub(r'[<>:"/\\|?*]', "_", name)
        return name

    def _load_json(self, file_path: Path) -> Any:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading or parsing {file_path}: {e}")
            return None

    def run(self, use_business_process_grouping=True):
        screen_vars_path = config.SCREEN_VARIABLES_OUTPUT_PATH
        if not screen_vars_path.exists():
            logging.error(f"screen_variables.json not found at {screen_vars_path}")
            return
        screen_variables = self._load_json(screen_vars_path)
        if not screen_variables:
            logging.error("Failed to load screen_variables.json")
            return
        doc_output_path = config.DOCUMENT_OUTPUT_PATH
        if use_business_process_grouping:
            self._generate_combinations_by_business_process(screen_variables, doc_output_path)
        else:
            self._generate_combinations_for_all_groups(screen_variables, doc_output_path)

    def _generate_combinations_by_business_process(self, screen_variables, doc_output_path):
        logging.info("\n🔄 Starting business process and screen-based pairwise generation...")
        business_process_screen_params = self._group_parameters_by_business_process_and_screen(screen_variables)
        if not business_process_screen_params:
            logging.warning("No business process groupings found")
            return
        for process_name, screens_data in business_process_screen_params.items():
            logging.info(f"\n📋 Processing Business Process: {process_name}")
            for screen_name, use_cases_data in screens_data.items():
                for use_case_id, use_case_data in use_cases_data.items():
                    self._create_pairwise_for_business_process_screen(
                        process_name, screen_name, use_case_data, doc_output_path, use_case_id
                    )
        logging.info("\n✅ Business process and screen-based pairwise generation complete!")

    def _group_parameters_by_business_process_and_screen(self, screen_variables):
        business_process_screen_params = {}
        for screen in screen_variables.get("screens", []):
            screen_name = screen.get("screen_name")
            for layer in screen.get("layers", []):
                layer_level = layer.get("layer_level", 0)
                trigger_element = layer.get("trigger_element")
                for group in layer.get("element_groups", []):
                    group_name = group.get("group_name")
                    belong_to = group.get("belong_to", "")
                    use_case_id = group.get("use_case_id", "UNKNOWN")
                    if belong_to:
                        for process_name in [name.strip() for name in belong_to.split(",")]:
                            business_process_screen_params.setdefault(process_name, {})
                            business_process_screen_params[process_name].setdefault(screen_name, {})
                            if use_case_id not in business_process_screen_params[process_name][screen_name]:
                                business_process_screen_params[process_name][screen_name][use_case_id] = {
                                    "parameters": [], "groups": []
                                }
                            group_info = {"group_name": group_name, "layer_level": layer_level,
                                          "trigger_element": trigger_element, "use_case_id": use_case_id}
                            business_process_screen_params[process_name][screen_name][use_case_id]["groups"].append(group_info)
                            for param in group.get("parameters", []):
                                enriched_param = param.copy()
                                enriched_param["source_screen"] = screen_name
                                enriched_param["source_group"] = group_name
                                enriched_param["layer_level"] = layer_level
                                enriched_param["trigger_element"] = trigger_element
                                enriched_param["use_case_id"] = use_case_id
                                business_process_screen_params[process_name][screen_name][use_case_id]["parameters"].append(enriched_param)
        return business_process_screen_params

    def _create_pairwise_for_business_process_screen(self, process_name, screen_name, screen_data,
                                                     doc_output_path, use_case_id=None):
        all_parameters = screen_data["parameters"]
        params_with_data = [
            p for p in all_parameters
            if p.get("test_data", {}).get("valid_values") or p.get("test_data", {}).get("invalid_values")
        ]
        if not params_with_data:
            logging.info(f"      └── No parameters with test data for screen '{screen_name}' (UC: {use_case_id}). Skipping.")
            return
        self._write_business_process_screen_pairwise_csv(
            process_name, screen_name, params_with_data, screen_data, doc_output_path, use_case_id
        )

    def _write_business_process_screen_pairwise_csv(self, process_name, screen_name, params,
                                                    screen_data, doc_output_path, use_case_id=None):
        param_names = []
        param_values = []
        for param in params:
            source_group = param.get("source_group", "Unknown")
            element_name = param.get("element_name", "Unknown")
            unique_name = f"{source_group}_{element_name}"
            param_names.append(unique_name)
            test_data = param.get("test_data", {})
            combined = test_data.get("valid_values", []) + test_data.get("invalid_values", [])
            param_values.append(combined if combined else [None])

        filtered_params = [(name, values) for name, values in zip(param_names, param_values)
                           if values != [None] and values]
        if not filtered_params:
            logging.warning(f"No parameters with concrete test data for screen '{screen_name}' in '{process_name}'. Skipping.")
            return
        filtered_names, filtered_values = zip(*filtered_params)

        if len(filtered_values) == 1:
            test_cases = [{filtered_names[0]: val} for val in filtered_values[0]]
        else:
            try:
                all_pairs = AllPairs(list(filtered_values))
                test_cases = [dict(zip(filtered_names, pair)) for pair in all_pairs]
            except Exception as e:  # noqa: BLE001
                logging.error(f"Error during AllPairs generation for screen '{screen_name}': {e}")
                return

        header = list(param_names) + ["outcome", "business_process", "screen", "use_case_id", "groups_involved"]
        rows = []
        groups_involved = ", ".join([g["group_name"] for g in screen_data.get("groups", [])])
        for case in test_cases:
            row_data = {name: case.get(name) for name in param_names}
            has_invalid = False
            for param in params:
                source_group = param.get("source_group", "Unknown")
                element_name = param.get("element_name", "Unknown")
                unique_name = f"{source_group}_{element_name}"
                if unique_name in case:
                    invalid_values = param.get("test_data", {}).get("invalid_values", [])
                    if case[unique_name] in invalid_values:
                        has_invalid = True
                        break
            row_data["outcome"] = "False" if has_invalid else "True"
            row_data["business_process"] = process_name
            row_data["screen"] = screen_name
            row_data["use_case_id"] = use_case_id if use_case_id else "UNKNOWN"
            row_data["groups_involved"] = groups_involved
            rows.append(row_data)

        safe_process_name = self._sanitize_name(process_name)
        safe_screen_name = self._sanitize_name(screen_name)
        safe_use_case_id = self._sanitize_name(use_case_id) if use_case_id else "UNKNOWN"
        output_dir = doc_output_path / "pairwise" / safe_process_name
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{safe_screen_name}_{safe_use_case_id}.csv"
        try:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
                writer.writerows(rows)
            logging.info(f"      └── Successfully saved to {output_path}")
            logging.info(f"      └── Generated {len(test_cases)} test combinations")
        except IOError as e:
            logging.error(f"Error writing screen CSV to {output_path}: {e}")



# ===========================================================================
# TestCaseGenerator (modules/test_case_generator.py) — full dedup engine
# ===========================================================================
class TestCaseGenerator:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.model_name = config.MODEL_FLASH_NAME
        self.general_output_dir = config.GENERAL_OUTPUT_DIRECTORY
        self.pairwise_dir = config.PAIRWISE_OUTPUT_DIRECTORY
        self.path_dir = config.PATH_OUTPUT_DIRECTORY
        self.testcase_dir = config.TESTCASE_OUTPUT_DIRECTORY
        self.prompt_dir = self.general_output_dir.parent / "logs" / "test_case_prompts"
        self.context_file = self.general_output_dir / "test_case_context.json"

        # Load input data (cores/input_data.json in the original; optional here)
        input_data_path = config.PROJECT_ROOT / "input_data.json"
        raw_input_data = load_json_file(input_data_path) if input_data_path.exists() else {}
        self.input_data = (raw_input_data or {}).get("TestCaseInputData", [])

        self.test_case_id_counter = ThreadSafeCounter(start_value=1)
        self.prompt_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_name(self, name: str) -> str:
        name = re.sub(r"\s+", "_", name)
        name = name.replace(".", "_")
        name = re.sub(r'[<>:"/\\|?*]', "_", name)
        return name

    def _log_failed_test_case(self, output_dir: Path, step_id: int, screen_name: str, row_index: int,
                              error, test_case_id: str = None, csv_file_name: str = None,
                              matched_group: Dict[str, Any] = None):
        try:
            failed_dir = output_dir / "failed"
            failed_dir.mkdir(parents=True, exist_ok=True)
            failed_filename = failed_dir / f"failed_TC-{step_id:003}.json"
            failure_data = {
                "step_id": step_id, "screen_name": screen_name, "row_index": row_index,
                "error_message": str(error), "test_case_id": test_case_id,
                "csv_file_name": csv_file_name, "matched_group": matched_group,
            }
            existing_failed_cases = []
            if failed_filename.exists():
                with open(failed_filename, "r", encoding="utf-8") as f:
                    try:
                        existing_failed_cases = json.load(f)
                    except json.JSONDecodeError:
                        existing_failed_cases = []
            existing_failed_cases.append(failure_data)
            with open(failed_filename, "w", encoding="utf-8") as f:
                json.dump(existing_failed_cases, f, indent=2)
            print(f"    - ❌ Logged failed test case to {failed_filename} (total: {len(existing_failed_cases)})")
        except Exception as e:  # noqa: BLE001
            print(f"    - ❌ Error logging failed test case: {e}")

    def _get_screen_variables_for_business_process(self, screen_name, business_flow_id, screen_vars_data):
        if not screen_vars_data:
            return None
        target_business_process = f"business_process_{business_flow_id}"
        for screen in screen_vars_data.get("screens", []):
            if screen.get("screen_name") == screen_name:
                matching_groups = []
                for layer in screen.get("layers", []):
                    for group in layer.get("element_groups", []):
                        if group.get("belong_to", "") == target_business_process:
                            matching_groups.append(group)
                if matching_groups:
                    return {"screen_name": screen_name, "business_process": target_business_process,
                            "groups": matching_groups}
        return None

    def _check_if_uc_has_parameters(self, screen_name, uc_id, screen_vars_data):
        if not screen_vars_data or not uc_id:
            return False
        for screen in screen_vars_data.get("screens", []):
            if screen.get("screen_name") == screen_name:
                total_params = 0
                groups_found = 0
                for layer in screen.get("layers", []):
                    for group in layer.get("element_groups", []):
                        if group.get("use_case_id", "") == uc_id:
                            groups_found += 1
                            total_params += len(group.get("parameters", []))
                if groups_found > 0:
                    has_parameters = total_params > 0
                    if not has_parameters:
                        print(f"    - ℹ️  UC '{uc_id}' has NO parameters across {groups_found} group(s) - will skip CSV")
                    else:
                        print(f"    - ✅ UC '{uc_id}' has {total_params} parameter(s) across {groups_found} group(s) - will use CSV")
                    return has_parameters
        print(f"    - ⚠️  UC '{uc_id}' not found in screen_variables for '{screen_name}' - assuming it has parameters")
        return True

    def _find_matching_csv_files(self, step_info, screen_name, business_flow_id, uc_id=None):
        business_process_name = f"business_process_{business_flow_id}"
        business_process_dir = self.pairwise_dir / business_process_name
        if not business_process_dir.exists():
            print(f"    - ❌ Error: Business process directory not found '{business_process_name}'.")
            return []
        safe_screen_name = self._sanitize_name(screen_name)
        safe_uc_id = self._sanitize_name(uc_id) if uc_id else None
        if safe_uc_id:
            screen_csv_file = business_process_dir / f"{safe_screen_name}_{safe_uc_id}.csv"
            if screen_csv_file.exists():
                print(f"    - ✅ Found screen CSV file (exact UC match): {screen_csv_file.name}")
                return [screen_csv_file]
        matching_files = list(business_process_dir.glob(f"{safe_screen_name}_UC*.csv"))
        if matching_files:
            print(f"    - ✅ Found screen CSV file (different UC): {matching_files[0].name}")
            return [matching_files[0]]
        screen_csv_file = business_process_dir / f"{safe_screen_name}.csv"
        if screen_csv_file.exists():
            print(f"    - ✅ Found screen CSV file (legacy format): {screen_csv_file.name}")
            return [screen_csv_file]
        print(f"    - ❌ No CSV file found for screen '{screen_name}' (UC: {uc_id}) in '{business_process_name}'")
        return []

    def _call_llm_for_test_case(self, prompt, output_dir, step_id, screen_name, row_index,
                                test_case_id=None, csv_file_name=None, matched_group=None):
        """Calls the LLM (via provider) with thinking_budget=0, mirroring the original."""
        parsed = self.provider.generate_structured(
            prompt, TestCase, module_name="test_case_generator", thinking_budget=0
        )
        if parsed is None:
            self._log_failed_test_case(output_dir, step_id, screen_name, row_index,
                                       "LLM response parsing failed", test_case_id, csv_file_name, matched_group)
            return None
        time.sleep(config.REQUEST_DELAY_SECONDS)
        return parsed

    def load_json_file(self, file_path) -> Any:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_csv_file(self, file_path) -> List[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return [row for row in csv.DictReader(f)]
        except Exception as e:  # noqa: BLE001
            print(f"Error loading CSV file {file_path}: {e}")
            return []

    def generate_test_cases(self):
        bp_files = list(self.general_output_dir.glob("business_process_*.json"))
        if not bp_files:
            print("No business process files found.")
            return

        project_output_dir = self.general_output_dir.parent
        self.pairwise_dir = project_output_dir / "pairwise"
        screen_vars_path = project_output_dir / "general" / "screen_variables.json"
        screen_vars_data = self.load_json_file(screen_vars_path) if screen_vars_path.exists() else None
        if not screen_vars_data:
            print(f"  - ⚠️  CRITICAL: screen_variables.json not found at {screen_vars_path}.")

        if not self.context_file.exists():
            with open(self.context_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
        with open(self.context_file, "r", encoding="utf-8") as f:
            full_test_case_context = json.load(f)

        tested_screen_use_cases = {
            (v.get("screen_name"), v.get("uc_id"))
            for v in full_test_case_context.values()
            if "screen_name" in v and "uc_id" in v
        }
        tested_groups = set()
        for v in full_test_case_context.values():
            groups_str = v.get("groups_involved", "")
            if groups_str:
                tested_groups.update(g.strip() for g in groups_str.split(","))
        tested_screen_names = {uc[0] for uc in tested_screen_use_cases if uc[0]} if tested_screen_use_cases else set()

        cumulative_step_counter = 1

        for bp_file in bp_files:
            business_process = self.load_json_file(bp_file)
            bp_name = Path(bp_file).stem
            try:
                business_flow_id = int(re.search(r"\d+$", bp_name).group())
            except (AttributeError, ValueError):
                print(f"    - ⚠️  Could not extract business flow ID from '{bp_name}'. Defaulting to 1.")
                business_flow_id = 1

            bp_output_dir = self.testcase_dir / bp_name
            bp_output_dir.mkdir(parents=True, exist_ok=True)
            bp_prompt_dir = self.prompt_dir / bp_name
            bp_prompt_dir.mkdir(parents=True, exist_ok=True)
            print(f"Processing business process: {business_process['process_name']} -> {bp_output_dir}")

            path_file_name = bp_file.name.replace("business_process", "path_business_process")
            path_file = self.path_dir / path_file_name
            if not path_file.exists():
                print(f"  - Path file not found: {path_file}. Skipping.")
                continue
            paths_data = self.load_json_file(path_file)
            paths = paths_data.get("paths", [])

            for step in business_process.get("steps", []):
                step_id = step.get("step_id")
                screen_name = step.get("current_screen")
                uc_id = step.get("uc_id")
                if not screen_name:
                    print(f"    - 'current_screen' not found for a step in {bp_file.name}. Skipping.")
                    continue
                print(f"  Processing Step {step_id}: {screen_name} (UC: {uc_id})")

                screen_vars_file = self.general_output_dir / "screen_variables.json"
                screen_vars_data = self.load_json_file(screen_vars_file) if screen_vars_file.exists() else None

                uc_has_parameters = self._check_if_uc_has_parameters(screen_name, uc_id, screen_vars_data)
                csv_files = []
                if uc_has_parameters:
                    csv_files = self._find_matching_csv_files(step, screen_name, business_flow_id, uc_id)
                else:
                    print(f"    - Skipping CSV lookup (UC '{uc_id}' has no parameters)")

                screen_data = []
                matched_group = None
                csv_file_name = None
                csv_unique_groups = set()
                skip_filter = False

                if csv_files:
                    print(f"    - Loading data from {len(csv_files)} CSV file(s).")
                    csv_file_name = csv_files[0].name if csv_files else None
                    for csv_file in csv_files:
                        screen_data.extend(self.load_csv_file(csv_file))

                    for row in screen_data:
                        groups_str = row.get("groups_involved", "")
                        if groups_str:
                            csv_unique_groups.update(g.strip() for g in groups_str.split(","))

                    if csv_unique_groups and csv_unique_groups.issubset(tested_groups):
                        print(f"    - ⚠️  All groups already tested (UC: {uc_id}).")
                        print(f"    - Generating 1 happy case to maintain business process flow.")
                        happy_case_rows = [r for r in screen_data if str(r.get("outcome", "")).strip().lower() == "true"]
                        if happy_case_rows:
                            screen_data = [{"_multiple_rows": True, "_all_happy_rows": happy_case_rows, "_count": len(happy_case_rows)}]
                            print(f"    - Consolidated {len(happy_case_rows)} happy case rows into 1 prompt.")
                        else:
                            print("    - No happy case found. Using first row.")
                            screen_data = screen_data[:1]
                        skip_filter = True

                    if not skip_filter:
                        original_row_count = len(screen_data)
                        filtered_screen_data = []
                        for row in screen_data:
                            groups_involved_str = row.get("groups_involved", "")
                            if not groups_involved_str:
                                filtered_screen_data.append(row)
                                continue
                            row_groups = [g.strip() for g in groups_involved_str.split(",")]
                            if any(group not in tested_groups for group in row_groups):
                                filtered_screen_data.append(row)
                        screen_data = filtered_screen_data
                        if original_row_count > len(screen_data):
                            print(f"    - Filtered CSV rows: {original_row_count} -> {len(screen_data)}")
                        if not screen_data:
                            print("    - All groups for this screen have been tested. Skipping.")
                            continue

                        untested_groups = csv_unique_groups - tested_groups
                        tested_group_ratio = (len(tested_groups & csv_unique_groups) / len(csv_unique_groups)
                                              if csv_unique_groups else 0)
                        if tested_group_ratio >= 0.5:
                            print(f"    - 📉 Optimization: {tested_group_ratio*100:.0f}% of groups already tested.")
                            happy_case_rows = [r for r in screen_data if str(r.get("outcome", "")).strip().lower() == "true"]
                            if happy_case_rows:
                                screen_data = [{"_multiple_rows": True, "_all_happy_rows": happy_case_rows, "_count": len(happy_case_rows)}]
                                print(f"    - Consolidated {len(happy_case_rows)} happy case rows into 1 prompt.")
                            else:
                                print("    - No happy case (outcome=true) found. Using first row.")
                                screen_data = screen_data[:1]

                    screen_uc_combo = (screen_name, uc_id)
                    if screen_uc_combo in tested_screen_use_cases:
                        print(f"    - ⚠️  Screen '{screen_name}' with use case '{uc_id}' has been tested before.")
                        happy_case_rows = [r for r in screen_data if str(r.get("outcome", "")).strip().lower() == "true"]
                        if happy_case_rows:
                            screen_data = [{"_multiple_rows": True, "_all_happy_rows": happy_case_rows, "_count": len(happy_case_rows)}]
                            print(f"    - Consolidated {len(happy_case_rows)} happy case rows into 1 prompt.")
                        else:
                            print("    - Warning: No happy case found. Using first row.")
                            screen_data = screen_data[:1]
                    elif screen_name in tested_screen_names:
                        print(f"    - Screen '{screen_name}' tested before but with different use case (UC: {uc_id}).")
                else:
                    print(f"    - No CSV file found. Using screen variables for '{screen_name}'.")
                    screen_data.append({})
                    screen_variables = self._get_screen_variables_for_business_process(
                        screen_name, business_flow_id, screen_vars_data
                    )
                    if screen_variables:
                        print(f"      - ✅ Found screen variables for '{screen_name}' in BP {business_flow_id}.")
                        matched_group = screen_variables
                    else:
                        print(f"      - ⚠️  No screen variables found for '{screen_name}' in BP {business_flow_id}.")
                        matched_group = None

                current_path = next((path for path in paths if path.get("path_id") == step_id), None)
                if not current_path:
                    print(f"    - Path not found for step_id: {step_id}. Skipping.")
                    continue

                previous_test_case_context = {}
                for prev_step_id in range(1, cumulative_step_counter):
                    context_key = f"TC-{prev_step_id:03}"
                    if context_key in full_test_case_context:
                        previous_test_case_context[context_key] = full_test_case_context[context_key]

                file_writer = ThreadSafeFileWriter()
                context_updater = ThreadSafeContextUpdater(self.context_file)
                print(f"    - Processing {len(screen_data)} test cases using {config.MAX_WORKERS} threads...")

                relevant_input_data = []
                if self.input_data:
                    if matched_group:
                        group_name = matched_group.get("group_name")
                        relevant_input_data = [
                            item for item in self.input_data
                            if item.get("screen_name") == screen_name and item.get("group_name") == group_name
                        ]
                        if not relevant_input_data:
                            relevant_input_data = [
                                item for item in self.input_data
                                if item.get("screen_name", "").lower() in screen_name.lower()
                                or screen_name.lower() in item.get("screen_name", "").lower()
                            ]
                    else:
                        relevant_input_data = [
                            item for item in self.input_data
                            if item.get("screen_name") == screen_name
                            or item.get("screen_name", "").lower() in screen_name.lower()
                            or screen_name.lower() in item.get("screen_name", "").lower()
                        ]
                    if not relevant_input_data:
                        relevant_input_data = self.input_data
                        print(f"    - ℹ️  No screen-specific input data for '{screen_name}'. Providing all input data.")

                results = process_test_case_batch_with_threads(
                    generator=self, screen_data=screen_data, step_info=step, path_info=current_path,
                    previous_test_case_context=previous_test_case_context, screen_name=screen_name,
                    step_id=step_id, cumulative_step_counter=cumulative_step_counter,
                    bp_output_dir=bp_output_dir, bp_prompt_dir=bp_prompt_dir, matched_group=matched_group,
                    input_data=relevant_input_data, file_writer=file_writer, context_updater=context_updater,
                    csv_file_name=csv_file_name,
                )

                tested_screen_use_cases.add((screen_name, uc_id))
                tested_screen_names.add(screen_name)
                if csv_files and csv_unique_groups:
                    tested_groups.update(csv_unique_groups)
                    print(f"    - ✅ Updated tested_groups: {csv_unique_groups}")

                cumulative_step_counter += 1
                with open(self.context_file, "r", encoding="utf-8") as f:
                    full_test_case_context = json.load(f)

                print(f"    📊 Summary: {results['successful_cases']}/{results['total_cases']} successful, "
                      f"{results['failed_cases']} failed, Time: {results['processing_time']:.2f}s")



# ===========================================================================
# TestCaseRetry (modules/test_case_retry.py)
# ===========================================================================
class TestCaseRetry:
    def __init__(self, provider: LLMProvider, test_generator: "TestCaseGenerator"):
        self.provider = provider
        self.test_generator = test_generator
        self.testcase_dir = config.TESTCASE_OUTPUT_DIRECTORY
        self.pairwise_dir = config.PAIRWISE_OUTPUT_DIRECTORY
        self.general_dir = config.GENERAL_OUTPUT_DIRECTORY
        self.retry_prompt_dir = config.LOGS_OUTPUT_DIRECTORY / "test_case_retry_prompt"
        self.business_processes = self._load_business_processes()
        self.paths_data = self._load_paths_data()
        self.file_lock = threading.Lock()
        self.print_lock = threading.Lock()
        self.retry_counters = {}
        self.retry_prompt_dir.mkdir(parents=True, exist_ok=True)
        print("🔄 Test Case Retry Module initialized")
        print(f"   - Found {len(self.business_processes)} business processes")

    def _load_business_processes(self):
        business_processes = []
        for bp_file in list(self.general_dir.glob("business_process_*.json")):
            try:
                with open(bp_file, "r", encoding="utf-8") as f:
                    business_processes.append({"file_id": bp_file.stem, "data": json.load(f)})
            except Exception as e:  # noqa: BLE001
                print(f"⚠️  Warning: Could not load {bp_file.name}: {e}")
        return business_processes

    def _load_paths_data(self):
        # NB: the original looks for general/paths.json which the path processor
        # does NOT produce (it writes path/path_business_process_N.json), so this
        # warns and path_info stays {} — preserved faithfully.
        paths_file = self.general_dir / "paths.json"
        if not paths_file.exists():
            print("⚠️  Warning: paths.json not found")
            return None
        try:
            with open(paths_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:  # noqa: BLE001
            print(f"⚠️  Warning: Could not load paths.json: {e}")
            return None

    def find_failed_test_cases(self):
        failed_cases = []
        if not self.testcase_dir.exists():
            print("❌ Test case directory not found")
            return failed_cases
        for bp_dir in self.testcase_dir.glob("business_process_*"):
            if not bp_dir.is_dir():
                continue
            failed_dir = bp_dir / "failed"
            if not failed_dir.exists():
                continue
            for failed_file in list(failed_dir.glob("failed_TC-*.json")):
                try:
                    with open(failed_file, "r", encoding="utf-8") as f:
                        failed_entries = json.load(f)
                    tc_id = failed_file.stem.replace("failed_", "")
                    failed_cases.append({
                        "business_process_id": bp_dir.name, "test_case_id": tc_id,
                        "failed_file": failed_file, "failed_entries": failed_entries,
                        "total_failures": len(failed_entries) if isinstance(failed_entries, list) else 1,
                    })
                except Exception as e:  # noqa: BLE001
                    print(f"❌ Error parsing {failed_file.name}: {e}")
        print(f"🔍 Found {len(failed_cases)} failed test cases total")
        return failed_cases

    def _load_csv_row(self, business_process_id, screen_name, row_index, csv_file_name=None):
        try:
            bp_num = business_process_id.split("_")[-1]
            if csv_file_name:
                csv_file = self.pairwise_dir / f"business_process_{bp_num}" / csv_file_name
            else:
                safe_screen_name = screen_name.replace(" ", "_")
                csv_file = self.pairwise_dir / f"business_process_{bp_num}" / f"{safe_screen_name}.csv"
            if not csv_file.exists():
                print(f"⚠️  CSV file not found: {csv_file}")
                return None
            with open(csv_file, "r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if row_index >= len(rows):
                print(f"⚠️  Row index {row_index} exceeds CSV length {len(rows)}")
                return None
            return rows[row_index]
        except Exception as e:  # noqa: BLE001
            print(f"❌ Error loading CSV row: {e}")
            return None

    def _get_step_info(self, business_process_id, step_id):
        for bp in self.business_processes:
            if bp["file_id"] == business_process_id:
                for step in bp["data"].get("steps", []):
                    if step.get("step_id") == step_id:
                        return step
                break
        print(f"⚠️  Step {step_id} not found in {business_process_id}")
        return None

    def _thread_safe_print(self, message):
        with self.print_lock:
            print(message)

    def _generate_single_test_case_with_context(self, step_info, csv_row_data, business_flow_id,
                                                screen_name, row_index, test_case_id, failed_entry=None):
        try:
            path_info = {}
            if self.paths_data and "paths" in self.paths_data:
                for path in self.paths_data["paths"]:
                    for path_step in path.get("steps", []):
                        if path_step.get("step_id") == step_info.get("step_id"):
                            path_info = path
                            break
                    if path_info:
                        break
            previous_test_case_context = {}
            relevant_input_data = {}
            if self.test_generator.input_data:
                for item in self.test_generator.input_data:
                    if item.get("screen", "").lower() == screen_name.lower():
                        relevant_input_data.update(item.get("value", {}))
                if not relevant_input_data:
                    for item in self.test_generator.input_data:
                        relevant_input_data.update(item.get("value", {}))

            formatted_prompt = prompt_storing.gen_test_case_prompt.format(
                step_info=json.dumps(step_info, indent=2),
                path_info=json.dumps(path_info, indent=2),
                test_case_context=json.dumps(previous_test_case_context, indent=2),
                screen_csv_data=json.dumps(csv_row_data, indent=2),
                matched_group=json.dumps({}, indent=2),
                input_data=json.dumps(relevant_input_data, indent=2),
            )
            parsed_test_case = self.provider.generate_structured(
                formatted_prompt, TestCase, module_name="test_case_retry", thinking_budget=0
            )
            time.sleep(config.REQUEST_DELAY_SECONDS)
            if parsed_test_case:
                test_case_data = parsed_test_case.model_dump()
                retry_id = self._generate_retry_test_case_id(test_case_id, f"business_process_{business_flow_id}")
                test_case_data["test_case_id"] = retry_id
                test_case_data["retry_metadata"] = {
                    "is_retry": True, "original_test_case_id": test_case_id, "retry_test_case_id": retry_id,
                    "retry_timestamp": datetime.now().isoformat(),
                    "retry_context": {"step_id": step_info.get("step_id"), "screen_name": screen_name,
                                      "row_index": row_index, "business_process": f"business_process_{business_flow_id}"},
                }
                return True, test_case_data
            return False, None
        except Exception as e:  # noqa: BLE001
            print(f"    ❌ Error generating test case with context: {e}")
            return False, None

    def _generate_retry_test_case_id(self, original_test_case_id, business_process_id):
        with self.file_lock:
            if original_test_case_id not in self.retry_counters:
                self.retry_counters[original_test_case_id] = self._get_existing_retry_count(
                    original_test_case_id, business_process_id
                )
            self.retry_counters[original_test_case_id] += 1
            return f"{original_test_case_id}R{self.retry_counters[original_test_case_id]:03d}"

    def _get_existing_retry_count(self, original_test_case_id, business_process_id):
        try:
            retry_file = self.testcase_dir / business_process_id / f"{original_test_case_id}_retry.json"
            if not retry_file.exists():
                return 0
            with open(retry_file, "r", encoding="utf-8") as f:
                retry_data = json.load(f)
            if isinstance(retry_data, dict) and "test_cases" in retry_data:
                return len(retry_data["test_cases"])
            elif isinstance(retry_data, dict) and "test_case_id" in retry_data:
                return 1
            return 0
        except Exception:  # noqa: BLE001
            return 0

    def _save_retry_result(self, business_process_id, test_case_id, test_case_data):
        try:
            output_dir = self.testcase_dir / business_process_id
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{test_case_id}_retry.json"
            with self.file_lock:
                if output_file.exists():
                    with open(output_file, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                    if isinstance(existing_data, dict) and "test_cases" in existing_data:
                        retry_data = existing_data
                        retry_data["test_cases"].append(test_case_data)
                        n = len(retry_data["test_cases"])
                        retry_data["summary"] = {"total_cases_in_file": n, "generated_cases": n,
                                                 "progress": f"{n} / {n}",
                                                 "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    elif isinstance(existing_data, dict) and "test_case_id" in existing_data:
                        retry_data = {"summary": {"total_cases_in_file": 2, "generated_cases": 2, "progress": "2 / 2",
                                                  "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                                      "test_cases": [existing_data, test_case_data]}
                    else:
                        retry_data = {"summary": {"total_cases_in_file": 1, "generated_cases": 1, "progress": "1 / 1",
                                                  "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                                      "test_cases": [test_case_data]}
                else:
                    retry_data = {"summary": {"total_cases_in_file": 1, "generated_cases": 1, "progress": "1 / 1",
                                              "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                                  "test_cases": [test_case_data]}
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(retry_data, f, indent=2, ensure_ascii=False)
            self._thread_safe_print(f"    ✅ Saved retry result: {output_file.name} "
                                    f"(Total: {retry_data['summary']['total_cases_in_file']})")
            return True
        except Exception as e:  # noqa: BLE001
            self._thread_safe_print(f"    ❌ Error saving retry result: {e}")
            return False

    def _remove_failed_entry(self, failed_file, entry_to_remove):
        try:
            with self.file_lock:
                with open(failed_file, "r", encoding="utf-8") as f:
                    failed_entries = json.load(f)
                if isinstance(failed_entries, list):
                    for i, entry in enumerate(failed_entries):
                        if (entry.get("step_id") == entry_to_remove.get("step_id")
                                and entry.get("screen_name") == entry_to_remove.get("screen_name")
                                and entry.get("row_index") == entry_to_remove.get("row_index")):
                            failed_entries.pop(i)
                            break
                    if not failed_entries:
                        failed_file.unlink()
                        self._thread_safe_print(f"    🗑️  Deleted empty failed file: {failed_file.name}")
                        return True
                    with open(failed_file, "w", encoding="utf-8") as f:
                        json.dump(failed_entries, f, indent=2, ensure_ascii=False)
                    self._thread_safe_print(f"    📝 Updated failed file: {len(failed_entries)} entries remaining")
                    return True
                return False
        except Exception as e:  # noqa: BLE001
            self._thread_safe_print(f"    ❌ Error removing failed entry: {e}")
            return False

    def _process_single_failed_entry(self, business_process_id, test_case_id, failed_file, failed_entry):
        result = {"success": False, "test_case_id": test_case_id, "business_process_id": business_process_id,
                  "failed_entry": failed_entry, "error_message": None}
        try:
            step_info = self._get_step_info(business_process_id, failed_entry["step_id"])
            csv_row_data = self._load_csv_row(business_process_id, failed_entry["screen_name"],
                                              failed_entry["row_index"], failed_entry.get("csv_file_name"))
            business_flow_id = int(business_process_id.split("_")[-1])
            if not step_info or not csv_row_data:
                result["error_message"] = f"Missing context for {test_case_id}"
                return result
            success, test_case_data = self._generate_single_test_case_with_context(
                step_info=step_info, csv_row_data=csv_row_data, business_flow_id=business_flow_id,
                screen_name=failed_entry["screen_name"], row_index=failed_entry["row_index"],
                test_case_id=test_case_id, failed_entry=failed_entry,
            )
            if success and test_case_data:
                if self._save_retry_result(business_process_id, test_case_id, test_case_data):
                    if self._remove_failed_entry(failed_file, failed_entry):
                        result["success"] = True
                        return result
                    result["error_message"] = "Failed to remove entry from failed file"
                    return result
                result["error_message"] = "Failed to save retry result"
                return result
            result["error_message"] = f"Retry failed for step={failed_entry.get('step_id')}"
            return result
        except Exception as e:  # noqa: BLE001
            result["error_message"] = f"Exception in processing: {str(e)}"
            return result

    def run_retry_process(self):
        start_time = time.time()
        print("=" * 60 + "\n🔄 STARTING TEST CASE RETRY PROCESS (MULTITHREADED)\n" + "=" * 60)
        failed_cases = self.find_failed_test_cases()
        if not failed_cases:
            print("✅ No failed test cases found!")
            return {"total_failed_found": 0, "total_entries_processed": 0, "successful_retries": 0,
                    "failed_retries": 0, "total_time": time.time() - start_time}
        results = {"total_failed_found": len(failed_cases), "total_entries_processed": 0,
                   "successful_retries": 0, "failed_retries": 0, "total_time": 0, "processing_details": []}
        tasks = []
        for failed_case in failed_cases:
            for failed_entry in failed_case["failed_entries"]:
                tasks.append({"business_process_id": failed_case["business_process_id"],
                              "test_case_id": failed_case["test_case_id"],
                              "failed_file": failed_case["failed_file"], "failed_entry": failed_entry})
        results["total_entries_processed"] = len(tasks)
        print(f"\n🚀 Processing {len(tasks)} tasks with 3 worker threads...")
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_task = {
                executor.submit(self._process_single_failed_entry, t["business_process_id"],
                                t["test_case_id"], t["failed_file"], t["failed_entry"]): t for t in tasks
            }
            for future in as_completed(future_to_task):
                try:
                    result = future.result()
                    if result["success"]:
                        results["successful_retries"] += 1
                        self._thread_safe_print(f"    ✅ Successfully retried {result['test_case_id']}")
                    else:
                        results["failed_retries"] += 1
                        self._thread_safe_print(f"    ❌ Failed retry for {result['test_case_id']}: {result.get('error_message')}")
                    results["processing_details"].append({
                        "test_case_id": result["test_case_id"], "business_process_id": result["business_process_id"],
                        "success": result["success"], "error_message": result.get("error_message")})
                except Exception as e:  # noqa: BLE001
                    results["failed_retries"] += 1
                    self._thread_safe_print(f"    ❌ Exception processing task: {e}")
        results["total_time"] = time.time() - start_time
        print("\n" + "=" * 60 + "\n📊 RETRY PROCESS SUMMARY\n" + "=" * 60)
        print(f"Successful Retries: {results['successful_retries']}")
        print(f"Failed Retries: {results['failed_retries']}")
        self._cleanup_empty_failed_folders()
        return results

    def _cleanup_empty_failed_folders(self):
        try:
            print("\n🧹 Checking for empty failed folders to cleanup...")
            for bp_dir in [d for d in self.testcase_dir.iterdir() if d.is_dir() and d.name.startswith("business_process_")]:
                failed_dir = bp_dir / "failed"
                if failed_dir.exists() and failed_dir.is_dir():
                    if not list(failed_dir.glob("*.json")):
                        try:
                            failed_dir.rmdir()
                            print(f"  ✅ Removed empty failed folder: {failed_dir.relative_to(self.testcase_dir)}")
                        except OSError as e:
                            print(f"  ⚠️  Could not remove {failed_dir.relative_to(self.testcase_dir)}: {e}")
            print("🧹 Cleanup check completed!")
        except Exception as e:  # noqa: BLE001
            print(f"⚠️  Error during failed folder cleanup: {e}")


# ===========================================================================
# MutationTestCaseGenerator (modules/mutation_test_case_generator.py)
# ===========================================================================
class MutationTestCaseGenerator:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.model_name = config.MODEL_FLASH_NAME
        self.general_output_dir = config.GENERAL_OUTPUT_DIRECTORY
        self.mutation_output_dir = self.general_output_dir.parent / "mutation_test_case"
        self.screen_vars_path = self.general_output_dir / "screen_variables.json"
        self.mutation_test_case_id_counter = ThreadSafeCounter(start_value=1)
        self.lock = threading.Lock()
        self.total_cost = 0.0
        self.total_tokens = 0
        self.request_count = 0
        self.mutation_output_dir.mkdir(parents=True, exist_ok=True)

    def load_json_file(self, file_path) -> Any:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:  # noqa: BLE001
            print(f"Error loading JSON file {file_path}: {e}")
            return None

    def _get_business_rules_for_screens(self, screen_names, screen_vars_data):
        if not screen_vars_data:
            return []
        all_rules = set()
        for screen in screen_vars_data.get("screens", []):
            if screen.get("screen_name") in screen_names:
                for layer in screen.get("layers", []):
                    for group in layer.get("element_groups", []):
                        for param in group.get("parameters", []):
                            for rule in param.get("test_data", {}).get("used_business_rules", []):
                                all_rules.add(rule)
        return list(all_rules)

    def _process_single_use_case(self, uc_id, steps, screen_vars_data):
        result = {"uc_id": uc_id, "success": False, "test_cases_count": 0, "error": None}
        try:
            print(f"  - Analyzing Use Case: {uc_id}")
            associated_screen_names = {step["current_screen"] for step in steps if "current_screen" in step}
            business_rules = self._get_business_rules_for_screens(associated_screen_names, screen_vars_data)
            steps_summary = json.dumps(steps, indent=2)
            business_rules_summary = (json.dumps(business_rules, indent=2) if business_rules
                                      else "No specific business rules were extracted for the associated screens.")
            prompt = prompt_storing.MUTATION_TEST_CASE_GENERATION_PROMPT.format(
                use_case_id=uc_id, business_process_steps=steps_summary, business_rules=business_rules_summary
            )
            output_dir = self.mutation_output_dir / uc_id
            output_dir.mkdir(parents=True, exist_ok=True)
            with open(output_dir / "mutation_prompt.txt", "w", encoding="utf-8") as f:
                f.write(prompt)

            # Original retries up to 3x on DEADLINE_EXCEEDED; the provider swallows
            # exceptions internally, so we retry on a None result.
            parsed_response = None
            for attempt in range(3):
                parsed_response = self.provider.generate_structured(
                    prompt, GeneratedTestCases, module_name="mutation_test_case_generator"
                )
                if parsed_response is not None:
                    break
                time.sleep(5)
            if not parsed_response:
                result["error"] = "Failed to get response after 3 attempts"
                return result

            generated_test_cases = parsed_response.test_cases
            if not generated_test_cases:
                print(f"    - No new scenarios found for {uc_id}.")
                result["success"] = True
                return result
            print(f"    - Found {len(generated_test_cases)} new test cases for {uc_id}.")
            for i, test_case in enumerate(generated_test_cases):
                mutation_id = self.mutation_test_case_id_counter.increment_and_get()
                test_case_data = test_case.model_dump()
                test_case_data["test_case_id"] = f"MTC-{mutation_id:03d}"
                with open(output_dir / f"mutation_tc_{i+1}.json", "w", encoding="utf-8") as f:
                    json.dump(test_case_data, f, indent=2, ensure_ascii=False)
                print(f"      - Saved test case MTC-{mutation_id:03d}")
            result["success"] = True
            result["test_cases_count"] = len(generated_test_cases)
        except Exception as e:  # noqa: BLE001
            result["error"] = str(e)
            print(f"    - Error generating test cases for {uc_id}: {e}")
        return result

    def generate_mutation_test_cases(self):
        print("Starting mutation test case generation...")
        screen_vars_data = self.load_json_file(self.screen_vars_path)
        if not screen_vars_data:
            print(f"  - ⚠️  Warning: screen_variables.json not found at {self.screen_vars_path}.")
        bp_files = list(self.general_output_dir.glob("business_process_*.json"))
        if not bp_files:
            print("No business process files found.")
            return
        all_steps_by_uc_id = {}
        for bp_file in bp_files:
            business_process = self.load_json_file(bp_file)
            if not business_process:
                continue
            for step in business_process.get("steps", []):
                uc_id = step.get("uc_id")
                if uc_id:
                    all_steps_by_uc_id.setdefault(uc_id, []).append(step)

        print(f"\n🚀 Processing {len(all_steps_by_uc_id)} use cases with 3 worker threads...")
        results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_uc = {
                executor.submit(self._process_single_use_case, uc_id, steps, screen_vars_data): uc_id
                for uc_id, steps in all_steps_by_uc_id.items()
            }
            for future in as_completed(future_to_uc):
                uc_id = future_to_uc[future]
                try:
                    results.append(future.result())
                except Exception as exc:  # noqa: BLE001
                    print(f"    ❌ {uc_id}: Exception - {exc}")
                    results.append({"uc_id": uc_id, "success": False, "test_cases_count": 0, "error": str(exc)})

        successful = sum(1 for r in results if r["success"])
        total_test_cases = sum(r["test_cases_count"] for r in results)
        print("\n" + "=" * 70 + "\n📊 MUTATION TEST CASE GENERATION SUMMARY\n" + "=" * 70)
        print(f"Total Use Cases Processed: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Total Mutation Test Cases Generated: {total_test_cases}")


# ===========================================================================
# FULL END-TO-END ORCHESTRATION  (mirrors run.ipynb steps 1-8)
# ===========================================================================
def _log_execution_time(module_name: str, start: float, end: float, status: str = "SUCCESS") -> None:
    try:
        config.LOGS_OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
        line = (f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {module_name:28} | "
                f"Status: {status:7} | Duration: {end - start:8.2f}s\n")
        with open(config.PERFORMANCE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: could not log execution time: {exc}")


def run_full_pipeline(provider_name: Optional[str] = None) -> None:
    config.ensure_output_dirs()
    provider = LLMProvider.create(provider_name)
    provider.prepare_document()  # extract the PDF text once (used inline per request)

    overall_start = time.time()

    def _run(name, fn):
        start = time.time()
        status = "SUCCESS"
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            status = "FAILED"
            print(f"❌ Error in {name}: {exc}")
        finally:
            end = time.time()
            _log_execution_time(name, start, end, status)
            print(f"⏱️  {name} completed in {end - start:.2f}s")

    # Step 1: Business Process Detector (extracts screens first as dependency)
    _run("Business Process Detector",
         lambda: BusinessProcessDetector(provider).extract_business_processes(str(config.PDF_DOCUMENT_PATH)))
    # Step 2: Screen Variable Detector
    _run("Screen Variable Detector", lambda: ScreenVariableDetector(provider).generate_screen_variables())
    # Step 3: Screen Graph Detector
    _run("Screen Graph Detector", lambda: ScreenGraphDetector(provider).generate_screen_graph())
    # Step 4: Path Processor
    _run("Path Processor", lambda: PathProcessor().process_all_business_processes())
    # Step 5: Pairwise Generator
    _run("Pairwise Generator", lambda: PairwiseGenerator().run())
    # Step 6: Test Case Generator
    tcg = TestCaseGenerator(provider)
    _run("Test Case Generator", lambda: tcg.generate_test_cases())
    # Step 7: Test Case Retry
    _run("Test Case Retry", lambda: TestCaseRetry(provider, tcg).run_retry_process())
    # Step 8: Mutation Test Case Generator
    _run("Mutation Test Case Generator", lambda: MutationTestCaseGenerator(provider).generate_mutation_test_cases())

    print(f"\n🎉 Pipeline finished in {time.time() - overall_start:.2f}s")
    print(f"📁 Artifacts in: {config.DOCUMENT_OUTPUT_PATH}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="IntelliTest — full end-to-end LLM-driven functional test-case generation."
    )
    parser.add_argument("--pdf", default=None,
                        help="Path to the RDS/SRS PDF (defaults to config.PDF_DOCUMENT_PATH).")
    parser.add_argument("--provider", choices=["gemini", "deepseek"], default=None,
                        help="LLM provider (defaults to LLM_PROVIDER env var, then 'gemini').")
    args = parser.parse_args(argv)

    if args.pdf:
        config.apply_document(args.pdf)
    if not config.PDF_DOCUMENT_PATH.exists():
        parser.error(f"PDF not found: {config.PDF_DOCUMENT_PATH}")

    provider = (args.provider or config.LLM_PROVIDER).lower()
    print(f"Provider : {provider}")
    print(f"Document : {config.PDF_DOCUMENT_PATH}")
    print("Mode     : full (end-to-end)")

    try:
        run_full_pipeline(provider)
    except Exception as exc:  # noqa: BLE001
        print(f"\nPipeline error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
