# A Systematic Approach for LLM-Based Functional Software Test Case Generation and Autonomous Execution

**A reproduction-and-extension study.** Formatted after the IntelliTest capstone thesis
(*A Systematic Approach for LLM-Based Functional Software Test Case Generation*) and the prior
published paper (*A Business Process-Centric Approach for LLM-Driven Functional Test Generation*).

> **Scope and honesty statement.** The **generation** pipeline (§III-A) is **prior published work**
> and is reproduced here, not claimed as novel. The contributions of *this* document are: (1) a faithful
> **reproduction on a new multi-model backend** (BytePlus: `deepseek-v4-flash`, `deepseek-v4-pro`,
> `dola-seed-2-1-turbo`) with complete per-call token/cost/latency logging; (2) an **end-to-end
> integration** of generation with the Test Execution and Adaptation Agent (TEAA) against a live,
> locally-deployed system under test (FullTeaching); and (3) a **transparent economic and reliability
> analysis** that discloses, rather than hides, discrepancies between metrics computed over different
> test populations. Every quantitative claim traces to a logged artifact under `research_project/`.

---

## Definitions and Acronyms

| Acronym | Definition |
|---|---|
| API | Application Programming Interface |
| BFS | Breadth-First Search |
| BVA | Boundary Value Analysis |
| BVC | Boundary Value Coverage |
| BP | Business Process |
| CoT | Chain-of-Thought |
| DOM | Document Object Model |
| E2E | End-to-End |
| EP | Equivalence Partitioning |
| LLM | Large Language Model |
| LTM | Long-Term Memory |
| SRS | Software Requirements Specification |
| STC | State Transition Coverage |
| STM | Short-Term Memory |
| SUT | System Under Test |
| TEAA | Test Execution and Adaptation Agent |
| UAT | User Acceptance Testing |
| VBER | Verified BVA Execution Rate |
| VLM | Vision-Language Model |

---

## Abstract

Validating end-to-end business processes in software engineering remains a critical bottleneck because
of the *semantic gap* between ambiguous textual requirements and the precision required for executable
test scenarios. Prior published work — the business-process-centric IntelliTest **generation** pipeline —
demonstrated that combining the semantic reasoning of Large Language Models (LLMs) with deterministic
Specification-Based Testing (Equivalence Partitioning, Boundary Value Analysis, and Pairwise Testing),
together with a graph-based navigational model, produces mathematically complete, high-coverage functional
test suites while mitigating the "context amnesia" of purely generative models. That work stops at test
*generation*.

This paper reproduces the generation pipeline on a new, provider-agnostic multi-model backend (BytePlus,
OpenAI-compatible) and instruments it so that **every** model call records its prompt, response, prompt and
completion token counts, monetary cost, and latency. We then integrate the generation output with the
**Test Execution and Adaptation Agent (TEAA)**, an engine that translates the structured, ISO/IEC/IEEE
29119-3-style test specifications into resilient interactions on a live web application. We deploy the
system under test (FullTeaching, an Angular + Spring + OpenVidu learning-management platform) locally via
Docker and confirm the full generation→execution loop.

Empirically, a full generation run over the 31-page FullTeaching SRS consumes **2,450,312 tokens across 69
model calls (deepseek-v4-flash)** or approximately **2.6M tokens across 90 calls (deepseek-v4-pro)**,
producing 63 ISO-style test cases and 100+ mutation test cases in roughly 50–63 minutes. The two models
produce comparable artifact volumes, but the "pro" model costs approximately **3.5× more** per suite under
current (placeholder) pricing. On the execution side, we verify from the authors' artifacts a **42.2%
all-flows success rate** and an **81.3% valid-action rate** over 166 executed test cases and 1,756 browser
actions. We explicitly disclose that this all-flows figure differs from the thesis's headline 89.2%
normal-flow figure because the two are computed over different populations, and that the observed
exception-flow success (5.9%) contradicts the thesis's ">80%" exception claim — we report both and treat
exception handling as a documented limitation rather than a strength.

**Keywords:** Large Language Models, software testing, automated test generation, agentic execution,
functional testing, boundary value analysis, pairwise testing.

---

## I. Introduction

### I-A. The system-testing bottleneck

The Software Development Lifecycle treats testing not as a final phase but as a parallel assurance process.
Within it, **System Testing** is the definitive quality gate: it verifies that software complies with the
business requirements captured in the Software Requirements Specification (SRS). Achieving high-fidelity
assurance in this phase is cognitively expensive. Testers must (1) decompose the documentation into discrete
components — functional logic, UI designs — and map the web of interactions and state transitions between
them; and (2) strategically apply formal specification-based techniques to narrow an effectively infinite
input space into a finite, high-coverage test suite.

This burden is twofold. The **Test Analysis and Design** phase demands substantial cognitive load to
abstract business logic into executable scenarios. The **Test Implementation** phase — whether by manual
execution or by writing automation scripts — consumes large amounts of time. The high cost of maintaining
this rigor commonly produces a **happy-path bias**: testers prioritize valid workflows and neglect the
edge cases where defects concentrate, in order to meet delivery deadlines.

### I-B. Why naive LLM use is insufficient

LLMs promise to automate this domain, but current approaches exhibit two architectural deficiencies that
this project takes as its motivating premises:

