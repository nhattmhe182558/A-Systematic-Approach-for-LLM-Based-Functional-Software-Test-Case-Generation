# Track D — Execution Phase (TEAA Agent) Study & Verification

**Scope.** Study and document the already-implemented IntelliTest EXECUTION phase (Test Execution and
Adaptation Agent, TEAA) in `web_testing_capstone_enhance-nhat/`, verify its computed execution metrics
against the shipped result artifacts, map the code to thesis section 3.2 (eqs 3.14–3.20), and specify
what a fresh BytePlus re-run would require. **No LLM/BytePlus API was called and the browser was not
driven.** This is a pure code + artifact study.

**SUT deploy confirmation.** FullTeaching is live: `GET https://localhost:5000/` returned **HTTP 200**
(HTTPS only; plain HTTP returns 400). Accounts: `teacher@gmail.com/pass`, `student1@gmail.com/pass`,
`student2@gmail.com/pass`. The agent entrypoints (`CustomLLMDroid/Agent.py`, `Mutation_Agent.py`) hard-code
`web_url = "https://localhost:5000/#/"` and launch Chrome with `--ignore-certificate-errors
--allow-insecure-localhost`, consistent with this deployment.

---

## 1. Architecture → Thesis §3.2 Mapping

The TEAA is implemented as `TestAgent` in `CustomLLMDroid/Agent.py` (positive/negative Golden-Path pipeline)
and `CustomLLMDroid/Mutation_Agent.py` (mutation re-execution pipeline). LLM access is `CustomLLMDroid/LLMCaller.py`
(Google `google-generativeai`, `gemini-2.5-flash`, multi-key rotation). Prompts live in `CustomLLMDroid/Prompt.py`,
JSON schemas in `CustomLLMDroid/Schemas.py`. `CustomLLMDroid/Reuseable_Module.py` + top-level `rerun.py` are the
LLM-free deterministic runners.

