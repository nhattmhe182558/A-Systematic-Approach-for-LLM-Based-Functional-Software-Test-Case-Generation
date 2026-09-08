# Baseline 3 — Bhatia et al.

Replication of the conversational, specification-based test-case generation
baseline from:

> S. Bhatia, T. Gandhi, D. Kumar, P. Jalote, *"System test case design from
> requirements specifications: insights and challenges of using ChatGPT"*, 2024.

## Approach

A single chat session with the model:

1. **Familiarization (Prompt 1):** the full SRS (as JSON) is sent so the model
   has the whole specification in context.
2. **Generation (Prompt 2):** for each use case, the model is asked for
   specification-based test cases in a 6-column Markdown table
   (`ID`, `summary description`, `functionality/condition to be tested`,
   `input action/input values`, `expected output/behavior`, `additional comments`).
3. The Markdown rows are parsed into structured JSON records.

Both prompts are verbatim from the original. The LLM call is routed through a
`ChatProvider` so the same logic runs on **Gemini or DeepSeek**.

## Files

```
baseline_3/
├── main.py            # pipeline (verbatim prompts + parsing)
├── provider.py        # chat abstraction (GeminiChat / DeepSeekChat)
├── logger_utils.py    # token/cost/timing logging (per-day billing CSV)
├── requirements.txt
├── .env.example
├── input/             # put your SRS JSON here (input/srs_extracted_4lv.json)
└── output/            # generated test cases + logs land here
```

## Setup & run

```bash
pip install -r requirements.txt
cp .env.example .env        # add your API key(s)

python main.py --provider gemini
python main.py --provider deepseek
```

## Input format

`input/srs_extracted_4lv.json` — a JSON SRS with a top-level `use_cases` list,
each entry having `id`, `name`, `description`, and optionally `preconditions`,
`postconditions`, `expected_results`, `normal_flow`, `alternative_flows`,
`exceptions`. Edit `DOCUMENTS_CONFIG` in `main.py` to point at your file.

## Output

`output/<NAME>/generated_test_cases_<NAME>.json` plus a `logs/` folder with the
run log, per-day API-billing CSV, and execution-timing log.