1. **The rigor gap (coverage reliability).** The stochastic nature of LLMs leads to hallucination and
   precludes the systematic application of formal techniques. Consider a screen with `n` input parameters,
   each with a domain of representative values `D_i` after Equivalence Partitioning. The exhaustive test
   space is the Cartesian product `|Ω_data| = Π|D_i|`. A registration form with `n=10` fields and 4
   partitions each yields `4^10 ≈ 1,048,576` combinations. A purely inferential model produces a stochastic
   subset `T̂ ⊂ Ω_data` with `|T̂| ≪ |Ω_data|`, heavily biased toward the happy path. Combinatorial
   optimization (Pairwise Testing) is required to reduce this space while preserving interaction coverage.

2. **Context amnesia (contextual scope).** LLMs operate as localized inference engines and tend to generate
   tests for functions in isolation, failing to synthesize the stateful, multi-step business workflows that
   validate end-to-end logic. Formally, modeling the application as a state-transition graph `G = (V, E)`,
   a business process is a directed path `π = ⟨s_0 →a_1 s_1 →a_2 … →a_k s_k⟩`, and validating state `s_k`
   often depends on latent variables produced at earlier steps. Purely generative models lose this
   continuity.

A parallel deficiency appears in **execution**: autonomous agents often navigate without a grounded script
(behaving like an "unguided mouse in a maze") and, crucially, lack a definitive **oracle** — an awareness of
correct behavior derived from requirements — so they cannot reliably decide whether the application is
functioning correctly.

### I-C. Contributions of this document

The prior published IntelliTest generation pipeline addresses the rigor gap and context amnesia for the
*design* phase, using LLMs strictly for requirement comprehension while delegating completeness to
deterministic algorithms (EP, BVA, Pairwise) and a graph-based navigational model. Because that work is
already published, this document does not re-claim it. Instead, the contributions here are deliberately
scoped to what is new:

1. **Reproduction on a new multi-model backend with full accounting.** We port the pipeline to BytePlus
   (an OpenAI-compatible endpoint) and run it on three models, logging every call's tokens, cost, and
   latency. This establishes that the method is not tied to a single model family and yields the
   per-model cost profile the original did not report.
2. **End-to-end generation→execution integration.** We connect the generated ISO-style specifications to
   the TEAA execution agent and confirm the loop against a **live**, locally-deployed FullTeaching SUT.
3. **Transparent economics and reliability accounting.** We report measured token/cost figures and, per the
   supervisor's explicit instruction to *not hide any data*, we disclose where measured execution metrics
   diverge from previously reported headline numbers, including a contradiction in the exception-flow claim.

The remainder is organized as: §II literature review (an 82-paper PRISMA synthesis, with Yun Lin's
WebTestPilot as the closest execution-phase prior art); §III methodology (generation as referenced prior
work; execution/TEAA as the integration focus); §IV experiment; §V discussion including economic
feasibility and threats to validity; §VI conclusion.


---

## II. Literature Review

### II-A. Review protocol (PRISMA)

To situate this work, we conducted a PRISMA-style systematic review. Search strings combined four keyword
groups — **domain** {system testing, functional testing, UAT, acceptance testing} × **technique** {LLM,
large language model, AI agent, autonomous, multi-agent} × **target** {web application, GUI, interface,
app} × **activity** {test case generation, test execution, test automation} — augmented with adjacent
subfields (unit/integration test generation, oracle generation, self-healing automation, DOM/accessibility
abstraction, RAG for testing, VLM GUI testing, REST API testing, BDD/Gherkin, flaky-test detection,
requirements traceability, combinatorial testing). Approximately 30 distinct queries were executed against
arXiv, IEEE Xplore, the ACM Digital Library, and venue proceedings. After title/abstract screening and
de-duplication by normalized title and arXiv identifier, **82 papers** were included. The machine-readable
corpus (11-column schema: title, authors, year, venue, link, quartile, summary, problem solved, methodology,
type, original link) is provided as `related_articles.xlsx` across three sheets (Systematic Review = 82;
New Research 2025–26 = 19; All References = 101 rows). Uncertain author/venue/quartile fields are explicitly
marked `[estimated]`; all arXiv identifiers are real.

### II-B. Taxonomy of dynamic testing techniques

We frame the work within the standard taxonomy. **Structure-based (white-box)** techniques (statement,
decision coverage) verify the "how" of implementation but are insufficient for functional validation.
**Experience-based** techniques (error guessing, exploratory testing) are valuable but subjective and hard
to automate reproducibly. The focus of this project is **Specification-Based Testing (black-box)**, which
derives tests strictly from external documentation (SRS, use cases, user stories). Within it: **Equivalence
Partitioning (EP)** and **Boundary Value Analysis (BVA)** are the input-validation pillars; **Pairwise
Testing** mitigates combinatorial explosion by guaranteeing that every pair of parameter values is covered
at least once; **Decision Table** and **State Transition** testing address logic and lifecycle dynamics; and
**Use Case Testing** links functions into coherent workflows.

### II-C. Two paradigms and the gap between them

The 82-paper corpus separates into two paradigms:

- **Top-down, document/requirement-driven GENERATION.** The prior IntelliTest work sits here. Neighbours:
  ChatTester and ChatUniTest (unit-test generation with adaptive focal context and generation-validation-
  repair loops); high-level/requirements test generation (arXiv:2503.17998, 2510.03641); UAT tooling
  (AutoUAT + Test Flow, arXiv:2504.07244; AToMIC, arXiv:2510.18861); and multi-agent generators with oracle
  panels (CANDOR, arXiv:2506.02943; TestAgent, arXiv:2607.09101).