| Thesis concept (§3.2) | Formula | Code location | How it is realized |
|---|---|---|---|
| **(a) Golden Path filter** `G_k = {tc : ExpectedOutcome=True}` | **3.14** | `Agent.walkthrough()` | Loops business processes; `pop`s the `expected_outcome=='true'` test case as the `success_tc` before running negatives. |
| **(a) Semantic DOM Abstraction** `Φ: H_t → S_t`, `S_t={e: v(e)=1 ∧ ∃a∈{id,name,class,role}}` | **3.15** | `Agent.extract_interactable_elements()` + `is_visible()` | Parses HTML with BeautifulSoup; prunes `display:none/visibility:hidden/opacity:0/hidden/aria-hidden`, hidden CSS classes, and hidden ancestors (Visual Visibility `v(e)=1`); keeps clickable/input/form tags + elements with `role`/`on*`/`tabindex` (Functional Interactivity `A_ctrl`), emitting compact JSON. Thesis claims ~95% token reduction. `html_text_with_paths()` adds breadcrumb text for the oracle. |
| **(b) Strategy Function** `a_t = σ(S_t, M_STM, D_input)` + short-term memory | **3.16** | `Agent.evaluate_next_step()` + `EVALUATE_NEXT_STEP` prompt + `EVALUATE_NEXT_STEP_SCHEMA` | Single-action decision loop. Prompt receives `extracted_elem` (`S_t`), `short_term_memory` (`M_STM = self.short_term_mem["execute_log"]`), test-case fields, and both assumption + true `D_input`. Structured output = `{action, selector_type, selector_value, input_value, reasoning, done, web_fail, llm_fail}`. |
| **(b) Termination** `σ(...)="done" ⇒ Terminate` | **3.17** | `while not done:` loop; `done = response.get("done")` | Loop also has a 600s watchdog (`timeout_seconds`) that resets the driver/session to break infinite loops. |
| **(c) Golden Trace / long-term memory** `τ_verified → M_LTM` | (3.16–3.17 text) | `Agent.long_term_mem`, `success_happy_path.json`; reuse via `evaluate_past_success_tc()` + `CHOOSE_EXISTING_STEP_PROMPT` | On success, the error-free `execute_log` (minus `done`) is appended to `long_term_mem` and persisted. A "boosting" step queries LTM: if a past `tc_id` matches the current state, its steps are replayed to fast-forward — the thesis "Golden Trace reuse to bypass expensive re-inference." |
| **(d) Multi-modal Oracle** `Verdict(τ)=PASS iff ValidTech(τ) ∧ Match(ΔS, E_exp)` over `Diff_html` + `Snapshot_visual` | **3.18** | `Agent.evaluate_test_execution()` + `get_html_diff()` + `EVALUATE_TESTCASE_EXECUTION_PROMPT` + `VALIDATION_RESULT_SCHEMA`; images via `LLMCaller.generate_json_with_images()` | Captures `screenshot_before/after` (base64) and a unified HTML diff (truncated to 5000 chars), plus visible text and elements. Gemini returns `{valid_action (ValidTech), result (Match), llm_fail, web_fail, reasoning, assertion_selector}`. Two-channel structural+visual evaluation = the multi-modal oracle. |
| **(e) Trace Mutation for negatives** `τ_neg = Ψ(τ_verified, δ)` | **3.19** | `Agent.generate_false_testcase()` + `GENERATE_FALSE_TESTCASE_PROMPT` + `GENERATE_FALSE_TESTCASE_SCHEMA`; structural mutations in `Mutation_Agent.py` | Preserves the navigational sequence of the Golden Trace and perturbs input data at target steps (invalid/empty/malformed values). `Mutation_Agent.walkthrough()` handles heavier structural exception flows (reads `mutation_test_case/`, writes `generated_mutation_testcase_action/`, `success_mutation_path.json`). Oracle logic is reversed for negatives (expect error/blocking). |
| **(f) Deterministic Serialization** `S_exec = Γ(τ_verified, A) → {Actions[], Assertions[]}`, replayed by `R_det` | **3.20** | `Reuseable_Module.ReusableTestRunner` and top-level `rerun.py` (`TestCaseRunner`) | LLM-free Selenium runners consume saved `execute_log` + `assertions` (from the oracle's `assertion_selector`) and replay them with 12 assertion primitives (`element_exists`, `text_contains`, `url_contains`, visibility/enabled/attribute checks). `C_script ≪ C_LLM`: no model call at replay time. |

**§3.2.1–3.2.4 correspondence:** 3.2.1 (BP ingest + Golden Path + Semantic DOM) → `walkthrough` + `extract_interactable_elements`;
3.2.2 (Cognitive Decision Making / Contextual Memory) → `evaluate_next_step` + STM/LTM; 3.2.3 (Multi-modal Oracle Self-Reflective
Mutation) → `evaluate_test_execution` + `generate_false_testcase`; 3.2.4 (Deterministic Artifact Serialization) → `ReusableTestRunner`/`rerun.py`.

---

## 2. Verified Execution Metrics (from shipped artifacts)

Source of truth verified programmatically (env python + `json`): `my_method_evaluation_summary.json`.
All aggregates below were **recomputed and reconcile exactly** (no arithmetic discrepancy inside the artifact).

### 2.1 Top-line (verified totals add up)

| Metric | Value | Reconciliation check |
|---|---|---|
| Total test cases | **166** | passed 70 + failed 96 = 166 ✓ |
| Passed | 70 | success_rate = 70/166 = **42.17%** ✓ |
| Failed | 96 | — |
| Valid actions (case-level) | 135 | valid 135 + invalid 31 = 166 ✓; valid_action_rate = 135/166 = **81.33%** ✓ |
| Invalid actions | 31 | — |
| LLM failures | 35 | llm 35 + web 61 = 96 (= failed) ✓ |
| Web failures | 61 | — |
| Total actions | **1756** | done 528 + input 553 + click 667 + upload 8 = 1756 ✓ |

Per-business-process rows also reconcile: Σtotal = 166, Σpassed = 70, Σweb_fail = 61, Σllm_fail = 35.
(Note: BP-level `llm_fail`/`web_fail` sum to 35/61 but individual BP rows count failing categories per-case; BP-1 dominates with 132/166 cases.)

### 2.2 Action-type success rates (step-level, verified)

| Action | Success / Total | Rate |
|---|---|---|
| done | 363 / 528 | 68.8% |
| input | 142 / 553 | **25.7%** |
| click | 220 / 667 | 33.0% |
| upload | 4 / 8 | 50.0% |
| **All actions** | **729 / 1756** | **41.51%** |

`input` is the weakest action type (25.7%) — consistent with the failure-pattern data (269 input failures) and
the many `no such element [id=email/password/...]` errors: the agent frequently targets input fields by an `id`
that is not present in the current DOM state.

### 2.3 Selector usage & failures (`my_method_evaluation_failure_patterns.json`)

- Selector usage (from summary): `id` 1496, `text` 158, `xpath` 78, `class` 13, empty 11.
- Selector failures: `id` 590, `xpath` 49, `text` 48, `class` 5, empty 4.
- Action failures: `click` 308, `input` 269, `done` 116, `upload` 3.
- Failure by step type: `test_action` 402, `navigation` 99, `path_action` 11.
- Dominant runtime errors: `NoSuchElement` on hallucinated `id`s (email/password/log-in-btn/course inputs),
  `element not interactable` (esp. 11× on one session), `stale element reference`, and brittle deep XPath
  chains for session/file-group rows. One data error: a hard-coded local upload path
  (`C:\Users\Windows\Desktop\web_testing_capstone_enhance\reference_document.pdf`) not found → `upload` failure.

### 2.4 `comprehensive_report.csv` / `test_execution_overview.csv`
- `test_execution_overview.csv` = per-TC outcome table (64 rows): categories include `Success`, `Invalid Action`,
  `Assertion Failure`, `Unknown Failure`; success rows carry `Is Success=1`. This is the case-level roll-up view.
- `comprehensive_report.csv` = BVA "Rule Count" per generated test-case file (mapping TC → generated_testcase_action file
  → number of boundary rules) — the artifact behind the §4.3.6 BVA/VBER analysis, not the same population as the 166-case run.

### 2.5 `test_result.xlsx` / `test_result_updated.xlsx` (read via env python + openpyxl)
- Both hold **169 test cases** (sheet `test_results` / `Sheet1`), columns `ID, test_name, test_status, test_intent,
  errors, performance` (+ `relevant_ids` in the `_updated` version).
- Status distribution: **failed 132, passed 26, skipped 11** (169 total).
- These are **Cypress/static-script style** results (errors reference `Cypress`, `loginAndNavigateToCreateCourse()`,
  elements "obscured by the logo header") — i.e., the **static-script baseline** (AutoUAT-style), NOT the TEAA agent run.
  They evidence §4.3.6's "Static Script Fallacy": high failure due to race conditions / obscured elements. `relevant_ids`
  maps each Cypress test to the SRS rule IDs it targets.

### 2.6 Discrepancy vs thesis-reported figures — **IMPORTANT for the writer**

The thesis (§4.3.5, Table 4.4; §4.3.6, Table 4.5) reports **higher** numbers than the raw
`my_method_evaluation_summary.json`. They are **not the same population**:

| Figure | Thesis claim | Artifact (`my_method_evaluation_summary.json`) |
|---|---|---|
| Cohort | **Normal Flow only, N=166** (Golden Path + input-validation negatives that don't change screen flow) | **All 166** attempted cases (mixed) |
| Pass / Pass Rate | 148 passed → **89.20%** | 70 passed → **42.17%** |
| Valid Action Rate | 153/166 → **92.17%** | 135/166 → **81.33%** |
| LLM / Web failures | 17 / 72 | 35 / 61 |
| Verified Execution Rate (VBER) | **83.1%** (64/77 BVA rules) | n/a in this file (BVA lives in `comprehensive_report.csv`) |
| BVC (generation coverage) | **92.2%** (71/77) | n/a in this file |
| Exception success | ">80% exception" NOT supported — thesis Table 4.4 Exception Flow = **5.9%** (3/51) | — |

Key reconciliations / cautions:
1. **The 166 in the artifact ≠ the 166 "Normal Flow" cohort in Table 4.4.** The artifact's 166 is the full attempted
   set (42.17% pass). The thesis Table 4.4 partitions into Normal (N=166, 89.20%) and Exception (N=51, 5.9%). The two
   "166"s collide numerically but represent different filtering; the writer must not conflate the artifact's 42.17%
   with the thesis 89.20%.
2. **92.17% valid-action** in the thesis = 153/166 on the *Normal Flow* cohort; the artifact's comparable field is
   81.33% (135/166) on the full set. Both are internally consistent with their own denominators.
3. **VBER 83.1% and BVC 92.2%** come from the **FullTeaching BVA benchmark (N=77 rules)** (§4.3.6 / `comprehensive_report.csv`),
   a different measurement axis (rule coverage & verified execution), not the 166-case run.
4. The **">80% exception"** target is **contradicted** by the thesis's own Exception-Flow result (5.9%); the thesis
   explicitly documents a "Cognitive Ceiling" here and calls for future multimodal/visual grounding. The writer should
   present exception handling as a documented limitation, not a strength.

---

## 3. CustomLLMDroid vs LLMDroid — characterization

- **`LLMDroid/`** = the *original* LLMDroid port (the exploratory GUI-testing agent from the bundled paper
  "LLMDroid: Enhancing Automated Mobile App GUI Testing Coverage with LLM Guidance"). Structure: `Agent.py`,
  `WebTestingTool.py`, `WebPageManager.py`, `CoverageMonitor.py`, `GeminiInterface.py`, `Prompt.py`, `dataObject.py`.
  It is *coverage-driven, blind exploration* — dataclasses `TestCase/PageNode/CoverageMonitor`, discovers pages and
  maximizes coverage without SRS grounding. In the thesis this is **Baseline (LLMDroid, Exploratory)** — Table 4.5:
  BVC 29.9%, VBER 29.9%, 0.0% execution gap ("Survivorship Bias of Blind Exploration": near-zero gap only because it
  attempts only the simple happy paths it stumbles upon).

- **`CustomLLMDroid/`** = the authors' *adaptation of the LLMDroid idea into the TEAA*: it drops blind coverage
  exploration and instead consumes **SRS-derived, business-process-grouped test cases** (`tc_process/`), adds
  **Golden-Path filtering, STM/LTM Golden-Trace reuse, the multi-modal oracle, trace mutation, and deterministic
  serialization**. This is the file set the thesis §3.2 describes and the one that produced the 166-case artifacts.
  (Project logs refer to the LLMDroid adaptation as "baseline_5.")

Both share the same Selenium action primitives and Gemini backend; the difference is *specification-grounded,
memory-augmented, oracle-verified execution* (CustomLLMDroid) vs *coverage-maximizing exploration* (LLMDroid).

---

## 4. What a fresh BytePlus re-run would require

The agents currently bind to **Google `google-generativeai` + `gemini-2.5-flash`** and are **multimodal**
(the oracle sends two screenshots per verdict). To re-run on BytePlus (OpenAI-compatible):

1. **Port `CustomLLMDroid/LLMCaller.py` from `google-generativeai` to an OpenAI-compatible BytePlus client.**
   - Replace `genai.configure` / `GenerativeModel` with `openai.OpenAI(base_url=<BytePlus>, api_key=...)`.
   - `generate_json()` → `chat.completions.create(..., response_format={"type":"json_object"})`. Gemini's
     `response_schema` has no 1:1 OpenAI equivalent; either use JSON-mode + validate against the existing
     `Schemas.py` dicts, or convert them to JSON-Schema and use structured-output/`json_schema` mode if the chosen
     BytePlus model supports it. Keep the multi-key rotation loop (`_switch_key`) or swap for retry/backoff.
2. **Multimodal support is mandatory for the visual oracle.** `generate_json_with_images()` passes PIL images to
   Gemini. On OpenAI-compatible APIs this becomes content parts with `image_url` = `data:image/png;base64,<...>`.
   **The chosen BytePlus model must accept image inputs**, otherwise §3.2.3's dual-channel (DOM diff + screenshot)
   oracle degrades to the DOM-only fallback (`generate_json`), weakening exactly the exception-flow cases the thesis
   already flags as weak. If a vision-capable BytePlus model is unavailable, this is a hard blocker for faithful
   reproduction of the oracle.
3. **Keep Selenium unchanged.** The browser layer (`webdriver.Chrome`, `--ignore-certificate-errors`,
   `--allow-insecure-localhost`, `execute_action`, `extract_interactable_elements`) is provider-agnostic and needs no
   changes. The SUT is already live at `https://localhost:5000/#/`.
4. **Config/plumbing.** Replace `GEMINI_API_KEY` env with BytePlus key/base-url/model in `.env`; verify the same
   change is mirrored in `Mutation_Agent.py`. No API is called in this study — this is the delta spec only.
5. **Determinism note.** Only §3.2.4's `ReusableTestRunner`/`rerun.py` replay is LLM-free; the Golden-Trace discovery
   and oracle steps still incur LLM cost on a re-run.

---

## 5. Files reviewed (evidence trail)
- Code: `CustomLLMDroid/{Agent.py, Mutation_Agent.py, Prompt.py, LLMCaller.py, Reuseable_Module.py, Schemas.py}`, `rerun.py`, `LLMDroid/Agent.py` (+ folder listing).
- Artifacts: `my_method_evaluation_summary.json`, `my_method_evaluation_failure_patterns.json`, `comprehensive_report.csv`, `test_execution_overview.csv`, `test_result.xlsx`, `test_result_updated.xlsx`.
- Thesis: `_thesis_text.txt` §3.2 (eqs 3.14–3.20), §4.3.5 Table 4.4, §4.3.6 Table 4.5.
- SUT: `https://localhost:5000/` → HTTP 200 (HTTPS).
- Verification: env python `openpyxl` + `json` reconciliation (all sums check out; see §2).
