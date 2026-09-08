"""
models.py
=========

Faithful port of the original IntelliTest infrastructure, consolidated here:

  * Pydantic schemas   - exact copies of the per-module model definitions.
  * ``BFSGraph``       - verbatim from ``utils/bfs_utils.py``.
  * billing helpers    - verbatim from ``utils/api_utils.py`` (Gemini pricing).
  * thread helpers     - verbatim from ``utils/thread_helpers.py``
                         (ThreadSafeFileWriter, ThreadSafeContextUpdater,
                          process_single_test_case, process_test_case_batch_with_threads).
  * ``ThreadSafeGraphWriter`` / ``ThreadSafeCounter`` - from the detector modules.
  * ``LLMProvider``    - the ONLY addition: a thin abstraction so the exact same
                         pipeline logic runs on Gemini OR DeepSeek.

Constants come from ``config.py`` (descendant of the original ``variables.py``),
imported as ``import config`` and referenced the way the original referenced
``variables.X``.
"""

from __future__ import annotations

import csv
import json
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel, Field, field_validator

import config

TModel = TypeVar("TModel", bound=BaseModel)


# ===========================================================================
# SCHEMAS (verbatim from the per-module definitions)
# ===========================================================================
# --- screen_utils.py ---
class ScreenItem(BaseModel):
    screen_name: str
    description: str


class ScreenList(BaseModel):
    screens: List[ScreenItem]


# --- business_process_detector.py ---
class BusinessProcessStep(BaseModel):
    step_id: int
    uc_id: str
    current_screen: str
    next_screen: str
    step: str
    description: str
    element: str
    keywords: List[str]
    role: str  # User role performing this action


class BusinessProcess(BaseModel):
    process_name: str
    process_description: str
    steps: list[BusinessProcessStep]


class BusinessProcesses(BaseModel):
    business_processes: list[BusinessProcess]


# --- screen_graph_detector.py ---
class GraphNode(BaseModel):
    id: int
    name: str


class GraphEdge(BaseModel):
    source: str
    target: str
    action: str
    element: str
    keywords: List[str]
    important_key: str
    roles: Optional[List[str]] = None


class ScreenFlowGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# --- screen_variable_detector.py ---
class TestData(BaseModel):
    valid_values: List[str] = []
    invalid_values: List[str] = []
    used_business_rules: List[str] = []


class ParameterElement(BaseModel):
    element_name: str
    element_type: str
    test_data: TestData


class ActionElement(BaseModel):
    element_name: str
    element_type: str


class ElementGroup(BaseModel):
    group_name: str
    business_function: str
    belong_to: str
    use_case_id: str
    parameters: List[ParameterElement] = []
    actions: List[ActionElement] = []


class Layer(BaseModel):
    layer_level: int
    trigger_element: Optional[str] = None
    element_groups: List[ElementGroup]

    @field_validator("trigger_element", mode="before")
    @classmethod
    def validate_trigger_element(cls, v):
        if isinstance(v, dict):
            return v.get("element_name")
        return v


class ScreenVariables(BaseModel):
    screen_name: str
    layers: List[Layer]


class ScreenVariablesResponse(BaseModel):
    screens: List[ScreenVariables]


# --- test_case_generator.py ---
class TestStep(BaseModel):
    step: str = Field(..., description="Description of the test step.")
    screen: str = Field(..., description="The screen where the step is performed.")
    step_type: str = Field(..., description="The type of the test step.")


class TestDataField(BaseModel):
    field_name: str = Field(..., description="The name of the data field.")
    field_value: str = Field(..., description="The concrete value for the data field.")


class TestCase(BaseModel):
    test_case_id: str = Field("", description="Will be set by the algorithm, leave empty.")
    path_number: str = Field(..., description="The path number identifier.")
    use_case_id: str = Field(..., description="The use case ID associated with this path.")
    navigation_sequence: List[str] = Field(..., description="Array of screen names in the navigation sequence.")
    current_screen: str = Field(..., description="The current screen name.")
    path_step: str = Field(..., description="The path step description.")
    test_scenario: str = Field(..., description="The overall scenario being tested.")
    test_case_title: str = Field(..., description="A concise title for the test case.")
    pre_condition: str = Field(..., description="The state required before executing the test.")
    expected_result: str = Field(..., description="The expected outcome of the test.")
    post_condition: str = Field(..., description="The state after the test is successfully executed.")
    expected_outcome: str = Field(..., description="The expected outcome from the CSV, 'true' or 'false'.")
    test_steps: List[TestStep] = Field(..., description="A list of detailed, actionable steps for the test case.")
    test_data_fields: List[TestDataField] = Field(..., description="A list of data fields and their values used in the test.")