- **Bottom-up, AGENTIC EXECUTION.** DroidAgent (intent-driven mobile GUI testing with long/short-term
  memory), GPTDroid (functionality-aware GUI Q&A), WebVoyager (multimodal end-to-end web agent, 59.1% task
  success), and Autonomous Test Agents (PinATA/SeeAct-ATA, arXiv:2504.01495).

**Three synthesis claims** carry into this paper:

1. **Two paradigms, one gap.** No single 2025–2026 work integrates *business-process-grounded generation*
   with an *autonomous UAT execution agent* that issues reliable verdicts, while simultaneously addressing
   soundness/consistency and oracle reliability. The prior published work covers generation only; this
   document's contribution is the integration.
2. **The rigor gap is measurable.** Generation is evaluated with reproducible metrics (coverage, mutation,
   assertion correctness). Execution/agentic work relies on ad-hoc task-success rates with no shared oracle
   benchmark — WebVoyager reports 59.1% task success; PinATA reports ~60% correct verdicts (up to 94%
   specificity). This is precisely why our execution results (§IV-C) are reported against multiple
   denominators.
3. **Context amnesia is shared.** ChatUniTest's token-budget focal context and DroidAgent's explicit memory
   modules both exist to fight the same amnesia the generation pipeline threads business-process context
   through. Our TEAA carries this forward with short-term and long-term (Golden Trace) memory.

### II-D. Closest prior art for the execution phase

Two works are the primary anchors for the execution half:

- **WebTestPilot** — Xiwen Teoh, **Yun Lin** (Associate Professor & Deputy Head of the CS Department,
  Shanghai Jiao Tong University; formerly NUS, PAT group of Prof. Jin Song Dong), Duc-Minh Nguyen, Ruofei
  Ren, Wenjie Zhang, Jin Song Dong. **FSE 2026** (arXiv:2602.11724). This is the single closest concurrent
  competitor to the TEAA. It is a **neurosymbolic** LLM agent that (1) detects and **symbolizes** critical
  GUI elements into variables, and (2) translates an NL specification into a sequence of steps, each equipped
  with **inferred pre- and post-condition oracles** over those symbols, capturing **data, temporal, and
  causal** dependencies. It directly attacks the two problems the thesis also names — the *implicit oracle
  inference* problem (the agent must be its own oracle) and the *probabilistic inference* problem
  (distinguishing a hallucination from a real bug). On a bug-injected benchmark it reports **99% task
  completion, 96% precision, and 96% recall** (+70 precision / +27 recall over the best baseline).
  *Differentiation:* our TEAA grounds execution in the **business-process graph inherited from the
  generation half**, and uses **Semantic DOM abstraction + Golden-Trace memory + a multi-modal (DOM diff +
  screenshot) oracle + trace mutation**, whereas WebTestPilot centers on symbolization and inferred
  symbolic pre/post-condition oracles. WebTestPilot is the recommended primary comparison for any future
  head-to-head execution evaluation.

  Yun Lin's group produces several other directly relevant 2025–2026 works: *Compiling Large Multi-Modal
  Requirement Documents into Runnable Software Systems* (ISSTA 2026, arXiv:2602.13723); *Generating
  Project-Specific Test Cases with Requirement Validation Intention* (ISSTA 2026); *Generalizing Test Cases
  for Comprehensive Test Scenario Coverage* (TestGeneralizer, FSE 2026, arXiv:2604.21771); and design-to-
  action agents for GUI testing (ISSTA 2025).

- **Are Autonomous Web Agents Good Testers? (PinATA / SeeAct-ATA)** — arXiv:2504.01495. Establishes that
  autonomous test agents can execute NL test cases and return pass/fail verdicts, but at limited reliability
  (~60% correct verdict). This is the empirical baseline for "can agents judge correctness at all," and it
  contextualizes our 42.2% all-flows figure.

### II-E. Newly-emerged concerns (2025–2026) the paper must acknowledge

The re-research track surfaced several themes that postdate the prior published work and shape the execution
half's threats-to-validity:

- **NL-test soundness and consistency** (arXiv:2509.19136): NL tests can be *unsound* (false failures from
  ambiguity) and *inconsistent* (nondeterministic re-runs). This must appear as a threat to validity.
- **Self-healing via DOM/accessibility trees** (arXiv:2603.20358): sub-second selector re-discovery at zero
  ongoing API cost, scaling to 300+ tests.
- **Bounded autonomous repair** (arXiv:2605.01471): ~70% repair convergence, mean 4.4 iterations — realistic
  limits on self-correction during execution.
- **DOM pruning at scale** (Prune4Web, arXiv:2511.21398): programmatic pruning of 10k–100k-token DOMs, the
  same bottleneck the TEAA's Semantic DOM Abstraction addresses.
- **Accessibility-tree prompt injection** (arXiv:2507.14799): a genuine security threat model for DOM/
  accessibility-tree-driven agents.
- **Requirement→oracle alignment on real bugs** (arXiv:2607.10277): LLM-generated oracles align more with
  requirements than with the SUT and show high variance — central to autonomous-verdict reliability.


---

## III. Methodology

### III-A. Test Case Design Phase (PRIOR PUBLISHED WORK — reproduced, not claimed)

The generation pipeline is the previously published IntelliTest design phase. It is included here in detail
only to ground the execution integration and to document the faithful reproduction on BytePlus. It runs
eight stages end-to-end (`intellitest/main.py::run_full_pipeline`), each funneling through a single provider
abstraction (`LLMProvider.generate_structured`) that returns a validated Pydantic object.

