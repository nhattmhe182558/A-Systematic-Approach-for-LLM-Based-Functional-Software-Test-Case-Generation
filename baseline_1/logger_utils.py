"""
logger_utils.py (Baseline 2 — Milchevski et al.)
================================================

Port of the original ExperimentLogger. Tracks per-module timing, token/cost
accounting, a per-day API-billing CSV, an execution-timing log, and a run log.
``log_api_call`` accepts a plain ``usage`` dict so it works across providers.
"""

import os
import datetime
import csv


class ExperimentLogger:
    def __init__(self, log_dir, doc_name, model_name="gemini-2.5-flash"):
        self.doc_name = doc_name
        self.model_name = model_name

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.doc_log_dir = os.path.join(log_dir, "logs", doc_name)
        os.makedirs(self.doc_log_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(self.doc_log_dir, f"log_{doc_name}_{timestamp}.txt")

        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        api_billing_dir = os.path.join(self.doc_log_dir, "api_billing")
        os.makedirs(api_billing_dir, exist_ok=True)
        self.csv_file_path = os.path.join(api_billing_dir, f"{date_str}.csv")
        self._init_csv_file()

        self.timing_log_path = os.path.join(self.doc_log_dir, "execution_timing.log")

        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.module_stats = {}
        self.module_start_times = {}

        self.pricing = {"gemini-2.5-flash": {"input": 0.30, "output": 2.50}}

        self.file = open(self.log_file_path, "w", encoding="utf-8")
        self.log_header()

    def _init_csv_file(self):
        if not os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "module", "input_tokens", "output_tokens",
                                 "total_tokens", "input_pricing", "output_pricing", "total_cost"])

    def log_header(self):
        self.write_line("==================================================")
        self.write_line(f"EXPERIMENT LOG - Document: {self.doc_name}")
        self.write_line(f"Time: {datetime.datetime.now()}")
        self.write_line(f"Model: {self.model_name}")
        self.write_line("==================================================\n")

    def log(self, message):
        self.write_line(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

    def log_api_call(self, usage=None, module_name="unknown"):
        p_tokens = (usage or {}).get("prompt_tokens", 0)
        c_tokens = (usage or {}).get("completion_tokens", 0)
        self.total_input_tokens += p_tokens
        self.total_output_tokens += c_tokens
        cost = self.calculate_cost(p_tokens, c_tokens)
        self.total_cost += cost

        stats = self.module_stats.setdefault(
            module_name, {"input_tokens": 0, "output_tokens": 0, "cost": 0.0, "requests": 0}
        )
        stats["input_tokens"] += p_tokens
        stats["output_tokens"] += c_tokens
        stats["cost"] += cost
        stats["requests"] += 1

        self._log_to_csv(module_name, p_tokens, c_tokens, cost)
        self.write_line(f"   >>> API Call ({self.model_name} - {module_name}): "
                        f"in={p_tokens} out={c_tokens} cost=${cost:.6f} total=${self.total_cost:.6f}")

    def _log_to_csv(self, module_name, input_tokens, output_tokens, cost):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prices = self.pricing.get(self.model_name, self.pricing["gemini-2.5-flash"])
        input_pricing = (input_tokens / 1_000_000) * prices["input"]
        output_pricing = (output_tokens / 1_000_000) * prices["output"]
        with open(self.csv_file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, module_name, input_tokens, output_tokens,
                             input_tokens + output_tokens,
                             f"{input_pricing:.8f}", f"{output_pricing:.8f}", f"{cost:.8f}"])

    def calculate_cost(self, input_tokens, output_tokens):
        prices = self.pricing.get(self.model_name, list(self.pricing.values())[0])
        return (input_tokens / 1_000_000) * prices["input"] + (output_tokens / 1_000_000) * prices["output"]

    def start_module(self, module_name):
        self.module_start_times[module_name] = datetime.datetime.now()

    def end_module(self, module_name, status="SUCCESS"):
        if module_name not in self.module_start_times:
            return
        start_time = self.module_start_times[module_name]
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        with open(self.timing_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] {module_name.ljust(25)} | "
                    f"Status: {status} | Duration: {duration:8.2f}s\n")
        del self.module_start_times[module_name]

    def log_summary(self):
        self.write_line("\n==================================================")
        self.write_line("SUMMARY")
        self.write_line(f"Total Input Tokens: {self.total_input_tokens}")
        self.write_line(f"Total Output Tokens: {self.total_output_tokens}")
        self.write_line(f"Total Estimated Cost: ${self.total_cost:.6f}")
        self.write_line("==================================================")

    def write_line(self, text):
        print(text)
        self.file.write(text + "\n")
        self.file.flush()

    def close(self):
        self.log_summary()
        with open(self.csv_file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["TOTAL_COST", "", "", "", "", "", "", f"{self.total_cost:.8f}"])
        self.file.close()
