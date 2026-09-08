# IntelliTest (compact, provider-agnostic)

A compact re-implementation of the IntelliTest business-process-centric pipeline
for LLM-driven functional test-case generation. The original multi-module
codebase is condensed into four files and made to run on **either Gemini or
DeepSeek**. It always runs **full end-to-end** (every stage, in order).

```
intellitest/
├── config.py          # all constants (descendant of the original variables.py)
├── prompts.py         # all prompt templates
├── models.py          # schemas, BFS graph, billing, LLM provider abstraction
├── main.py            # full E2E pipeline + CLI
├── requirements.txt
├── .env.example
├── input/             # put your RDS/SRS PDF here (see input/input.md)
└── output/            # generated artifacts land here (see output/output.md)
```

## Setup

```bash
python -m venv env
# Windows:  env\Scripts\activate
# Linux/Mac: source env/bin/activate

pip install -r requirements.txt
cp .env.example .env        # then fill in your API key(s)
```

## Run (always end-to-end)

```bash
# Full pipeline with Gemini (default)
python main.py --pdf input/spec.pdf

# Use DeepSeek instead
python main.py --pdf input/spec.pdf --provider deepseek
```

If `--pdf` is omitted, `config.PDF_DOCUMENT_PATH` is used (default:
`input/4lv-ieee830-lastest.pdf`, overridable via the `PDF_DOCUMENT_PATH` env var).

The pipeline runs these stages in order (mirrors the original `run.ipynb`):
Business Process Detector → Screen Variable Detector → Screen Graph Detector →
Path Processor → Pairwise Generator → Test Case Generator → Mutation Test Case
Generator. (Screen extraction runs first as a dependency of the BP detector.)

## config.py

`config.py` holds the constants from the original `back_end/cores/configs/
variables.py` — same names, same values (`MAX_WORKERS`, `BATCH_SIZE`,
`SUCCESS_OUTCOME_THRESHOLD`, all the module-specific limits, and the full
output-directory / file-path layout). It adds provider settings (Gemini +
DeepSeek) and an `apply_document(pdf)` helper that re-points the derived paths
at runtime. The Gemini context-cache constants (`CACHE_TTL`, `CACHE_DISPLAY_NAME`,
etc.) were removed since caching is not used — the document is sent inline on
every request for both providers.

## Providers

Document handling is **uniform** across providers: the PDF text is extracted
once (`prepare_document`) and injected inline into every request. No
provider-specific context caching is used, so the two backends behave
identically.

| | Gemini | DeepSeek |
|---|---|---|
| Document ingestion | extracted text injected as `system_instruction` per request | extracted text injected as system message per request |
| Structured output | `response_schema` (Pydantic) | JSON mode + Pydantic validation |
| Billing log | per-call cost CSV under `logs/api_billing/` | — |
| SDK | `google-genai` | `openai` (pointed at DeepSeek base URL) |

Both are exposed behind the same `LLMProvider.generate(prompt, schema)` call, so
the pipeline code is provider-independent. Add a new provider by subclassing
`LLMProvider` in `models.py` and registering it in `LLMProvider.create`.

## Output

Artifacts are written under `output/<document_stem>/`:
`general/` (screens, business processes, screen graph, screen variables, context),
`path/`, `pairwise/`, `testcase/`, `mutation_test_case/`, and `logs/`
(prompts, per-call billing, execution timing). See `output/output.md` for the
full breakdown.