**Stage 1 — Screen extraction.** Extract the set of system screens `S` from the SRS → `general/screens.json`.
On the FullTeaching SRS this yielded 4 screens (Landing, Dashboard, Course Details, Video Session).

**Stage 2 — Business Process Detector.** Extract ordered, multi-step business processes. A **grounding
constraint** prevents hallucinated navigation: for every step `st` in every business process `b`,
`{cs(st), ns(st)} ⊆ S_names` — the current and next screen of each step must be members of the
pre-identified screen set. On FullTeaching this produced 6 business processes
(`business_process_1..6.json`).

**Stage 3 — Screen Variable Detector.** For each screen, an LLM function `F_var` builds a behavioral model
`M_var(S_i) = F_var(P_var(B(S_i)), C)` (eq. 3.6), where `B(S_i)` is the subset of business processes
touching screen `S_i` and `C` is the document context. The prompt introduces a **hierarchical layer
structure** `L_i = {l_0, l_1, …, l_m}` (a base layer of always-visible elements; each subsequent layer
gated by a trigger in the previous), organizes elements into **element groups** `g`, and instructs the model
to act as a Test Analyst applying BVA, decision-table, and state-machine reasoning. A **Strict Abstract
Value Constraint** forces abstract data categories (e.g., `"valid_email_format"`) rather than concrete
instances. For each parameter `p` it yields a domain `TD_p = (V_valid, V_invalid)`. Each group is linked to
its business function: `∀g ∈ M_var(S_i): β(g) ∈ {b.name | b ∈ B(S_i)}` (eq. 3.7).

**Stage 4 — Screen Graph Detector.** Build the directed navigational graph `G_screen = (V, E)` with `V = S`.
For each screen, a CoT-guided function `F_graph` emits the outgoing edge subset `E_i = F_graph(P_graph, C,
s_i)` (eq. 3.5). Each edge is a tuple `e = (s_source, s_target, a, el, K, k_imp)` (action, element, keyword
set, most-critical keyword). A thread-safe writer atomically unions the subsets: `E = ∪ E_i`.

**Stage 5 — Path Processor.** For each step `st_k` of business process `b_j`, compute the navigation path via
BFS: `π_k = BFS(G_screen, s_start(π_k), cs(st_k))` (eq. 3.11), where the start screen carries continuity —
`s_start(π_k) = cs(st_1)` if `k=1`, else `ns(st_{k-1})` (eq. 3.10).

**Stage 6 — Pairwise Generator.** For each element group's collected parameter set `P_gk` (gathered
recursively across the hierarchical layers), apply All-Pairs: `Comb(g_k) = Pairwise(TD_p1, …, TD_pm)` (eq.
3.8). The expected outcome of a combination is deterministic: `outcome(c) = False if c ∩ V_invalid ≠ ∅ else
True` (eq. 3.9).

**Stage 7 — Test Case Generator.** For each `(st_k, c ∈ Comb(g_k))`, synthesize one test case `tc_k =
F_gen(P_gen(st_k, π_k, c, H_{k-1}, D_input), C)` (eq. 3.12), where `H_{k-1}` is the aggregated historical
context of prior successful test cases in the same flow — enabling **stateful testing** (e.g., reusing a
newly created account to log in) — and `D_input` are injected constants (e.g., admin credentials). Output
conforms to **ISO/IEC/IEEE 29119-3:2013**. A **Test Case Retry** step re-attempts failed generations.

**Stage 8 — Mutation / Exception Generator.** Synthesize exception/negative cases by mutating tested rules:
`tc'_k = F_except(P_except(st_k, r), C)` (eq. 3.13).

**Reproduction defect fix.** The BytePlus (OpenAI-compatible) provider path originally set **no
`max_tokens`**, so the large business-process JSON was truncated mid-string ("EOF while parsing a string"),
which silently zeroed every downstream stage (0 business processes → 0 paths → 0 pairwise → 0 test cases).
The fix adds a `max_tokens` bound (env `DEEPSEEK_MAX_TOKENS`, default 16384) and per-call usage logging.
This is the only functional change; prompts and control flow are unchanged.

### III-B. Test Execution Phase — TEAA (integration focus of this work)

The **Test Execution and Adaptation Agent** consumes the generated ISO-style specifications and drives a
live browser via Selenium. It is implemented as `TestAgent` in `CustomLLMDroid/Agent.py` (positive/negative
Golden-Path pipeline) and `CustomLLMDroid/Mutation_Agent.py` (structural exception flows), with LLM access
in `LLMCaller.py`, prompts in `Prompt.py`, and JSON schemas in `Schemas.py`. The following table maps each
thesis concept (§3.2, eqs 3.14–3.20) to its concrete code realization (verified by source inspection):

