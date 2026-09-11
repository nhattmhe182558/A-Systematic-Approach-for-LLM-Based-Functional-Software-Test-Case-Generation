# Track B — Baseline Fidelity Audit

**Auditor:** Track B (code audit)
**Date:** 2026-09-11
**Question:** Do `baseline_1/2/3` faithfully reproduce the source methods
(Augusto, Milchevski, Bhatia) that the published "Generate test" paper claims as
its comparison baselines?

**Method:** Read each baseline's `README.md`, `main.py`, `provider.py`, and
supporting modules; compare the implemented control flow, prompts, and
generation config against the described source method and the thesis §4.1.3
baseline descriptions.

---

## Baseline 1 — Augusto et al. (ICTSS 2024): "Scenario-to-Case Derivation"

**Thesis §4.1.3 claim:** two-stage — (1) generate high-level test scenarios from
requirements, (2) scenarios become input to derive detailed test cases.

**Implementation (`baseline_1/main.py`):**
- `run_rq1`: Few-Shot + CoT prompt (`prompt_test_scenarios_few_shot_cot`)
  generates scenarios from `inputUserRequirements_en.txt` + a scenario example.
- `run_rq2`: extracts scenario titles from RQ1 output (regex), then for each
  title generates one system test case with a Few-Shot + CoT prompt, using
  leave-one-out cross-validation over the example test cases (split on `//TC`,
  removing example at index `i % 5 + 1`).
- Generation config: `temperature=0.1, top_p=1.0, max_output_tokens=32768`.

**Verdict: FAITHFUL.** Prompts are verbatim from the original Java
`RQ1Experimentation`/`RQ2Experimentation`. The two-stage scenario→case flow,
the cross-validation logic, and the generation config all match. The only
change is a Python port + provider abstraction (documented). ✔

**Caveat:** The two stages are decoupled — RQ2 reads `inputTestScenarios.txt`
which must be manually populated from RQ1 output. For an automated run we must
bridge RQ1→RQ2 (write RQ1 output into the scenarios file) or run `--stage all`
with an auto-copy step. This is a run-orchestration detail, not a fidelity flaw.

---

## Baseline 2 — Milchevski et al. (ACL 2025 Industry): "Intermediate Artifact Generation"

**Thesis §4.1.3 claim:** mimics a human tester — first generate structured
intermediate artifacts (decision tables, state diagrams, test purposes), then
use them as structured input for final test specifications.

**Implementation (`baseline_2/main.py`, `src/generator.py`):**
- Step 3a: `generate_test_design` → Decision Table (Markdown), text model.
- Step 3b: `extract_test_scenarios` parses the Markdown table into records.
- Step 3c: `generate_test_purposes` → one purpose per scenario.
- Step 4: per scenario, **Generation Agent** (`generate_initial_test_spec`) →
  initial JSON spec, then **Reflection Agent** (`refine_test_spec`) critiques &
  refines. 3 retries each. Few-shot retrieval disabled (as in original).
- Targets 15–40 specs.

**Verdict: FAITHFUL.** Prompts in `src/prompts.py` are verbatim (they even
retain the original Vietnamese docstring references to the source figures,
"Hình 9 & 10" etc.). The design→scenarios→purposes→generation→reflection
multi-step agentic workflow matches the ACL 2025 method exactly. Retrieval/
few-shot is disabled matching the original. ✔

**Caveat:** Requires a `requirements.txt` (one requirement per line, "If…then…"
form). The automotive/ISO-26262 framing is baked into the prompts (verbatim
from the source domain); when run on our web-app SRS this framing is a
faithfulness-vs-fit tradeoff inherited from the original method, and should be
noted as such in the paper, not "fixed."

---

## Baseline 3 — Bhatia et al. (2024): "Direct Prompt Chaining"

**Thesis §4.1.3 claim:** submit the whole SRS in a familiarization step, then a
chain of prompts, each generating test cases for one use case.

**Implementation (`baseline_3/main.py`):**
- Prompt 1 (familiarization): entire SRS JSON sent in a chat session.
- Prompt 2 (per use case): asks for specification-based test cases in a 6-column
  Markdown table (ID, summary, functionality/condition, input action/values,
  expected output, additional comments), within the SAME chat session (memory).
- `parse_llm_response` parses Markdown rows into structured records.
- Generation config: `temperature=0.7, top_p=1, top_k=1, max_output_tokens=16384`.

**Verdict: FAITHFUL.** Both prompts are verbatim. The conversational
single-session design (familiarization + per-use-case chaining) preserves chat
memory across use cases, which is the defining characteristic of the Bhatia
method. The 6-column output schema matches. ✔

**Caveat:** Uses `ChatProvider` (stateful chat), unlike baselines 1/2 which are
single-shot. Our BytePlus shim for this baseline MUST preserve multi-turn chat
history, or the familiarization step is wasted and fidelity breaks.

---

## Cross-cutting finding: PROVIDER MISMATCH (blocks the run tracks)

All three baselines' `provider.py` support only `gemini` (google-generativeai)
or `deepseek` (api.deepseek.com). **None targets the BytePlus endpoint**
(`ark.ap-southeast.bytepluses.com/api/v3`) or the assigned model IDs
(dola-seed-2-1-turbo, deepseek-v4-pro, deepseek-v4-flash).

The DeepSeek provider is OpenAI-compatible and reads `DEEPSEEK_API_KEY` /
`DEEPSEEK_BASE_URL`. The cleanest faithful path to run on BytePlus WITHOUT
touching the verbatim prompts or control flow:

  **Option A (minimal, recommended):** set env so the existing `deepseek`
  provider points at BytePlus:
    `DEEPSEEK_API_KEY=<BYTEPLUST_API_KEY>`
    `DEEPSEEK_BASE_URL=https://ark.ap-southeast.bytepluses.com/api/v3`
    `DEEPSEEK_MODEL=<one of the 3 byteplus model ids>`
  and run `--provider deepseek`. This reuses the OpenAI-compatible client with
  ZERO change to prompts/flow. Baseline 3's chat provider also needs the same
  env; verify it keeps multi-turn history.

  **Option B:** add a thin `byteplus` provider branch to each `provider.py`.
  More code, same result. Only needed if Option A's env reuse is undesirable.

**Recommendation for Track B-run:** use Option A, and additionally wrap each
run so that per-call token/cost/latency is captured in the SHARED schema (the
baselines have their own `logger_utils`, but we want one unified dataset for
Track F plots). Simplest: keep the baselines' own logs AND parse their
per-day billing CSVs into the shared schema during aggregation.

---

## Summary table

| Baseline | Source method | Faithful? | Blocker for running on BytePlus |
|----------|---------------|-----------|--------------------------------|
| 1 (Augusto) | Scenario→Case, 2-stage, FS+CoT, LOO-CV | YES ✔ | RQ1→RQ2 auto-bridge; deepseek-provider→BytePlus env |
| 2 (Milchevski) | Decision-table→purposes→gen+reflect agents | YES ✔ | deepseek-provider→BytePlus env |
| 3 (Bhatia) | Chat: familiarize + per-UC chaining | YES ✔ | must preserve chat memory; deepseek→BytePlus env |

All three are verbatim-prompt, control-flow-accurate ports. The published
paper's baseline claims are supported by the code. The only work needed to run
them is provider re-pointing (Option A) and unified logging for the comparison.
