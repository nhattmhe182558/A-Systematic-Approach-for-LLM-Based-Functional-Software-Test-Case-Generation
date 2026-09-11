# Track E — New-Research Findings Report

**Scope:** Net-new (≈2025–2026) literature that appeared *after* the prior published work
*"A Business Process-Centric Approach for LLM-Driven Functional Test Generation"* (IEEE Access, ~9 months old),
which covers only the **generation** half. This report grounds the full **"IntelliTest"** thesis:
LLM-based functional test-case **GENERATION** + autonomous test **EXECUTION** (UAT agents).

> Note: All papers below are real and were located via web search of arXiv/ACM/IEEE/venue pages.
> Author lists and exact venue/acceptance status that could not be confirmed from the search
> snippets are marked **[estimated]**. arXiv IDs with a `26xx` prefix denote 2026-dated preprints.

---

## 1. The single most important shift since the prior work: from GENERATION to EXECUTION

The prior IEEE Access paper stops at *producing* functional test cases from business processes.
The dominant net-new trend in 2025–2026 is that the community has moved the frontier to the
**autonomous execution + verdict** stage — precisely the new contribution of the IntelliTest paper.
Concretely, four sub-trends have emerged that did **not** exist (or were immature) 9 months ago:

1. **Autonomous Test Agents (ATAs) that execute NL test cases and issue verdicts.**
   *Are Autonomous Web Agents Good Testers?* (PinATA / SeeAct-ATA, arXiv:2504.01495) is the
   canonical reference: LLM agents execute manual natural-language test cases against real web
   apps and return pass/fail verdicts (~60% correct verdict, up to 94% specificity). This is
   the exact "second half" the new paper claims.

2. **Reliability / soundness of NL-driven execution is now a named research problem.**
   *On the Soundness and Consistency of LLM Agents for Executing Test Cases Written in Natural
   Language* (arXiv:2509.19136) formalizes that NL test execution is *unsound* (false failures
   from ambiguous instructions) and *inconsistent* (nondeterministic re-runs). The new paper's
   execution half must address this as a threat to validity.

3. **Self-healing execution and autonomous test repair.**
   *A Zero-Cost Self-Healing Approach Using DOM Accessibility Tree Extraction* (arXiv:2603.20358)
   and *Practical Limits of Autonomous Test Repair* (arXiv:2605.01471) show that brittle-locator
   recovery and self-correction during execution are active, measurable areas (e.g., 70% repair
   convergence, mean 4.4 iterations). This directly motivates and bounds the execution contribution.

4. **DOM / accessibility-tree abstraction as the interface for execution agents.**
   *DOM Tree Pruning Programming for Web Agent* (Prune4Web, arXiv:2511.21398) programmatically
   prunes 10k–100k-token DOMs; the self-healing paper uses accessibility-tree extraction; and
   *Manipulating LLM Web Agents ... via HTML Accessibility Tree* (arXiv:2507.14799) adds a security
   threat model. DOM abstraction is now a first-class execution concern, not an afterthought.

---

## 2. What is genuinely new in the field (by theme)

### A. Autonomous web/UAT execution agents (the new frontier)
- **PinATA / SeeAct-ATA** (2504.01495): LLM ATAs execute manual NL tests and give verdicts; quantifies limits.
- **Autonomous NL-Driven Web Execution + Security Assurance** (2605.15281): NL→Selenium execution, script success 55%→93%, 8× fewer navigation failures, 75% less authoring time.
- **WebProber — AI Agents for Web Testing** (2509.05197): URL-in → autonomous exploration, bug/usability detection, human-readable report.
- **HxAgent** (2608.15491): iterative planning for E2E web testing; strong MiniWoB++/real-task accuracy, beats WALT.
- **CAT — Code-Driven Agentic Testing** (2609.00081): agent writes Playwright code to drive the browser and explore for bugs; ships a **benchmark**.

### B. Multi-agent testing architectures
- **ScenGen** (2506.05079): 5 agents (Observer/Decider/Executor/Supervisor/Recorder) — a perceive→decide→execute→verify loop grounded in app business logic.
- **CANDOR** (2506.02943): multi-agent JUnit generation with **consensus-based oracle** to fight hallucination.
- **TestAgent** (2607.09101): human-testing-inspired multi-agent unit-test workflow.
- **Agent-Based Test Assertion Generation via Diverse Perspective Aggregation** (2608.05822).

### C. Oracle / verdict techniques (critical for autonomous execution)
- **From Business Requirements to Test Assertions** (2607.10277): evaluates requirement→oracle path on real bugs; oracles align more with requirements than with the SUT and show high variance — a direct caution for requirement-driven generation like the prior work.
- **KuiTest** (2025): knowledge-in-the-wild as GUI oracle where no executable spec exists.
- **Fail-Aware and Explainable Test Oracle Prediction** (2607.11342).

### D. DOM abstraction & agent perception
- **Prune4Web** (2511.21398): LLM-generated Python pruning scripts for huge DOMs.
- **DOM Accessibility Tree self-healing** (2603.20358): structured accessibility-tree extraction.
- **HTML Accessibility Tree prompt injection** (2507.14799): security threat to accessibility-tree-based agents.

### E. Story → executable acceptance tests (generation↔execution bridge)
- **AutoUAT + Test Flow** (2504.07244): user story → Gherkin → executable Cypress; industrially validated.
- **The Potential of LLMs in Automating Software Testing** (2501.00217): generation + execution + reporting in one agentic loop.
- **Evaluating LLMs for Multimodal GUI Test Generation in Android** (SAST 2025): recent multimodal model comparison.

---

## 3. Trends the NEW paper should explicitly acknowledge

Especially for the **execution half** (the new contribution):

1. **Position IntelliTest against ATAs.** Cite PinATA/SeeAct-ATA (2504.01495) as the closest prior
   art on autonomous execution+verdict, and differentiate (e.g., business-process grounding,
   generation→execution integration, higher verdict reliability).
2. **Confront soundness/consistency head-on** (2509.19136): report determinism/flakiness of the
   execution agent and mitigations (multiple runs, consensus verdicts, deterministic locators).
3. **Include self-healing + repair limits** (2603.20358, 2605.01471) as both a feature and a
   bounded expectation — avoid over-claiming full autonomy.
4. **Justify the DOM/accessibility-tree abstraction** choice with Prune4Web (2511.21398) and the
   accessibility-tree self-healing work; acknowledge the prompt-injection security risk (2507.14799).
5. **Treat the oracle problem as unsolved.** Use 2607.10277 / CANDOR (2506.02943) to argue for a
   consensus/multi-perspective or requirement-grounded oracle and to state accuracy caveats.
6. **Adopt or compare against an agentic testing benchmark** (CAT, 2609.00081; WebArena-family) so
   the execution evaluation is comparable to concurrent work.
7. **Acknowledge the generation half is now crowded** (multi-agent generation: CANDOR, TestAgent,
   ScenGen) — the differentiator is the *end-to-end* generation→execution loop, not generation alone.

---

## 4. Gap the new paper fills

No single 2025–2026 work combines **(a)** business-process/requirement-grounded functional test
**generation** with **(b)** an **autonomous UAT execution agent** that runs the generated cases,
self-heals locators over a DOM abstraction, and issues reliable verdicts — while **(c)** empirically
addressing the soundness/consistency and oracle-reliability problems that the execution literature
above has only recently named. The prior IEEE Access paper covers only (a). The new contribution is
the integrated (a)+(b)+(c) pipeline.

---

*Prepared by Track E (new-research). Companion machine-readable data: `new_papers.csv`.*