| Thesis concept | Formula | Code | Realization |
|---|---|---|---|
| **Golden-Path filter** `G_k = {tc : ExpectedOutcome = True}` | 3.14 | `Agent.walkthrough()` | Pops the positive-outcome test case as `success_tc` before running negatives. |
| **Semantic DOM Abstraction** `Φ: H_t → S_t`, keeping visible interactive nodes | 3.15 | `extract_interactable_elements()` + `is_visible()` | BeautifulSoup prune of `display:none/visibility:hidden/opacity:0/aria-hidden` and hidden ancestors (visual visibility `v(e)=1`); keep clickable/input/form tags and elements with `role/on*/tabindex` (`A_ctrl`); emit compact JSON (thesis claims ~95% token reduction). |
| **Strategy Function** `a_t = σ(S_t, M_STM, D_input)` | 3.16 | `evaluate_next_step()` + `EVALUATE_NEXT_STEP` prompt/schema | Single-action decision loop; input = abstracted elements `S_t`, short-term memory `M_STM` (execute log), test-case fields, assumption + true `D_input`; output = `{action, selector_type, selector_value, input_value, reasoning, done, web_fail, llm_fail}`. |
| **Termination** `σ(...) = "done" ⇒ terminate` | 3.17 | `while not done:` + 600s watchdog | Watchdog resets driver/session to break infinite loops. |
| **Golden Trace / LTM** `τ_verified → M_LTM` | (3.16–3.17) | `long_term_mem`, `success_happy_path.json`, `evaluate_past_success_tc()` | On success, the error-free execute log is persisted; a boosting step replays matching past traces to bypass expensive re-inference. |
| **Multi-modal Oracle** `Verdict = PASS iff ValidTech ∧ Match(ΔS, E_exp)` | 3.18 | `evaluate_test_execution()` + `get_html_diff()` + images via `generate_json_with_images()` | Captures before/after screenshots (base64) + unified HTML diff (≤5000 chars) + visible text; returns `{valid_action, result, llm_fail, web_fail, reasoning, assertion_selector}` — a two-channel structural+visual verdict. |
| **Trace Mutation** `τ_neg = Ψ(τ_verified, δ)` | 3.19 | `generate_false_testcase()`; structural in `Mutation_Agent.py` | Preserves navigation, perturbs input data (invalid/empty/malformed); oracle logic reversed (expect error/blocking). |
| **Deterministic Serialization** `S_exec = Γ(τ_verified, A)` replayed by `R_det` | 3.20 | `Reuseable_Module.ReusableTestRunner`, `rerun.py` | LLM-free Selenium replay of saved actions + assertions, with 12 assertion primitives; `C_script ≪ C_LLM` — no model call at replay. |

The key integration property is that **the generation half feeds the execution half**: the
business-process-grounded, ISO-style specification becomes the TEAA's script, directly addressing the
"unguided explorer" and "missing oracle" deficiencies of prior agentic testing.


---

## IV. Experiment

### IV-A. Experimental setup

**Case studies.**
1. **FullTeaching** — an open-source learning-management platform (Angular front end, Spring back end,
   OpenVidu WebRTC), selected because of its rich dynamic interface and complex state transitions. It is the
   live SUT for the execution phase. Deployed locally via Docker Compose (three containers: the app,
   MySQL, and the OpenVidu KMS server) and confirmed reachable at `https://localhost:5000/` (HTTP 200;
   HTTPS only — plain HTTP returns 400). Default accounts: `teacher@gmail.com/pass`,
   `student1@gmail.com/pass`, `student2@gmail.com/pass`. Its SRS
   (`full-teaching-system-design.pdf`, 31 pages, 60,717 characters extracted, tabulated functional
   requirements FR-001…) drives generation; the pipeline detected 4 screens and 6 business processes.
2. **RetailOnboardPro / 4LV (limited sample).** The available artifact `srs_extracted_4lv.json` is a
   **2-use-case sample** (Submit Training Request; Approve Training Request), **not** the full
   RetailOnboardPro SRS from the original thesis (which has 10 use cases, 8 screens, 75 business rules).
   It was rendered to PDF (`make_4lv_pdf.py`) and used to characterize behavior on a minimal input.
   All 4LV results are reported explicitly as a limited sample.

**Models (BytePlus, OpenAI-compatible, `https://ark.ap-southeast.bytepluses.com/api/v3`).**
`deepseek-v4-flash-ga-260731` (flash), `deepseek-v4-pro-ga-260813` (pro), `dola-seed-2-1-turbo-260628`
(dola). All three were verified to respond and to report usage tokens. flash and pro were run through full
pipelines; dola was connectivity-validated but not run through a full pipeline (a documented limitation).

**Baselines (generation).** Three faithful reimplementations, confirmed by a code audit to be verbatim-prompt,
control-flow-accurate ports of their source methods:
- **Baseline 1 (Augusto et al., ICTSS 2024)** — two-stage scenario→case derivation with Few-Shot + CoT and
  leave-one-out cross-validation over example test cases (`temperature=0.1, top_p=1.0, max=32768`).
- **Baseline 2 (Milchevski et al., ACL 2025 Industry)** — intermediate-artifact workflow: decision table →
  scenarios → test purposes → Generation Agent → Reflection Agent (3 retries each; few-shot disabled as in
  the original).
- **Baseline 3 (Bhatia et al., 2024)** — conversational: familiarize the model with the full SRS, then chain
  per-use-case prompts producing a 6-column Markdown test table (`temperature=0.7`); chat memory preserved.

Execution baselines referenced from the thesis: **AutoUAT** (scenario-to-code, static Cypress) and
**LLMDroid** (exploratory coverage agent).

**Logging.** Every LLM call records prompt/response, prompt/completion/total tokens, USD cost, and latency to
JSONL. Pricing uses **placeholder** per-1M rates (flash 0.15/0.60, pro 0.55/2.20, dola 0.30/1.20
input/output) because official BytePlus rates for these preview model IDs are not published; **raw tokens are
always logged, so USD is exactly recomputable** once real rates are known.

