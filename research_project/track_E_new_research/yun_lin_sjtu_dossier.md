# Yun Lin (林云, SJTU) — Directly-Related Researcher Dossier

**Requested by supervisor: "find the one named Yun Lin from SJTU, he has the same research direction."**

## Who
Dr. LIN, Yun (林云) — Associate Professor & Deputy Head, Dept. of Computer Science
and Technology, School of Computer Science, **Shanghai Jiao Tong University (SJTU)**.
Formerly Research Assistant Professor at NUS with Prof. Jin Song Dong (PAT group).
Homepage: http://www.linyun.info/  ·  Email: lin_yun@sjtu.edu.cn  ·  Group: CoPhi.
Research: automatic programming, explainable AI, web misinformation, software testing.

## Why he matters to THIS paper
His group works on **exactly the two halves of our thesis** — LLM/agentic test
GENERATION from requirements AND autonomous E2E web test EXECUTION with oracles.
Several 2025-2026 papers are the closest prior art and must be cited (some are
strong candidate comparison points / competing methods for the execution half).

## Most relevant papers (add to references)

1. **WebTestPilot: Agentic End-to-End Web Testing against Natural Language
   Specification by Inferring Oracles with Symbolized GUI Elements** — FSE 2026.
   Authors: Xiwen Teoh, **Yun Lin**, Duc-Minh Nguyen, Ruofei Ren, Wenjie Zhang,
   Jin Song Dong. arXiv:2602.11724.
   * THE closest prior art to our EXECUTION (TEAA) phase. A neurosymbolic LLM agent
     that (1) symbolizes critical GUI elements into variables and (2) translates an
     NL spec into steps each equipped with inferred PRE/POST-CONDITION ORACLES over
     those symbols, capturing data/temporal/causal dependencies.
   * Directly attacks the same problems our thesis names: the "implicit oracle
     inference" problem and the "probabilistic inference / hallucination" problem
     (distinguishing a real bug from an LLM hallucination). Builds a bug-injected
     web-app benchmark. Reports 99% task completion, 96% precision, 96% recall in
     bug detection (+70 precision / +27 recall over the best baseline).
   * WRITER ACTION: cite as primary related work for the execution phase; contrast
     TEAA's DOM-abstraction + golden-trace + multi-modal oracle against
     WebTestPilot's symbolization + inferred pre/post-condition oracle. This is
     likely the single most important comparison for the execution contribution.

2. **Compiling Large Multi-Modal Requirement Documents into Runnable Software
   Systems: From an Agentic Test-Driven Perspective** — ISSTA 2026. arXiv:2602.13723.
   * Agentic, test-driven handling of LARGE multi-modal requirement documents —
     resonates with our SRS-driven generation and the "context amnesia at scale"
     problem. Cite in generation + document-maturity discussion.

3. **Generating Project-Specific Test Cases with Requirement Validation Intention**
   — ISSTA 2026 (Binhang, Xinyi, Yuhuan, Chenyan; group of Yun Lin).
   * Requirement-intention-driven test generation; aligns with our
     requirement-grounded, business-process-centric generation. Cite in generation.

4. **Generalizing Test Cases for Comprehensive Test Scenario Coverage** — FSE 2026.
   arXiv:2604.21771. TestGeneralizer: requirement/scenario understanding -> scenario
   template -> instances -> executable tests. Cite for coverage/scenario generation.

5. **Design-to-action agents for GUI testing** — ISSTA 2025 (Ruofan, Xiwen, et al.).
   * Agentic GUI testing (design intent -> actions). Cite for agentic execution lineage.

6. Foundational testing lineage (older, for methodology grounding): "Towards Optimal
   Concolic Testing" (ICSE'18, ACM Distinguished Paper); search-based unit testing
   (ESEC/FSE'21, ISSTA'20); regression localization/explanation (TSE'19, ICSE'17).

## One-line framing for the paper
Yun Lin's WebTestPilot (FSE'26) is the strongest concurrent competitor to the
IntelliTest EXECUTION phase: both turn an NL/requirement spec into an autonomously
executed web test with an inferred oracle. Our differentiation = business-process
graph grounding from the GENERATION half feeding execution + golden-trace memory +
multi-modal (DOM+visual) oracle + trace mutation, evaluated with token/cost economics.
