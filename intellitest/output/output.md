# Output

This folder holds the **outputs** of the IntelliTest pipeline.

All artifacts are written under:

```
output/<document_stem>/
```

where `<document_stem>` is the PDF filename without its extension (e.g. a PDF
named `4lv-ieee830-lastest.pdf` produces `output/4lv-ieee830-lastest/`).

## Directory layout

```
output/<document_stem>/
├── general/                         # intermediate models of the app
│   ├── screens.json                 # [step 1 dep] all screens in the document
│   ├── business_process_1.json      # [step 1] one file per business process
│   ├── business_process_2.json
│   ├── ...
│   ├── screen_graph.json            # [step 3] navigation graph (nodes + edges)
│   ├── screen_variables.json        # [step 2] UI elements + BVA/EP test values
│   └── test_case_context.json       # [step 6] running context between test cases
├── path/                            # [step 4] BFS navigation paths
│   └── path_business_process_N.json
├── pairwise/                        # [step 5] pairwise (all-pairs) data as CSV
│   └── business_process_N/
│       └── <Screen>_<UC-id>.csv
├── testcase/                        # [step 6] final synthesised test cases
│   └── business_process_N/
│       ├── TC-<step>_batch_<n>.json # batch files ({summary, test_cases})
│       ├── TC-<id>_retry.json       # [step 7] successful retries
│       └── failed/                  # [step 6] failed cases (retried in step 7)
│           └── failed_TC-<step>.json
├── mutation_test_case/              # [step 8] gap-filling / "unhappy path" cases
│   └── <UC-id>/
│       ├── mutation_prompt.txt
│       └── mutation_tc_*.json
└── logs/
    ├── api_billing/<date>.csv       # per-call Gemini cost (+ TOTAL_COST row)
    ├── business_process_prompts/    # saved prompts per stage
    ├── screen_variable_prompts/
    ├── screen_graph_prompts/
    ├── test_case_prompts/
    ├── test_case_retry_prompt/
    └── execution_timing.log         # per-stage durations
```

## What each pipeline step produces

The runner always executes the full end-to-end pipeline (mirrors the original
`run.ipynb` steps 1–8):

| Step | Module | Output |
|------|--------|--------|
| — | screen extraction | `general/screens.json` — `{ "screens": [ { "screen_name", "description" } ] }` (a dependency of step 1). |
| 1 | Business Process Detector | `general/business_process_*.json` — per process: `process_name`, `process_description`, ordered `steps` (each with `uc_id`, `current_screen`, `next_screen`, `role`, …). |
| 2 | Screen Variable Detector | `general/screen_variables.json` — per screen: hierarchical `layers` → `element_groups` → `parameters`/`actions`, with `valid_values`/`invalid_values` from Boundary Value Analysis and Equivalence Partitioning. |
| 3 | Screen Graph Detector | `general/screen_graph.json` — `nodes` (screens) and `edges` (navigation actions with `element`, `keywords`, `roles`). Written incrementally by a thread-safe writer. |
| 4 | Path Processor | `path/path_business_process_*.json` — for each business-process step, the shortest navigation path (BFS over the screen graph, role-filtered). |
| 5 | Pairwise Generator | `pairwise/business_process_*/<Screen>_<UC>.csv` — all-pairs combinations of field values, each row tagged with `outcome` (`True`/`False`), `business_process`, `screen`, `use_case_id`, `groups_involved`. |
| 6 | Test Case Generator | `testcase/business_process_*/TC-*_batch_*.json` — final ISO-style test cases (`test_case_title`, `pre_condition`, `test_steps`, `test_data_fields`, `expected_result`, `expected_outcome`, `post_condition`). Failures logged under `failed/`. |
| 7 | Test Case Retry | `testcase/business_process_*/TC-*_retry.json` — regenerated cases for entries that failed in step 6 (IDs `TC-XXXRNNN`). Empty `failed/` folders are cleaned up. |
| 8 | Mutation Test Case Generator | `mutation_test_case/<UC>/mutation_tc_*.json` — extra cases covering functional gaps, each with `uncovered_conditions` for traceability. |

## The primary deliverables

- **`testcase/`** — the main business-process-driven functional test cases
  (happy paths + validation/negative scenarios from the pairwise data), plus
  any `*_retry.json` recovered by step 7.
- **`mutation_test_case/`** — extra adversarial / edge-case tests filling
  coverage gaps.

The `general/`, `path/`, and `pairwise/` folders are intermediate artifacts that
feed the later steps, but are also useful for inspection and reproducibility.
The `logs/` folder captures every prompt, per-call billing, and stage timings.

## Notes
- JSON is written UTF-8, pretty-printed.
- Steps are incremental: later steps read the JSON produced by earlier ones.
- Billing (`logs/api_billing/`) is populated only for the Gemini provider.
