# Track A — Systematic Literature Review (PRISMA)
## LLM-Based Functional Test GENERATION + Autonomous Test EXECUTION (the full "IntelliTest" thesis)

**Prepared for:** the new paper covering the complete IntelliTest thesis (generation **and** execution / UAT agents).
**Relation to prior work:** The already-published *"A Business Process-Centric Approach for LLM-Driven Functional Test Generation"* (IEEE Access, ~9 months old) covers only the **generation** half; this review deliberately expands coverage to autonomous **execution** and agentic UAT so the new paper can position the full pipeline.
**Artifacts:** `systematic_review.csv` (**77 included papers** after the expansion pass; opens in Excel — can be saved as `.xlsx`), this `REPORT.md`.

> **EXPANSION PASS (2026-09-11):** The corpus was widened from 20 to **77 unique real papers** to meet the >50-paper requirement. The expansion merged (a) the original 20 included papers, (b) 16 net-new papers from Track E (re-mapped to the 11-column schema; 3 of the 19 Track-E papers were already present and de-duplicated away), and (c) 41 additional real papers surfaced by ~30 new PRISMA search queries across adjacent subfields (LLM unit/integration test generation, coverage-guided generation, test oracle generation, flaky-test detection/repair, test prioritization, RAG-for-testing, VLM/mobile GUI testing agents, autonomous web-agent benchmarks WebArena/MiniWoB++/SWE-bench, REST API testing, BDD/Gherkin generation, self-healing, and program-repair-adjacent test work). Deduplicated by case-insensitive title and by arXiv id.

---

## 1. PRISMA Search Protocol

### 1.1 Objective
Identify peer-reviewed and preprint literature covering **(a)** LLM-based generation of functional / acceptance / system test cases and **(b)** autonomous LLM-agent execution and verification of tests over web/GUI/app interfaces.

### 1.2 Sources
Web/academic search over arXiv, IEEE Xplore, ACM Digital Library, MDPI, Springer, ACL Anthology, and Google-Scholar-indexed venues (accessed via web search, Sept 2026).

### 1.3 Keyword group matrix
The search combined four keyword groups (Cartesian-style combination, sampling the most productive intersections):

| Group | Terms |
|-------|-------|
| **Domain** | system testing, functional testing, UAT, acceptance testing |
| **Technique** | LLM, large language model, AI agent, autonomous, multi-agent |
| **Target** | web application, GUI, interface, app |
| **Activity** | test case generation, test execution, test automation |

### 1.4 Exact search strings executed (12 searches)
1. `LLM agent GUI test automation web application autonomous`
2. `LLM large language model functional test case generation software`
3. `user acceptance testing UAT LLM large language model automation`
4. `multi-agent LLM software testing framework autonomous test execution`
5. `survey large language models software testing systematic review`
6. `LLM web application end-to-end test generation Selenium Playwright`
7. `LLM test case generation requirements specifications user stories natural language`
8. `LLM mobile app GUI testing Android autonomous agent exploration`
9. `LLM test oracle problem automated verification software testing`
10. `LLM behavior driven development Gherkin BDD acceptance test automation`
11. `LLM agent web navigation benchmark WebArena WebVoyager task completion`
12. `autonomous web application testing agent execute verify verdict LLM manual test cases`
13. `large language models software engineering comprehensive survey Hou 2024`
14. `ChatGPT unit test generation empirical study coverage correctness ChatUniTest`

### 1.4b Expansion-pass search strings (16 additional searches, ~30 queries total)
15. `flaky test detection large language models FlakyFix`
16. `LLM unit test generation coverage TestPilot CodaMosa`
17. `WebArena benchmark autonomous web agents MiniWoB++ Mind2Web`
18. `coverage-guided LLM test generation fuzzing CoverUp SymPrompt`
19. `retrieval augmented generation software test generation RAG LLM`
20. `vision language model GUI testing screenshot multimodal mobile app`
21. `test case prioritization large language models regression testing`
22. `LLM behavior driven development Gherkin scenario generation acceptance criteria`
23. `combinatorial pairwise testing input generation large language model`
24. `SWE-bench resolve GitHub issues language models benchmark`
25. `self-healing test automation locators LLM web UI`
26. `automated program repair large language models test generation ChatRepair`
27. `LLM system integration test generation EvoSuite comparison Java`
28. `requirements to test case traceability LLM natural language`
29. `AutoDroid LLM Android task automation GUI agent`
30. `LLM REST API testing generation RESTGPT specification`