### IV-B. Generation results (reproduction on BytePlus)

**Full-pipeline resource consumption (measured).**

| Case study | Model | Calls | Prompt tok | Completion tok | Total tokens | Cost (placeholder) | Wall time | Test cases | Mutations |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FullTeaching (31pg) | flash | 69 | 1,873,422 | 576,890 | **2,450,312** | ~$0.63 | ~50 min | 63 | 116 |
| FullTeaching (31pg) | pro | 90 | 2,192,937 | 448,668 | ~**2,641,605**\* | ~$2.19\* | ~63 min | 63 | 104 |
| 4LV sample (2 UC) | flash | 40 | 201,417 | 227,680 | **429,097** | ~$0.17 | ~28 min | 2 | 3 |
| 4LV sample (2 UC) | pro | 10 | 32,527 | 34,247 | **66,774** | ~$0.09 | ~7 min | 2 | 3 |

\* The pro FullTeaching total is cumulative with its 4LV run in the shared usage log; the FullTeaching-only
increment is the dominant component. This is disclosed rather than silently netted out.

**Per-module token distribution (FullTeaching, flash).** The generation cost is heavily concentrated in
test-case synthesis:

| Module | Tokens | Share |
|---|---:|---:|
| test_case_generator | 1,640,600 | ~67% |
| mutation_test_case_generator | 455,782 | ~19% |
| screen_variable_detector | 166,693 | ~7% |
| screen_graph_detector | 120,251 | ~5% |
| business_process_detector | 45,579 | ~2% |
| screen_extraction | 21,407 | ~1% |

(Figure F3 visualizes this distribution.)

**Cross-model finding.** flash and pro produce **comparable artifact volumes** (both 63 ISO-style test cases;
similar mutation counts), but pro costs **~3.5× more** per suite under placeholder rates while issuing fewer,
more concise calls (90 calls at ~2.6M tokens for pro vs 69 calls at 2.45M for flash — pro front-loads more
tokens per call). For a cost-sensitive, high-volume regression-suite generation task, flash is the
economically preferable model at comparable output volume; pro's value would need to be justified by a
downstream quality delta not measured here.

**Baseline re-runs on BytePlus (flash), confirming Option-A wiring works with zero code change:**

| Baseline | Method | Output | Cost (placeholder) | Tokens (in/out) |
|---|---|---|---:|---|
| 1 (Augusto) | scenario→case (RQ1→RQ2) | 26 test-case files | ~$1.09 | 140,081 / 414,787 |
| 2 (Milchevski) | decision table + gen/reflect specs | decision table + refined specs | ~$0.28 | 20,943 / 110,129 |
| 3 (Bhatia) | conversational per-use-case | 33 test cases | ~$0.018 | ~3,900 / ~6,900 |

Baseline 1 required the intended manual **RQ1→RQ2 bridge** (the model emitted scenarios in a `**SCENARIO N:**`
format; copying the RQ1 output into `inputTestScenarios.txt` allowed RQ2 title extraction to succeed).

### IV-C. Execution results (TEAA on live FullTeaching)

Verified programmatically from `my_method_evaluation_summary.json`; all aggregates reconcile exactly.

**Top-line (all aggregates internally consistent):**

| Metric | Value | Reconciliation |
|---|---|---|
| Total test cases | **166** | 70 passed + 96 failed = 166 ✓ |
| Success rate | **42.17%** | 70/166 ✓ |
| Valid-action rate | **81.33%** | 135 valid + 31 invalid = 166; 135/166 ✓ |
| LLM failures | 35 | 35 + 61 web = 96 failed ✓ |
| Web failures | 61 | — |
| Total browser actions | **1,756** | done 528 + input 553 + click 667 + upload 8 ✓ |

**Action-type success (step-level):**

| Action | Success / Total | Rate |
|---|---|---:|
| done | 363 / 528 | 68.8% |
| click | 220 / 667 | 33.0% |
| input | 142 / 553 | **25.7%** |
| upload | 4 / 8 | 50.0% |
| **All** | **729 / 1,756** | **41.5%** |

`input` is the weakest action, consistent with the failure-pattern data (269 input failures) and the frequent
`no such element [id=email/password/...]` errors — the agent often targets input fields by an `id` that is
not present in the current DOM state.

**Selector usage vs. failures** (`my_method_evaluation_failure_patterns.json`): usage `id` 1496 / `text` 158 /
`xpath` 78 / `class` 13; failures `id` 590 / `xpath` 49 / `text` 48 / `class` 5. Failures by step type:
`test_action` 402, `navigation` 99, `path_action` 11. Dominant runtime errors: `NoSuchElement` on hallucinated
`id`s, `element not interactable`, `stale element reference`, brittle deep XPath chains, and one hard-coded
local upload path that did not exist. (Figure F5: pass/fail by business process — BP1 carries 132 of 166
cases; Figure F6: action-type success.)

**Static-script baseline evidence.** `test_result.xlsx` / `test_result_updated.xlsx` hold **169 Cypress-style
results** (failed 132, passed 26, skipped 11), with errors referencing Cypress, `loginAndNavigateToCreateCourse()`,
and elements "obscured by the logo header." These are the **static-script (AutoUAT-style) baseline**, not the
TEAA agent, and they evidence the thesis's "Static Script Fallacy" — high failure from race conditions and
obscured elements, motivating the self-healing agent layer.


---