# --- mutation_test_case_generator.py ---
class MutationTestCase(TestCase):
    uncovered_conditions: List[str] = Field(
        default=[], description="List of specific functional gaps or business rules this test case covers."
    )


class GeneratedTestCases(BaseModel):
    """A container for a list of generated test cases."""
    test_cases: List[MutationTestCase]


# ===========================================================================
# ThreadSafeCounter (test_case_generator.py / mutation_test_case_generator.py)
# ===========================================================================
class ThreadSafeCounter:
    """A simple thread-safe counter."""

    def __init__(self, start_value: int = 1):
        self._value = start_value
        self._lock = threading.Lock()

    def get_and_increment(self) -> int:
        with self._lock:
            current_value = self._value
            self._value += 1
            return current_value

    # mutation generator used this name
    def increment_and_get(self) -> int:
        with self._lock:
            current_value = self._value
            self._value += 1
            return current_value


# ===========================================================================
# BFSGraph (verbatim from utils/bfs_utils.py)
# ===========================================================================
class BFSGraph:
    """Graph class for Breadth-First Search algorithm."""

    def __init__(self):
        self.graph: Dict[str, List[Dict[str, Any]]] = {}

    def add_edge(self, source: str, target: str, action: str, element: str,
                 roles: Optional[List[str]] = None):
        if source not in self.graph:
            self.graph[source] = []
        edge = {"source": source, "target": target, "action": action,
                "element": element, "roles": roles}
        self.graph[source].append(edge)

    def find_shortest_path(self, start: str, end: str,
                           current_role: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        if start == end:
            return []
        if start not in self.graph:
            return None
        queue = deque([(start, [])])
        visited = {start}
        while queue:
            current_screen, path = queue.popleft()
            for edge in self.graph.get(current_screen, []):
                edge_roles = edge.get("roles")
                if edge_roles and current_role:
                    if current_role not in edge_roles:
                        continue
                next_screen = edge["target"]
                if next_screen == end:
                    return path + [edge]
                if next_screen not in visited:
                    visited.add(next_screen)
                    queue.append((next_screen, path + [edge]))
        return None

    def get_all_screens(self) -> List[str]:
        screens = set()
        for source, edges in self.graph.items():
            screens.add(source)
            for edge in edges:
                screens.add(edge["target"])
        return list(screens)

    def get_neighbors(self, screen: str) -> List[str]:
        return [edge["target"] for edge in self.graph.get(screen, [])]


def build_graph_from_screen_graph(screen_graph_data: Dict[str, Any]) -> BFSGraph:
    graph = BFSGraph()
    for edge in screen_graph_data.get("edges", []):
        graph.add_edge(
            source=edge.get("source", ""),
            target=edge.get("target", ""),
            action=edge.get("action", ""),
            element=edge.get("element", ""),
            roles=edge.get("roles"),
        )
    return graph


def find_path_between_screens(graph: BFSGraph, start_screen: str, end_screen: str,
                              current_role: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    return graph.find_shortest_path(start_screen, end_screen, current_role)


# ===========================================================================
# ThreadSafeGraphWriter (verbatim from screen_graph_detector.py)
# ===========================================================================
class ThreadSafeGraphWriter:
    """A thread-safe writer for incrementally building the screen graph JSON file."""

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self._lock = threading.Lock()
        self._node_names = set()
        self._max_id = 0

    def initialize_file(self):
        with self._lock:
            if not self.output_path.exists() or self.output_path.stat().st_size == 0:
                self.output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.output_path, "w", encoding="utf-8") as f:
                    json.dump({"nodes": [], "edges": []}, f, indent=4)
            with open(self.output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._node_names = {node["name"] for node in data["nodes"]}
                self._max_id = max((node["id"] for node in data["nodes"]), default=0)

    def write_graph_chunk(self, graph_chunk: ScreenFlowGraph):
        with self._lock:
            with open(self.output_path, "r", encoding="utf-8") as f:
                graph_data = json.load(f)
            new_nodes = []
            for node in graph_chunk.nodes:
                if node.name not in self._node_names:
                    self._max_id += 1
                    node.id = self._max_id
                    new_nodes.append(node)
                    self._node_names.add(node.name)
            graph_data["nodes"].extend([node.model_dump() for node in new_nodes])
            graph_data["edges"].extend([edge.model_dump() for edge in graph_chunk.edges])
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(graph_data, f, indent=4)
            print(f"  💾 Appended {len(new_nodes)} new nodes and {len(graph_chunk.edges)} edges to {self.output_path.name}")


# ===========================================================================
# api_utils billing (verbatim from utils/api_utils.py) — Gemini only
# ===========================================================================
def extract_gemini_metadata(response) -> Dict[str, int]:
    try:
        usage_metadata = response.usage_metadata
        input_tokens = 0
        if hasattr(usage_metadata, "prompt_tokens_details") and usage_metadata.prompt_tokens_details:
            for token_detail in usage_metadata.prompt_tokens_details:
                if hasattr(token_detail, "modality"):
                    if "TEXT" in str(token_detail.modality):
                        input_tokens = token_detail.token_count
                        break
        candidates_tokens = getattr(usage_metadata, "candidates_token_count", 0) or 0
        thoughts_tokens = getattr(usage_metadata, "thoughts_token_count", 0) or 0
        output_tokens = candidates_tokens + thoughts_tokens
        cache_tokens = getattr(usage_metadata, "cached_content_token_count", 0) or 0
        total_tokens = getattr(usage_metadata, "total_token_count", 0) or 0
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_tokens": cache_tokens,
            "total_tokens": total_tokens,
            "candidates_tokens": candidates_tokens,
            "thoughts_tokens": thoughts_tokens,
        }
    except Exception as e:  # noqa: BLE001
        print(f"Error extracting metadata: {e}")
        return {"input_tokens": 0, "output_tokens": 0, "cache_tokens": 0,
                "total_tokens": 0, "candidates_tokens": 0, "thoughts_tokens": 0}


def _calculate_cost_breakdown(metadata_dict):
    try:
        input_tokens = metadata_dict.get("input_tokens", 0)
        output_tokens = metadata_dict.get("output_tokens", 0)
        cache_tokens = metadata_dict.get("cache_tokens", 0)
        # No context caching is used; cache_tokens is normally 0. Pricing follows
        # the Gemini 2.5 Flash paid tier (per 1M tokens).
        input_pricing = input_tokens * 0.30 / 1_000_000
        output_pricing = output_tokens * 2.50 / 1_000_000
        cache_token_pricing = cache_tokens * 0.03 / 1_000_000
        total_tokens = input_tokens + output_tokens + cache_tokens
        total_token_pricing = input_pricing + output_pricing + cache_token_pricing
        total_cost = total_token_pricing
        return {
            "tokens": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                       "cache_tokens": cache_tokens, "total_tokens": total_tokens},
            "pricing": {"input_pricing": input_pricing, "output_pricing": output_pricing,
                        "cache_token_pricing": cache_token_pricing,
                        "total_token_pricing": total_token_pricing,
                        "total_cost": total_cost},
        }
    except Exception as e:  # noqa: BLE001
        print(f"Error calculating cost: {e}")
        return {"tokens": {"input_tokens": 0, "output_tokens": 0, "cache_tokens": 0, "total_tokens": 0},
                "pricing": {"input_pricing": 0, "output_pricing": 0, "cache_token_pricing": 0,
                            "total_token_pricing": 0, "total_cost": 0}}