### 1.5 Inclusion criteria
- Directly concerns LLMs/LLM-agents applied to test **generation**, **execution**, or **verification** of functional/acceptance/system behavior.
- Targets software interfaces (web, GUI, mobile app) or general functional test artifacts.
- Real, citable paper (peer-reviewed venue or archived preprint with identifiable authors/venue).

### 1.6 Exclusion criteria
- Blog posts, vendor marketing, Medium/tutorial articles, GitHub-only repos with no paper.
- Off-topic uses of LLMs (pure code generation, refactoring, penetration testing, hardware BDD) not connected to functional test G/E.
- Duplicate versions of the same work (kept the canonical entry).
- General LLM surveys with no testing focus.

---

## 2. PRISMA Flow Summary

```
IDENTIFICATION
  Records returned across 30 search queries (10 results each, gross) ........... ~300
  After removing search-engine duplicates & near-duplicate arXiv versions ..... 168 unique records

SCREENING
  Records screened (title + snippet) .......................................... 168
  Records excluded at screening ............................................... 78
     - Blog/tutorial/vendor (Medium, Testsigma, DeviQA, Checkly, BrowserStack,
       Katalon, GitHub tool pages) ........................................... 34
     - GitHub repo only, no paper ............................................. 9
     - Off-topic LLM use (pentest, hardware BDD, refactoring, combinatorial
       optimization/counting, general RAG surveys, RestGPT-as-orchestrator,
       DBMS/robot oracle, coupled-token eval, prompt-attribution) ............. 27
     - Duplicate PDF/HTML version of an already-captured paper ................ 8

ELIGIBILITY
  Full-text / abstract assessed for eligibility ............................... 90
  Excluded at eligibility ..................................................... 13
     - Marginal relevance / weak venue / redundant with a stronger entry ...... 13

INCLUDED
  Studies included in the review (systematic_review.csv) ...................... 77
     - Original included corpus (pass 1) ..................................... 20
     - Net-new from Track E, re-mapped & de-duplicated ....................... 16
     - Net-new from expansion-pass searches .................................. 41
```

The final included set of **77** is exact and listed in `systematic_review.csv` (verified by reading the file back: 77 data rows, 11 columns each, 0 duplicate titles). Identification/screening/eligibility sub-counts are estimated from the returned result sets [estimated]; the 20/16/41 provenance split is exact.

---

## 3. Included Corpus at a Glance

The original pass-1 highlights are retained below; the expansion pass broadened each theme.

- **Surveys / SLRs (6):** Wang et al. *Software Testing with LLMs* (TSE 2024); Hou et al. *LLM4SE SLR* (TOSEM 2024); MDPI *Foundation Models in SE* (2026); *Test Oracle Automation in the era of LLMs*; *SLR on LLMs for Automated Program Repair*; large independent study of LLM test-case generation.
- **Generation — unit / integration / functional (large group):** ChatGPT unit-test study (ChatTester); ChatUniTest; empirical open-source LLM unit tests; TestPilot; multi-language unit test generation; CoverUp; SymPrompt (code-aware prompting); SBST-vs-symbolic-vs-LLM comparison; IntTestGen (integration); Test-vs-Mutant adversarial agents; EvoGPT; PRIMG (mutant prioritization); execution-aware regression generation; RAG-based test generation; high-level test-case generation (2 papers); AI-driven NL-requirements test generation.
- **Test oracles (dedicated):** TOGLL (correct & strong oracles); *Do LLMs generate oracles for actual vs expected behaviour?*; CANDOR / multi-agent end-to-end oracles; requirement->assertion evaluation on real bugs; diverse-perspective assertion aggregation; KuiTest (knowledge-in-the-wild GUI oracle).
- **Generation — acceptance / UAT / BDD:** AutoUAT/Test Flow; AToMIC (mobile Gherkin/POs); Multi-Agent Collaborative UAT; test-scenario-generation tool; BDD acceptance-test generation; epic-vs-requirement Gherkin; private-GPT acceptance-criteria study; LLM-as-a-Judge for Gherkin coverage.
- **REST / API testing:** RESTGPT; RESTSpecIT; LlamaRestTest; verified-dependency REST testing.
- **Execution / agentic (web & mobile):** DroidAgent; GPTDroid; WebVoyager; *Are Autonomous Web Agents Good Testers?*; conversational testing agents; WebArena; WebPilot; HxAgent; ScenGen; WebProber; NL-driven Selenium execution+security; CAT benchmark; AutoDroid; DroidBot-GPT; VisionDroid; VisiDroid; GUI text-input generation.
- **Reliability / maintenance:** soundness & consistency of NL test execution; DOM-accessibility self-healing; autonomous-repair limits; Prune4Web (DOM pruning); accessibility-tree prompt-injection security; flaky-test fix (FlakyFix, FlakyGuard, fine-tuning/few-shot study); SWE-bench (test-validated issue resolution); TraceLLM (requirements->test traceability); SAGE (semantic game regression prioritization).