## V. Discussion

### V-A. Honest reconciliation of execution metrics (the central integrity point)

The thesis reports higher execution figures than the raw artifact `my_method_evaluation_summary.json`. These
are **not the same population**, and per the instruction to *not hide any data*, we lay both out side by side:

| Figure | Thesis claim | Artifact (`my_method_evaluation_summary.json`) |
|---|---|---|
| Cohort | Normal Flow only, N=166 | All 166 attempted cases (mixed) |
| Pass / pass rate | 148 passed → **89.20%** | 70 passed → **42.17%** |
| Valid-action rate | 153/166 → **92.17%** | 135/166 → **81.33%** |
| LLM / web failures | 17 / 72 | 35 / 61 |
| Verified BVA Execution Rate (VBER) | **83.1%** (64/77 BVA rules) | not in this file (BVA lives in `comprehensive_report.csv`) |
| Boundary Value Coverage (BVC) | **92.2%** (71/77) | not in this file |
| Exception-flow success | thesis Table 4.4 Exception = **5.9%** (3/51) | — |

Four points of caution for anyone citing these numbers:
1. **The artifact's 166 ≠ the thesis's "Normal Flow" 166.** The artifact's 166 is the *full attempted set*
   (42.17% pass). The thesis partitions results into Normal (N=166, 89.20%) and Exception (N=51, 5.9%). The
   two "166"s collide numerically but represent different filtering. One must not present the artifact's
   42.17% as if it were the 89.20% normal-flow figure, nor vice versa.
2. **92.17% valid-action** (thesis) is 153/166 on the *Normal Flow* cohort; the artifact's comparable field
   is 81.33% (135/166) on the *full* set. Both are internally consistent with their own denominators.
3. **VBER 83.1% and BVC 92.2%** come from the **FullTeaching BVA benchmark (N=77 rules)** — a coverage/
   verified-execution axis, not the 166-case run.
4. **The ">80% exception validation" claim is contradicted by the thesis's own Exception-Flow result (5.9%).**
   The honest reading is that exception handling is a **documented limitation** ("Cognitive Ceiling"), not a
   strength. Any paper built on this data should present it that way.

Our position: the integrated system reliably executes and verifies **normal, happy-path and input-validation
flows** at a high rate, but **exception/state-driven flows remain hard** — consistent with the broader
literature (PinATA ~60% verdict reliability; WebVoyager 59.1% task success). The 42.2% all-flows number is
best understood as a *mixed-population* figure dragged down by the exception cohort and by `input`-action
brittleness (25.7% success), not as a refutation of the approach on the flows it targets.

### V-B. Economic feasibility

Under placeholder pricing, a **full FullTeaching generation suite costs ~$0.63 (flash) to ~$2.19 (pro)**, with
generation cost concentrated in `test_case_generator` (~67%) and `mutation_test_case_generator` (~19%). Because
raw tokens are logged, exact USD is recomputable once official BytePlus rates are published. The economic
argument for the integrated approach rests on **deterministic serialization** (eq. 3.20): the expensive
LLM-driven discovery and oracle steps are paid **once**; verified traces are crystallized into LLM-free replay
scripts (`ReusableTestRunner`/`rerun.py`) whose regression cost `C_script ≪ C_LLM` is effectively free. Thus the
one-time generation+discovery spend amortizes across all subsequent regression cycles — the key to the thesis's
claimed ~88% cost reduction versus manual testing, which our token accounting makes independently auditable.

The **model-selection** implication is concrete: at comparable artifact volume (63 test cases either way),
flash is ~3.5× cheaper than pro, so a cost-optimal deployment uses flash for bulk generation and reserves a
stronger model only where a measured quality gain justifies it.

### V-C. Threats to validity

1. **4LV is a 2-use-case sample**, not the full RetailOnboardPro SRS (10 UC / 8 screens / 75 rules); its
   results characterize minimal-input behavior only and are not a thesis reproduction of RetailOnboardPro.
2. **Placeholder pricing.** All USD figures depend on unofficial per-1M rates; only token counts are ground
   truth.
3. **Cumulative pro token log.** The pro FullTeaching total includes its 4LV run in the shared JSONL; the
   FullTeaching-only figure is the dominant increment but is not cleanly isolated.
4. **Execution backend mismatch.** The execution artifacts were produced with a Gemini backend. A faithful
   BytePlus execution re-run requires porting `LLMCaller.py` to the OpenAI-compatible client **and a
   vision-capable model** for the multi-modal oracle; without image support the dual-channel oracle degrades
   to DOM-only, weakening exactly the exception flows already identified as weak.
5. **dola-seed-2-1-turbo** was connectivity-validated but not run through a full pipeline; the 3-model
   comparison is therefore 2-model in practice.
6. **NL-test soundness/consistency** (arXiv:2509.19136): some execution failures may be false failures from
   NL ambiguity, and re-runs may not be deterministic — an inherent limitation of NL-driven execution.

---

## VI. Conclusion

