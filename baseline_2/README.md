# Baseline 2 — Milchevski et al.

Replication of the multi-step, agentic test-specification generation baseline
from:

> D. Milchevski, G. Frank, A. Hätty, B. Wang, X. Zhou, Z. Feng,
> *"Multi-Step Generation of Test Specifications using Large Language Models for
> System-Level Requirements"*, ACL 2025 (Industry Track).

## Approach (multi-step agentic workflow)

1. **Test Design (3a):** generate a Decision Table (Markdown) from the
   requirements — *text model*.
2. **Test Scenarios (3b):** parse the Decision Table into scenario records.
3. **Test Purposes (3c):** generate one test purpose per scenario — *text model*.
4. **Test Specification (4):** for each scenario, a **Generation Agent** writes
   an initial JSON spec, then a **Reflection Agent** critiques and refines it —
   *JSON model*, 3 retries each. (Few-shot retrieval is disabled, as in the
   original.) Between 15 and 40 specs are targeted.
5. **Artifacts (5):** write a Markdown report + Decision Table CSV.

Prompts (`src/prompts.py`) and the Markdown-table parsing (`src/utils.py`) are
**verbatim** from the original. The two Gemini models are replaced by a
`Provider` exposing `generate_text` / `generate_json`, so the same workflow runs
on **Gemini or DeepSeek**.

## Files

```
baseline_2/
├── main.py                # run_full_workflow (steps 1-5)
├── provider.py            # Gemini / DeepSeek abstraction (text + JSON)
├── src/
│   ├── config.py
│   ├── prompts.py         # verbatim prompt builders
│   ├── utils.py           # verbatim markdown-table parsing + artifact writer
│   ├── generator.py       # TestGenerationSystem (generation + reflection)
│   └── logger_utils.py    # token/cost/timing logging
├── requirements.txt
├── .env.example
├── input/requirements.txt # one requirement per line
└── output/                # report, decision table CSV, logs
```

## Setup & run

```bash
pip install -r requirements.txt
cp .env.example .env        # add your API key(s)

python main.py --provider gemini  --requirements input/requirements.txt
python main.py --provider deepseek --requirements input/requirements.txt
```

## Input format

`input/requirements.txt` — one user requirement per line, ideally in
"If … then …" form (black-box, testable). A sample is provided.

## Output

`output/<name>/test_artifacts_report.md` (scenarios, purposes, refined specs),
`output/<name>/decision_table.csv`, and a `logs/` folder with the run log,
per-day API-billing CSV, and execution-timing log.