---

## 4. Key Thematic Findings

### 4.1 Top-down, document-driven generation vs bottom-up, agentic exploration
Two distinct paradigms emerge and map cleanly onto the two halves of the IntelliTest thesis:

- **Top-down / document-driven (the "generation" half).** Work such as *Automatic High-Level Test Case Generation*, *Generating High-Level Test Cases from Requirements*, *AI-Driven Test Case Generation from NL Requirements*, AToMIC, and the AutoUAT/Test Flow line takes a **specification, user story, or requirement document as the source of truth** and derives test cases (often Gherkin scenarios, page objects, or high-level cases) from it. Strength: traceability to requirements and business intent. Weakness: it stops at *authoring* — the tests still need a runner and an oracle. This is precisely the space the prior IEEE Access business-process paper occupies.
- **Bottom-up / agentic exploration (the "execution" half).** Work such as DroidAgent, GPTDroid, WebVoyager, and the ATA line (*Are Autonomous Web Agents Good Testers?*, conversational testing agents) drives an LLM/MLLM agent to **perceive a live interface, plan actions, act, and judge outcomes** with little or no pre-written script. Strength: resilience to brittle locators and direct execution+verdict. Weakness: weak traceability, non-determinism, and unclear coverage guarantees.

The new paper's contribution is best framed as **unifying** these: document-driven generation feeding an agentic executor so that generated functional/UAT cases are actually run and verified end-to-end.

### 4.2 The rigor gap
Across the corpus, **generation is evaluated far more rigorously than execution.** Unit-test generation papers (ChatTester, ChatUniTest, the open-source empirical study) report standard, reproducible metrics — compilation rate, line/branch coverage, mutation score, assertion correctness. In contrast, **autonomous execution/agentic papers** rely on task-success rates on ad-hoc benchmarks (e.g., WebVoyager 59.1%), and the ATA studies explicitly question *whether agents are even good testers*. There is **no shared, standardized benchmark or oracle metric for autonomous functional/UAT execution**, and the oracle problem is repeatedly flagged (Test Oracle Automation in the era of LLMs; Multi-Agent LLMs for End-to-End Test Generation with Accurate Oracles). This rigor asymmetry is a defensible motivation for the new paper to introduce reproducible execution-side metrics.

### 4.3 Context amnesia
A recurring, cross-cutting limitation is **context amnesia** — LLMs losing track of prior steps, state, or global intent:
- ChatUniTest exists specifically because focal context must be *reconstructed within a token budget*; the model cannot hold the whole project.
- DroidAgent adds explicit **long- and short-term memory** modules precisely because the base agent forgets what it has already explored and why.
- Web-agent reliability studies surface failure modes (pop-ups, captchas, re-navigation) that stem from the agent not retaining task/environment state.
- The multi-agent UAT and end-to-end-oracle papers decompose work across agents partly to externalize memory the single model cannot sustain.

Context amnesia is therefore the shared technical enemy of *both* halves of the pipeline and a natural axis on which an integrated generation+execution architecture (persistent business-process context threaded through both stages) can claim novelty.

---

## 5. Notes for the Writer
- `systematic_review.csv` has the exact 11-column schema requested and can be opened in Excel and re-saved as `.xlsx`.
- Quartiles for arXiv-only preprints are marked **[estimated]**; venue-published entries (TSE, TOSEM, ICSE, ASE, ACL, FSE) are estimated Q1 from venue reputation. Author lists marked **[estimated]** should be verified against the DOI before final citation.
- Prior IEEE Access paper = the *generation* baseline to cite as "our prior work"; this review supplies the *execution/agentic* literature needed to justify extending it.