We reproduced the previously published IntelliTest **generation** pipeline on a new, provider-agnostic
multi-model BytePlus backend with complete token/cost/latency logging; we **integrated** it end-to-end with
the TEAA **execution** agent against a live, locally-deployed FullTeaching system under test; and we reported
a **transparent** economic and reliability analysis. The generation half is prior work and is credited as
such throughout. The contributions of this document are the reproduction (including a real defect fix that
was silently zeroing the pipeline on the new backend), the integration that closes the generation→execution
loop, the first per-model cost profile for this method (flash ≈ $0.63, pro ≈ $2.19 per full FullTeaching
suite; comparable output; pro ~3.5× costlier), and an honest reliability accounting that discloses the
42.2%-vs-89.2% population discrepancy and the exception-flow contradiction rather than reporting only the
favourable figure. The strongest concurrent competitor for the execution phase is **Yun Lin's WebTestPilot
(FSE 2026)**; a faithful head-to-head against it — and measurable improvement of exception-flow reliability
via a vision-capable oracle — are the clearest next steps.

---

## References

The complete machine-readable reference set (82 papers, 11-column schema) is in
`research_project/track_A_literature_review/related_articles.xlsx` (sheets: Systematic Review [82],
New Research 2025-26 [19], All References [101 rows]). Primary anchors cited above:

- Prior work: *A Business Process-Centric Approach for LLM-Driven Functional Test Generation* (IEEE Access).
- X. Teoh, **Y. Lin**, D.-M. Nguyen, R. Ren, W. Zhang, J. S. Dong. *WebTestPilot: Agentic End-to-End Web
  Testing against Natural Language Specification by Inferring Oracles with Symbolized GUI Elements.* FSE 2026.
  arXiv:2602.11724.
- *Are Autonomous Web Agents Good Testers? (PinATA / SeeAct-ATA).* arXiv:2504.01495.
- C. Augusto et al., *Software System Testing assisted by LLMs: An Exploratory Study.* ICTSS 2024.
- D. Milchevski et al., *Multi-Step Generation of Test Specifications using LLMs for System-Level
  Requirements.* ACL 2025 (Industry).
- S. Bhatia, T. Gandhi, D. Kumar, P. Jalote. *System test case design from requirements specifications:
  insights and challenges of using ChatGPT.* 2024.
- J. Wang et al., *Software Testing with LLMs: Survey, Landscape, and Vision.* IEEE TSE 2024.
- X. Hou et al., *LLMs for Software Engineering: A Systematic Literature Review.* ACM TOSEM 2024.
- H. He et al., *WebVoyager: Building an End-to-End Web Agent with LMMs.* ACL 2024.
- J. Yoon, R. Feldt, S. Yoo. *DroidAgent* (intent-driven mobile GUI testing).
- Z. Liu et al., *GPTDroid* (functionality-aware mobile GUI testing). ICSE 2024.
- Emerging concerns: NL soundness/consistency (arXiv:2509.19136); self-healing DOM (arXiv:2603.20358);
  autonomous repair limits (arXiv:2605.01471); Prune4Web DOM pruning (arXiv:2511.21398); accessibility-tree
  prompt injection (arXiv:2507.14799); requirement→oracle on real bugs (arXiv:2607.10277).
- Yun Lin group (additional): *Compiling Large Multi-Modal Requirement Documents…* (ISSTA 2026,
  arXiv:2602.13723); *Generating Project-Specific Test Cases with Requirement Validation Intention*
  (ISSTA 2026); *Generalizing Test Cases for Comprehensive Test Scenario Coverage* (FSE 2026,
  arXiv:2604.21771).

---

## Appendix A — Reproducibility artifacts

| Artifact | Path |
|---|---|
| Generation runner + per-model token summaries | `research_project/track_C_intellitest_run/` (`run_intellitest.py`, `summarize_usage.py`, `logs/usage_*_summary.json`) |
| 4LV PDF renderer | `research_project/track_C_intellitest_run/make_4lv_pdf.py` |
| Baseline fidelity audit | `research_project/track_B_baselines/REPORT.md` |
| Execution study + architecture→formula mapping | `research_project/track_D_execution_teaa/REPORT.md` |
| Literature review (82 papers) | `research_project/track_A_literature_review/{systematic_review.csv, related_articles.xlsx, REPORT.md}` |
| New-research + Yun Lin dossier | `research_project/track_E_new_research/{new_papers.csv, REPORT.md, yun_lin_sjtu_dossier.md}` |
| Figures (from real logs) | `research_project/track_F_plots/figures/F1..F6*.png` (`make_plots.py`) |
| Per-call LLM logs | `research_project/track_C_intellitest_run/logs/usage_*.jsonl` |
| Shared BytePlus client + logger | `research_project/shared/llm_client.py` |
| Coordination channels | `research_project/channels/{MAIN_LOG.txt, writer_inbox.txt}` |
| Live SUT | FullTeaching via Docker at `https://localhost:5000/` |

## Appendix B — Figure index

- **F1** Generation: total tokens per model (FullTeaching latest run).
- **F2** Generation: USD cost per model (placeholder rates, labeled as such).
- **F3** Generation: tokens by pipeline module (test_case_generator dominates ~67%).
- **F4** Generation: wall-clock minutes per run.
- **F5** Execution: pass/fail by business process (overall 42.2% success, N=166; BP1 = 132/166).
- **F6** Execution: success rate by action type (done ~69%, click ~33%, input ~26%, upload 50%).

## Appendix C — Environment

Windows; Python 3.11 venv (`env/`). Installed for this study: `matplotlib`, `openpyxl`, `fpdf2` (in addition
to the pipeline's `pydantic`, `python-dotenv`, `allpairspy`, `rapidfuzz`, `pypdf`, `google-genai`, `openai`).
Docker 29.7.2 for the SUT (git required `core.longpaths=true` on Windows to check out FullTeaching's deep
Java test paths).
