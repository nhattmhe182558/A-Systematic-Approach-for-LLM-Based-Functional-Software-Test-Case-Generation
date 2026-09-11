# A Systematic Approach for LLM-Based Functional Software Test Case Generation and Autonomous Execution

This repository reproduces and extends the **IntelliTest** research: an approach that pairs Large
Language Models (LLMs) with deterministic Specification-Based Testing (Equivalence Partitioning,
Boundary Value Analysis, Pairwise Testing) to generate high-coverage functional test suites from a
Software Requirements Specification (SRS), and then autonomously **executes** those tests against a
live web application.

> **What is prior work vs. what is new here.**
> The **generation pipeline** (`intellitest/`) and the three **baselines** (`baseline_1/2/3/`) are
> reproductions of already-published work. The contribution of the `research_project/` folder is:
> (1) reproducing generation on a new **multi-model BytePlus backend** with full token/cost/latency
> logging, (2) an **end-to-end integration** with the execution agent against a live system under
> test, and (3) a **transparent literature review + economic/reliability analysis**. See
> `research_project/writer/PAPER.md` for the full write-up (also as `.docx` and `.tex`).

---

## Repository layout

```
.
├── intellitest/                 # Generation pipeline (8-stage, provider-agnostic). PRIOR WORK.
│   ├── main.py                  #   end-to-end orchestrator + CLI
│   ├── models.py                #   Pydantic schemas, BFS, LLMProvider (Gemini/DeepSeek/BytePlus)
│   ├── prompts.py               #   all stage prompts
│   ├── config.py                #   paths, model config, thread/batch settings
│   └── .env.example
│
├── baseline_1/                  # Augusto et al. (ICTSS 2024) — scenario→case. PRIOR WORK.
├── baseline_2/                  # Milchevski et al. (ACL 2025) — decision table + agents. PRIOR WORK.
├── baseline_3/                  # Bhatia et al. (2024) — conversational per-use-case. PRIOR WORK.
│
├── web_testing_capstone_enhance-nhat/   # Execution phase (TEAA agent). Gemini + Selenium.
│   └── CustomLLMDroid/          #   TestAgent, Mutation_Agent, LLMCaller, Prompt, Schemas
│                                #   (large raw artifacts are git-ignored; see Track D report)
│
├── research_project/            # THIS WORK: reproduction, integration, analysis, paper.
│   ├── channels/                #   MAIN_LOG.txt (timeline) + writer_inbox.txt (track→writer reports)
│   ├── shared/llm_client.py     #   unified BytePlus client + per-call token/cost/latency logger
│   ├── track_A_literature_review/  # PRISMA review: systematic_review.csv, related_articles.xlsx (82 papers)
│   ├── track_B_baselines/       #   baseline fidelity audit (REPORT.md)
│   ├── track_C_intellitest_run/ #   run_intellitest.py, summarize_usage.py, make_4lv_pdf.py, logs/
│   ├── track_D_execution_teaa/  #   execution-phase study (REPORT.md); full-teaching/ SUT (git-ignored)
│   ├── track_E_new_research/    #   new-papers.csv + Yun Lin (SJTU) dossier
│   ├── track_F_plots/           #   make_plots.py + figures/ (F1–F6, from real logs)
│   └── writer/                  #   PAPER.md / PAPER.docx / PAPER.tex
│
├── env/                         # Python 3.11 virtualenv (git-ignored)
├── .env                         # secrets — API keys (git-ignored; create locally)
└── .gitignore
```

---

## Setup

Requires **Python 3.11** and (for the execution SUT) **Docker**.

```bash
# 1. Virtual environment
python -m venv env
env\Scripts\activate            # Windows
# source env/bin/activate       # Linux/macOS

# 2. Dependencies (generation pipeline)
pip install -r intellitest/requirements.txt
# plus analysis tooling used by research_project:
pip install matplotlib openpyxl fpdf2

# 3. Secrets — create .env at the PROJECT ROOT (never commit this file)
```

`.env` (root) for the **BytePlus** backend used in this study:

```dotenv
BYTEPLUST_API_KEY="your-byteplus-ark-key"
BASE_URL="https://ark.ap-southeast.bytepluses.com/api/v3"
DOLA_SEED_2_1="dola-seed-2-1-turbo-260628"
DEEPSEEK_V4_PRO="deepseek-v4-pro-ga-260813"
DEEPSEEK_V4_FLASH="deepseek-v4-flash-ga-260731"
```

The pipeline is **provider-agnostic**. It also runs on Gemini (`GEMINI_API_KEY`) or DeepSeek-direct
(`DEEPSEEK_API_KEY`) — see `intellitest/.env.example`.

---

## How to run

### 1. Generation pipeline (produces the test suite)

Direct:
```bash
cd intellitest
python main.py --pdf input/your-srs.pdf --provider gemini
```

On **BytePlus** with full token/cost/latency logging (recommended; via the Track C runner):
```bash
cd research_project/track_C_intellitest_run
python run_intellitest.py --model DEEPSEEK_V4_FLASH --pdf ../../web_testing_capstone_enhance-nhat/full-teaching-system-design.pdf
python summarize_usage.py logs/usage_DEEPSEEK_V4_FLASH.jsonl   # token/cost report
```
The runner points the pipeline's OpenAI-compatible provider at BytePlus (env only, no code change),
snapshots artifacts into `runs/<model>__<doc>/`, and writes per-call usage to `logs/usage_<model>.jsonl`.
Output stages: `screens → business_processes → screen_variables → screen_graph → paths → pairwise →
test cases → mutations` under `intellitest/output/<doc>/`.