def log_cost_to_csv(cost_breakdown, module_name="unknown"):
    try:
        config.API_BILLING_OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
        csv_filename = f"{datetime.now().strftime('%Y-%m-%d')}.csv"
        csv_filepath = config.API_BILLING_OUTPUT_DIRECTORY / csv_filename
        file_exists = csv_filepath.exists()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tokens = cost_breakdown["tokens"]
        pricing = cost_breakdown["pricing"]
        csv_row = {
            "timestamp": timestamp, "module": module_name,
            "input_tokens": tokens["input_tokens"], "output_tokens": tokens["output_tokens"],
            "cache_tokens": tokens["cache_tokens"], "total_tokens": tokens["total_tokens"],
            "input_pricing": pricing["input_pricing"], "output_pricing": pricing["output_pricing"],
            "cache_token_pricing": pricing["cache_token_pricing"],
            "total_token_pricing": pricing["total_token_pricing"],
            "total_cost": pricing["total_cost"],
        }
        with open(csv_filepath, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=list(csv_row.keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerow(csv_row)
        add_summary_row_to_csv(csv_filepath)
    except Exception as e:  # noqa: BLE001
        print(f"Error logging cost to CSV: {e}")


def add_summary_row_to_csv(csv_filepath):
    try:
        rows = []
        total_cost_sum = 0.0
        with open(csv_filepath, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames
            for row in reader:
                if row["timestamp"] != "TOTAL_COST":
                    rows.append(row)
                    if "total_cost" in row and row["total_cost"]:
                        try:
                            total_cost_sum += float(row["total_cost"])
                        except Exception:  # noqa: BLE001
                            pass
        if not rows:
            return
        summary_row = {}
        for field in fieldnames:
            if field == "timestamp":
                summary_row[field] = "TOTAL_COST"
            elif field == "total_cost":
                summary_row[field] = total_cost_sum
            else:
                summary_row[field] = ""
        with open(csv_filepath, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            writer.writerow(summary_row)
    except Exception as e:  # noqa: BLE001
        print(f"Error adding summary row: {e}")


def calculate_gemini_cost(metadata_dict, module_name="unknown"):
    cost_breakdown = _calculate_cost_breakdown(metadata_dict)
    log_cost_to_csv(cost_breakdown, module_name)
    return cost_breakdown


# ===========================================================================
# file utils (verbatim from utils/file_utils.py)
# ===========================================================================
def find_json_files(directory: Path) -> List[Path]:
    return list(directory.glob("**/*.json"))


def load_json_file(file_path: Path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"Error loading JSON file {file_path}: {e}")
        return None


# ===========================================================================
# thread_helpers (verbatim from utils/thread_helpers.py)
# ===========================================================================
def _save_prompt_to_file(prompt_dir: Path, cumulative_step_counter: int, row_index: int, prompt: str):
    try:
        prompt_filename = prompt_dir / f"prompt_TC-{cumulative_step_counter:03}_row_{row_index:03}.txt"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        with open(prompt_filename, "w", encoding="utf-8") as f:
            f.write(prompt)
    except Exception as e:  # noqa: BLE001
        print(f"    - ⚠️  Warning: Failed to save prompt to file: {e}")


class ThreadSafeFileWriter:
    """Thread-safe file writer for test case files."""

    def __init__(self):
        self._locks: Dict[str, threading.Lock] = {}
        self._lock = threading.Lock()

    def _get_lock(self, file_path: Path) -> threading.Lock:
        file_key = str(file_path)
        with self._lock:
            if file_key not in self._locks:
                self._locks[file_key] = threading.Lock()
            return self._locks[file_key]

    def write_test_case_batch(self, file_path: Path, test_case: Dict[str, Any], total_in_batch: int) -> bool:
        if not config.USE_LOCK_FOR_FILE_WRITING:
            return self._write_without_lock(file_path, test_case, total_in_batch)
        lock = self._get_lock(file_path)
        with lock:
            return self._write_without_lock(file_path, test_case, total_in_batch)

    def _write_without_lock(self, file_path: Path, test_case: Dict[str, Any], total_in_batch: int) -> bool:
        try:
            data = {"summary": {}, "test_cases": []}
            if file_path.exists() and file_path.stat().st_size > 0:
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        if "summary" not in data or "test_cases" not in data or not isinstance(data["test_cases"], list):
                            print(f"    - ⚠️  Warning: File {file_path.name} has incorrect format. Resetting.")
                            data = {"summary": {}, "test_cases": []}
                    except json.JSONDecodeError:
                        print(f"    - ⚠️  Warning: Could not decode JSON from {file_path.name}. Resetting.")
                        pass
            data["test_cases"].append(test_case)
            generated_count = len(data["test_cases"])
            data["summary"] = {
                "total_cases_in_file": total_in_batch,
                "generated_cases": generated_count,
                "progress": f"{generated_count} / {total_in_batch}",
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:  # noqa: BLE001
            print(f"Error writing test case to {file_path}: {e}")
            return False


class ThreadSafeContextUpdater:
    """Thread-safe context updater for test case context."""

    def __init__(self, context_file: Path):
        self.context_file = context_file
        self._lock = threading.Lock()

    def update_context(self, cumulative_step_counter: int, screen_name: str, test_case: Dict[str, Any]) -> bool:
        if not config.ENABLE_CONTEXT_UPDATE:
            return True
        if not config.USE_LOCK_FOR_CONTEXT_UPDATE:
            return self._update_without_lock(cumulative_step_counter, screen_name, test_case)
        with self._lock:
            return self._update_without_lock(cumulative_step_counter, screen_name, test_case)

    def _update_without_lock(self, cumulative_step_counter: int, screen_name: str, test_case: Dict[str, Any]) -> bool:
        try:
            expected_outcome_value = test_case.get("expected_outcome")
            is_success_outcome = (
                (isinstance(expected_outcome_value, bool) and expected_outcome_value is True)
                or (isinstance(expected_outcome_value, str) and expected_outcome_value.strip().lower() == "true")
            )
            if not is_success_outcome:
                return True
            context_data = {}
            if self.context_file.exists():
                with open(self.context_file, "r", encoding="utf-8") as f:
                    try:
                        context_data = json.load(f)
                    except json.JSONDecodeError:
                        context_data = {}
            context_key = f"TC-{cumulative_step_counter:03}"
            if context_key in context_data:
                return True
            context_data[context_key] = {
                "screen_name": screen_name,
                "uc_id": test_case.get("use_case_id"),
                "groups_involved": test_case.get("groups_involved", ""),
                "test_scenario": test_case.get("test_scenario"),
                "test_data": test_case.get("test_data_fields"),
                "result": test_case.get("expected_result"),
            }
            self.context_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.context_file, "w", encoding="utf-8") as f:
                json.dump(context_data, f, indent=2)
            return True
        except Exception as e:  # noqa: BLE001
            print(f"Error updating context: {e}")
            return False


def process_single_test_case(
    generator, formatted_prompt: str, step_id: int, cumulative_step_counter: int,
    screen_name: str, row_index: int, file_writer: "ThreadSafeFileWriter",
    context_updater: "ThreadSafeContextUpdater", output_filename: Path, bp_prompt_dir: Path,
    id_counter, total_in_batch: int, csv_file_name: str = None,
    data_row: Dict[str, Any] = None, matched_group: Dict[str, Any] = None,
) -> Tuple[bool, str]:
    try:
        if config.SAVE_PROMPTS_TO_TXT:
            _save_prompt_to_file(bp_prompt_dir, cumulative_step_counter, row_index, formatted_prompt)
        test_case_id = id_counter.get_and_increment()
        test_case_id_str = f"TC-{test_case_id:03}"
        parsed_test_case = generator._call_llm_for_test_case(
            formatted_prompt, output_filename.parent, step_id, screen_name, row_index,
            test_case_id_str, csv_file_name, matched_group,
        )
        if not parsed_test_case:
            return False, f"Failed to generate test case for row {row_index}"
        parsed_test_case.test_case_id = test_case_id_str
        new_test_case = parsed_test_case.model_dump()
        if data_row and "groups_involved" in data_row:
            new_test_case["groups_involved"] = data_row["groups_involved"]
        else:
            new_test_case["groups_involved"] = ""
        success = file_writer.write_test_case_batch(output_filename, new_test_case, total_in_batch)
        if not success:
            return False, f"Failed to write test case to file for row {row_index}"
        context_updater.update_context(cumulative_step_counter, screen_name, new_test_case)
        return True, f"Successfully generated test case for row {row_index}"
    except Exception as e:  # noqa: BLE001
        return False, f"Error processing row {row_index}: {str(e)}"


def process_test_case_batch_with_threads(
    generator, screen_data: List[Dict[str, Any]], step_info: Dict[str, Any],
    path_info: Dict[str, Any], previous_test_case_context: Dict[str, Any], screen_name: str,
    step_id: int, cumulative_step_counter: int, bp_output_dir: Path, bp_prompt_dir: Path,
    file_writer: "ThreadSafeFileWriter", context_updater: "ThreadSafeContextUpdater",
    input_data: Any, matched_group: Optional[Dict[str, Any]] = None, csv_file_name: str = None,
) -> Dict[str, Any]:
    import prompts as prompt_storing  # local import mirrors original `from cores.prompts import prompt_storing`
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {"total_cases": len(screen_data), "successful_cases": 0,
               "failed_cases": 0, "errors": [], "processing_time": 0}
    start_time = time.time()

    if config.CLEAR_OLD_BATCH_FILES:
        for old_batch_file in bp_output_dir.glob(f"TC-{step_id:03}_batch_*.json"):
            old_batch_file.unlink()

    batch_totals = {}
    for i in range(len(screen_data)):
        batch_index = i // config.BATCH_SIZE
        output_filename = bp_output_dir / f"TC-{step_id:03}_batch_{batch_index + 1:03}.json"
        str_filename = str(output_filename)
        batch_totals[str_filename] = batch_totals.get(str_filename, 0) + 1

    tasks = []
    for i, data_row in enumerate(screen_data):
        batch_index = i // config.BATCH_SIZE
        output_filename = bp_output_dir / f"TC-{step_id:03}_batch_{batch_index + 1:03}.json"
        prompt_template = prompt_storing.gen_test_case_prompt

        prompt_input_data = {}
        if isinstance(input_data, list) and input_data:
            prompt_input_data = {"input_groups": []}
            for item in input_data:
                group_data = {
                    "screen_name": item.get("screen_name", ""),
                    "group_name": item.get("group_name", ""),
                    "description": item.get("description", ""),
                    "values": item.get("value", {}),
                }
                prompt_input_data["input_groups"].append(group_data)
        elif isinstance(input_data, dict):
            prompt_input_data = input_data

        matched_group_data = matched_group if matched_group else {}

        if data_row and data_row.get("_multiple_rows"):
            csv_data_for_prompt = data_row["_all_happy_rows"]
        else:
            csv_data_for_prompt = data_row

        formatted_prompt = prompt_template.format(
            step_info=json.dumps(step_info, indent=2),
            path_info=json.dumps(path_info, indent=2),
            test_case_context=json.dumps(previous_test_case_context, indent=2),
            screen_csv_data=json.dumps(csv_data_for_prompt, indent=2) if csv_data_for_prompt else "{}",
            matched_group=json.dumps(matched_group_data, indent=2) if matched_group_data else "{}",
            input_data=json.dumps(prompt_input_data, indent=2) if prompt_input_data else "{}",
        )

        tasks.append({
            "formatted_prompt": formatted_prompt, "step_id": step_id,
            "cumulative_step_counter": cumulative_step_counter, "screen_name": screen_name,
            "row_index": i, "output_filename": output_filename, "bp_prompt_dir": bp_prompt_dir,
            "data_row": data_row, "total_in_batch": batch_totals[str(output_filename)],
            "csv_file_name": csv_file_name, "matched_group": matched_group,
        })

    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        future_to_task = {
            executor.submit(
                process_single_test_case, generator, task["formatted_prompt"], task["step_id"],
                task["cumulative_step_counter"], task["screen_name"], task["row_index"],
                file_writer, context_updater, task["output_filename"], task["bp_prompt_dir"],
                generator.test_case_id_counter, task["total_in_batch"], task["csv_file_name"],
                task["data_row"], task["matched_group"],
            ): task for task in tasks
        }
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                success, message = future.result()
                if success:
                    results["successful_cases"] += 1
                    if config.SHOW_PROGRESS:
                        print(f"    ✅ {message}")
                else:
                    results["failed_cases"] += 1
                    results["errors"].append({"row_index": task["row_index"], "error": message})
                    print(f"    ❌ {message}")
            except Exception as e:  # noqa: BLE001
                results["failed_cases"] += 1
                results["errors"].append({"row_index": task["row_index"], "error": str(e)})
                print(f"    ❌ Error processing row {task['row_index']}: {e}")

    results["processing_time"] = time.time() - start_time
    return results


# ===========================================================================
# LLM PROVIDER ABSTRACTION  (the only addition to the original design)
# ===========================================================================
def extract_pdf_text(pdf_path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    parts: List[str] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            parts.append(f"--- Page {i + 1} ---\n{text}")
    return "\n\n".join(parts)


# System instruction: treat the document as the authoritative RDS. Both
# providers inject the extracted document text inline on every request — no
# provider-specific context caching is used, so the two backends behave
# identically and the pipeline stays fully generalized.
DOCUMENT_SYSTEM_INSTRUCTION = (
    "You are analysing a software Requirement & Design Specification (RDS) document. "
    "Answer strictly from the document content. Do not invent screens, use cases, or "
    "business rules that are not present. When asked for JSON, return only valid JSON "
    "that matches the requested schema."
)


def _build_document_system_prompt(document_text: str, schema: "Type[TModel]") -> str:
    """Shared system prompt: instruction + full document text + schema hint."""
    try:
        schema_hint = json.dumps(schema.model_json_schema(), indent=2)
    except Exception:  # noqa: BLE001
        schema_hint = schema.__name__
    return (
        DOCUMENT_SYSTEM_INSTRUCTION
        + "\n\n=== RDS DOCUMENT CONTENT ===\n"
        + document_text
        + "\n\n=== END DOCUMENT ===\n\n"
        + "You MUST respond with a single JSON object that conforms to this JSON schema:\n"
        + schema_hint
    )


class LLMProvider:
    """Abstraction so identical pipeline logic runs on Gemini or DeepSeek.

    ``generate_structured`` is the single call every module funnels through. It
    returns a validated Pydantic instance (mirroring the original's
    ``response.parsed``) and logs billing per call with the caller's
    ``module_name``.

    Document handling is uniform across providers: ``prepare_document`` extracts
    the PDF text once, and each request injects that text inline. No context
    caching (a Gemini-only feature) is used.
    """

    provider_name = "base"

    def __init__(self):
        self.document_text = ""

    def prepare_document(self) -> None:
        print(f"[{self.provider_name}] Extracting text from document: {config.PDF_DOCUMENT_PATH}")
        self.document_text = extract_pdf_text(config.PDF_DOCUMENT_PATH)
        print(f"[{self.provider_name}] Extracted {len(self.document_text):,} characters.")

    def generate_structured(self, prompt: str, schema: Type[TModel],
                            module_name: str = "unknown",
                            thinking_budget: Optional[int] = None) -> Optional[TModel]:
        raise NotImplementedError

    @staticmethod
    def create(provider: Optional[str] = None) -> "LLMProvider":
        provider = (provider or config.LLM_PROVIDER).lower()
        if provider == "gemini":
            return GeminiProvider()
        if provider == "deepseek":
            return DeepSeekProvider()
        raise ValueError(f"Unknown provider '{provider}'. Use 'gemini' or 'deepseek'.")


class GeminiProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(self):
        super().__init__()
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set. Please add it to your .env file.")
        from google import genai
        from google.genai import types
        self.genai = genai
        self.types = types
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model_name = config.MODEL_FLASH_NAME

    def generate_structured(self, prompt, schema, module_name="unknown", thinking_budget=None):
        types = self.types
        try:
            gen_config_kwargs = dict(
                system_instruction=_build_document_system_prompt(self.document_text, schema),
                response_mime_type=config.RESPONSE_FORMAT,
                response_schema=schema,
            )
            if thinking_budget is not None:
                gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**gen_config_kwargs),
            )
            try:
                calculate_gemini_cost(extract_gemini_metadata(response), module_name=module_name)
            except Exception:  # noqa: BLE001
                pass
            parsed = response.parsed
            if parsed is not None:
                return parsed
            return schema.model_validate_json(response.text)
        except Exception as e:  # noqa: BLE001
            print(f"Warning: LLM call failed ({module_name}). Error: {e}")
            return None


class DeepSeekProvider(LLMProvider):
    provider_name = "deepseek"

    def __init__(self):
        super().__init__()
        if not config.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY is not set. Please add it to your .env file.")
        from openai import OpenAI
        self.client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL)
        self.model_name = config.DEEPSEEK_MODEL

    def generate_structured(self, prompt, schema, module_name="unknown", thinking_budget=None):
        system = _build_document_system_prompt(self.document_text, schema)
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            return schema.model_validate_json(response.choices[0].message.content)
        except Exception as e:  # noqa: BLE001
            print(f"Warning: LLM call failed ({module_name}). Error: {e}")
            return None