### 2. Baselines (comparison methods)

All three run on BytePlus via the same env wiring (`--provider deepseek` pointed at BytePlus):
```bash
# set DEEPSEEK_API_KEY=<byteplus key>, DEEPSEEK_BASE_URL=<byteplus url>, DEEPSEEK_MODEL=<byteplus id>
cd baseline_3 && python main.py --provider deepseek                       # Bhatia
cd baseline_2 && python main.py --provider deepseek --requirements input/requirements.txt   # Milchevski
cd baseline_1 && python main.py --stage all --provider deepseek           # Augusto (RQ1→RQ2)
```
Note for baseline_1: RQ2 reads scenarios from `input/inputTestScenarios.txt`; if empty, copy the RQ1
output there first (the two stages are decoupled for manual scenario selection).

### 3. Execution phase — deploy the SUT and run the agent

Deploy **FullTeaching** (the system under test):
```bash
cd research_project/track_D_execution_teaa
git clone https://github.com/elastest/full-teaching.git   # (Windows: git config core.longpaths true)
cd full-teaching/application/docker-compose
docker compose up -d
# App is served at https://localhost:5000/  (HTTPS; accounts teacher@gmail.com/pass, student1@gmail.com/pass)
```
The execution agent (`web_testing_capstone_enhance-nhat/CustomLLMDroid/`) is **Gemini-based + Selenium
+ multimodal**. To run it as-is, put a `GEMINI_API_KEY` in that folder's `.env`. To run it on BytePlus
you must port `LLMCaller.py` to the OpenAI-compatible client **and use a vision-capable model** (the
oracle sends screenshots) — see `research_project/track_D_execution_teaa/REPORT.md`.

### 4. Regenerate the figures and the reference workbook

```bash
cd research_project/track_F_plots && python make_plots.py             # F1–F6 from real logs
cd research_project/track_A_literature_review && python build_references_xlsx.py   # related_articles.xlsx
```

### 5. Regenerate the paper in DOCX / LaTeX (requires pandoc)

```bash
cd research_project/writer
pandoc PAPER.md -o PAPER.docx --toc --toc-depth=3
pandoc PAPER.md -o PAPER.tex  --standalone --toc --toc-depth=3 -V geometry:margin=1in
```

---

## Key results (measured, logged)

- **Generation, FullTeaching SRS (31pg):** flash = 2,450,312 tokens / 69 calls / ~$0.63 / ~50 min →
  63 test cases + 116 mutations. pro = ~2.6M tokens / 90 calls / ~$2.19 / ~63 min. Comparable output;
  pro ~3.5× costlier. `test_case_generator` dominates token use (~67%).
- **Execution, FullTeaching (from authors' artifacts):** 166 test cases, 42.2% all-flows success,
  81.3% valid-action rate, 1,756 actions. `input` is the weakest action (25.7%).
- **Honest caveat:** the 42.2% all-flows figure differs from the thesis's 89.2% *normal-flow* headline
  (different populations); the exception-flow figure (5.9%) contradicts the thesis's ">80%" claim.
  Both are reported; nothing is hidden. See `PAPER.md` §V-A.
- **Pricing is placeholder** (official BytePlus rates for these preview models are unpublished); raw
  tokens are logged so USD is recomputable.

---

## Our take on this code

**Strengths.** The generation pipeline is a clean, provider-agnostic reimplementation that faithfully
mirrors the published method (8 stages, EP/BVA/Pairwise, BFS navigation, ISO-style output). The three
baselines are verbatim-prompt ports of their source papers, so comparisons are fair. The execution
agent (TEAA) is a genuine end-to-end system (Semantic DOM abstraction, golden-trace memory, multi-modal
oracle, trace mutation, deterministic replay) that maps cleanly onto the thesis formulas.

**Weaknesses / things to know before trusting it.**
- The BytePlus provider path had a real bug: it set no `max_tokens`, silently truncating the
  business-process JSON and zeroing every downstream stage. Fixed in `intellitest/models.py`
  (`DEEPSEEK_MAX_TOKENS`, default 16384). Watch for the same pattern on any new provider.
- Generation is **expensive and slow** on a full SRS (~2.5M tokens, ~1 hour) — dominated by test-case
  synthesis. Budget accordingly.
- The execution agent leans on element `id`s that the LLM sometimes hallucinates, so `input` actions
  fail often (25.7% success). It is reliable on happy-path/input-validation flows but weak on
  exception/state-driven flows.
- The `4LV` SRS here is a **2-use-case sample**, not the full RetailOnboardPro spec; don't treat its
  results as a full case study.
- Execution and generation currently use **different backends** (Gemini vs BytePlus); a fully unified
  run needs the LLMCaller port described above.

**Reproducibility.** Every LLM call is logged (tokens/cost/latency) to JSONL; figures are regenerated
from those logs; the literature review and paper are scripted. Start from `research_project/channels/
MAIN_LOG.txt` for the full timeline and `research_project/writer/PAPER.md` for the analysis.
