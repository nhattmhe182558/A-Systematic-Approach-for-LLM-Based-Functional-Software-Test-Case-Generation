#!/usr/bin/env python3
"""Track A EXPANSION: merge existing 20 + Track E (remapped) + new web-search papers,
deduplicate by normalized title and arXiv id, write systematic_review.csv, report count.
NO LLM/API used. All papers are real (arXiv/venue verified via web search)."""
import csv, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
EXISTING = os.path.join(HERE, "systematic_review.csv")
TRACK_E = os.path.join(HERE, "..", "track_E_new_research", "new_papers.csv")
OUT = EXISTING

HEADER = ["Paper_Title","Authors","Year","Venue","Published_Link","Quartile",
          "Brief_Summary","Problem_Solved","Methodology_Short","Type","Original_Link"]

def norm_title(t):
    t = t.lower()
    t = re.sub(r"\(.*?\)", "", t)          # drop parenthetical tool names
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def arxiv_id(*urls):
    for u in urls:
        m = re.search(r"(\d{4}\.\d{4,5})", u or "")
        if m:
            return m.group(1)
    return None

rows = []
seen_titles = set()
seen_arxiv = set()

def add(row):
    t = norm_title(row["Paper_Title"])
    aid = arxiv_id(row.get("Published_Link",""), row.get("Original_Link",""))
    if t in seen_titles:
        return False
    if aid and aid in seen_arxiv:
        return False
    seen_titles.add(t)
    if aid:
        seen_arxiv.add(aid)
    rows.append(row)
    return True

# 1) existing 20 (keep all)
with open(EXISTING, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        add(r)
n_existing = len(rows)

# 2) Track E remapped to 11-col schema
E_TYPE = "empirical"
def remap_e(r):
    link = r.get("Link","")
    return {
        "Paper_Title": r["Paper_Title"],
        "Authors": r.get("Authors","Authors [estimated]"),
        "Year": r.get("Year",""),
        "Venue": r.get("Venue",""),
        "Published_Link": link,
        "Quartile": "Q3 [estimated]",
        "Brief_Summary": r.get("Novelty",""),
        "Problem_Solved": r.get("Advance_Over_Prior",""),
        "Methodology_Short": "See novelty; " + r.get("Relevance_To_Execution_Phase",""),
        "Type": E_TYPE,
        "Original_Link": link,
    }
with open(TRACK_E, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        add(remap_e(r))
n_after_e = len(rows)

# 3) NEW web-search papers (all real; arXiv IDs verified in search results)
NEW = [
["FlakyFix: Using Large Language Models for Predicting Flaky Test Fix Categories and Test Code Repair","Sakina Fatima, Hadi Hemmati, Lionel Briand [estimated]","2024","IEEE Transactions on Software Engineering (TSE)","https://arxiv.org/abs/2307.00012","Q1 [estimated]","Uses LLMs to predict flaky-test fix categories and to repair flaky test code, moving beyond mere flakiness prediction to actionable fixes.","Flaky tests non-deterministically pass/fail; little tool support exists to actually fix them.","LLM-based fix-category prediction plus code repair, evaluated on flaky-test datasets.","empirical","https://arxiv.org/pdf/2307.00012"],
["An Analysis of LLM Fine-Tuning and Few-Shot Learning for Flaky Test Detection and Classification","Riddhi More, Jeremy S. Bradbury [estimated]","2025","arXiv preprint","https://arxiv.org/abs/2502.02715","Q3 [estimated]","Compares fine-tuning vs few-shot learning of LLMs for detecting and classifying flaky tests, characterizing data/resource tradeoffs.","Reliable flaky-test detection/classification with limited labeled data.","Empirical comparison of LLM fine-tuning and few-shot learning on flaky-test datasets.","empirical","https://arxiv.org/html/2502.02715v1"],
["FlakyGuard: Automatically Fixing Flaky Tests at Industry Scale","Authors [estimated]","2025","arXiv preprint","https://arxiv.org/abs/2511.14002","Q3 [estimated]","Automatically repairs reproducible flaky tests at industrial scale, repairing 47.6% with 51.8% developer-accepted fixes and beating prior work by >=22%.","Industrial-scale automatic repair of flaky tests to keep CI reliable.","LLM-driven flaky-test reproduction and repair pipeline, industrial evaluation.","empirical","https://arxiv.org/pdf/2511.14002v1"],
["Adaptive Test Generation Using a Large Language Model (TestPilot)","Max Schafer, Sarah Nadi, Aryaz Eghbali, Frank Tip","2024","IEEE Transactions on Software Engineering (TSE)","https://arxiv.org/abs/2302.06527","Q1 [estimated]","TestPilot uses an off-the-shelf LLM (Codex) to adaptively generate JavaScript unit tests without extra training, achieving 70.2% median statement coverage.","Automated unit test generation across languages with poor tool support and low readability.","Adaptive prompt-based generation with feedback, evaluated against Nessie on npm packages.","tool","https://arxiv.org/html/2302.06527v2"],
["Multi-language Unit Test Generation using LLMs","Rangeet Pan, Myeongsoo Kim, Rahul Krishna, Raju Pavuluri, Saurabh Sinha","2025","IEEE/ACM ICSE 2025","https://arxiv.org/abs/2409.03093","Q1 [estimated]","A generic static-analysis-guided pipeline that steers LLMs to produce compilable, high-coverage unit tests across Java and Python, including environment mocking.","Generated tests often fail to compile and lack coverage; few languages supported.","Static-analysis-guided LLM pipeline (context + mocking) evaluated on Java and Python.","tool","https://arxiv.org/html/2409.03093v1"],
["Coverage-Guided LLM-Based Test Generation (CoverUp)","Juan Altmayer Pizzorno, Emery D. Berger","2024","arXiv preprint","https://arxiv.org/abs/2403.16218","Q3 [estimated]","CoverUp interleaves coverage analysis with LLM dialogs to iteratively raise Python regression-test coverage, beating CodaMosa on line/branch coverage.","LLM test generation uses fixed prompts and ignores which code remains uncovered.","Iterative coverage-analysis-in-the-loop prompting to target uncovered lines/branches.","tool","https://arxiv.org/html/2403.16218v1"],
["Code-Aware Prompting: A Study of Coverage-Guided Test Generation in Regression Setting using LLM (SymPrompt)","Gabriel Ryan, Siddhartha Jain, Mingyue Shang, Shiqi Wang, Xiaofei Ma, Murali Krishna Ramanathan, Baishakhi Ray","2024","ACM FSE / PACMSE 2024","https://arxiv.org/abs/2402.00097","Q1 [estimated]","SymPrompt uses symbolic path prompts to guide LLMs, improving correct test generations 5x and coverage 26% (2x on GPT-4) in regression settings.","Fixed prompting strategies limit coverage and correctness of LLM regression tests.","Symbolic execution-path-aware prompting evaluated on CodeGen2 and GPT-4.","tool","https://arxiv.org/abs/2402.00097v1"],
["A Comparative Study of SBST, Symbolic Execution, and LLM-Based Approaches to Unit Test Generation","Authors [estimated]","2025","arXiv preprint","https://arxiv.org/abs/2501.10200","Q3 [estimated]","Compares search-based, symbolic-execution, and LLM-based unit test generation; LLMs trail on coverage but lead on mutation score, indicating deeper semantic understanding.","Understanding relative strengths of classic vs LLM test generation paradigms.","Controlled empirical comparison across three test-generation paradigms.","empirical","https://arxiv.org/html/2501.10200v1"],
["Large-scale, Independent and Comprehensive Study of the Power of LLMs for Test Case Generation","Wendkuuni C. Ouedraogo, Kader Kabore, Haoye Tian, et al. [estimated]","2024","arXiv preprint","https://arxiv.org/abs/2407.00225","Q3 [estimated]","Large independent study of LLM unit-test generation across correctness, understandability, coverage, and test smells, comparing to EvoSuite.","Fragmented, non-independent evidence on LLM test-generation quality and test smells.","Large-scale empirical study over many models/projects benchmarked against EvoSuite.","empirical","https://arxiv.org/html/2407.00225v2"],
["Correct and Strong Test Oracle Generation with LLMs (TOGLL)","Soneya Binta Hossain, Matthew Dwyer","2024","arXiv preprint","https://arxiv.org/abs/2405.03786","Q3 [estimated]","TOGLL generates correct and fault-revealing test oracles with LLMs, detecting 1,023 mutants EvoSuite misses and outperforming TOGA on real Defects4J bugs.","The oracle problem: generating oracles that are both correct and strong at finding bugs.","LLM-based oracle generation evaluated on mutants and Defects4J real bugs.","tool","https://arxiv.org/html/2405.03786v2"],
["Do LLMs Generate Test Oracles That Capture the Actual or the Expected Program Behaviour?","Michael Konstantinou, Renzo Degiovanni, Mike Papadakis [estimated]","2024","arXiv preprint","https://arxiv.org/abs/2410.21136","Q3 [estimated]","Studies whether LLM-generated oracles encode expected vs actual behaviour; LLMs are better at generating than classifying oracles and benefit from meaningful names.","Risk that LLM oracles merely restate current (possibly buggy) behaviour instead of intended behaviour.","Empirical study of oracle generation vs classification with fault-detection analysis.","empirical","https://arxiv.org/html/2410.21136v1"],
["Retrieval-Augmented Test Generation","Jiho Shin, Reem Aleithan, Hadi Hemmati, Song Wang [estimated]","2024","arXiv preprint","https://arxiv.org/abs/2409.12682","Q3 [estimated]","Investigates RAG for unit-test generation over API docs, GitHub issues, and StackOverflow Q&As, analysing how each knowledge source affects test quality.","LLM tests lack grounding in external, domain-specific knowledge.","RAG pipeline evaluated across three knowledge sources for ML/DL API tests.","empirical","https://arxiv.org/html/2409.12682v1"],
["Generating Test Scenarios from NL Requirements using Retrieval-Augmented LLMs (RAGTAG)","Authors [estimated]","2024","arXiv preprint","https://arxiv.org/abs/2404.12772","Q3 [estimated]","RAGTAG uses RAG with LLMs to integrate domain knowledge and generate functional test scenarios from natural-language requirements.","Requirements-based test scenario generation needs domain grounding to be accurate.","Retrieval-augmented generation of test scenarios from NL requirements.","tool","https://arxiv.org/abs/2404.12772"],
["Vision-driven Automated Mobile GUI Testing via Multimodal Large Language Model (VisionDroid)","Zhe Liu, Cheng Li, Chunyang Chen, Junjie Wang, et al. [estimated]","2024","arXiv preprint","https://arxiv.org/abs/2407.03037","Q3 [estimated]","VisionDroid aligns GUI text with screenshots into a vision prompt so an MLLM can detect non-crash functional bugs during mobile GUI testing.","Detecting non-crash functional bugs that text-only GUI testing misses.","MLLM vision+text prompting over app exploration to spot functional GUI defects.","tool","https://arxiv.org/html/2407.03037v1"],
["Towards Test Generation from Task Description for Mobile Testing with Multi-modal Reasoning (VisiDroid)","Authors [estimated]","2025","arXiv preprint","https://arxiv.org/abs/2504.15917","Q3 [estimated]","VisiDroid combines images and text so an LLM can generate mobile tests from task descriptions and better judge task completion, reaching 87.3% accuracy.","Knowing when a task-driven mobile test has actually completed its goal.","Multimodal (image+text) reasoning framework for task-based mobile test generation.","tool","https://arxiv.org/html/2504.15917v1"],
["Large Language Models for Mobile GUI Text Input Generation","Authors [estimated]","2024","arXiv preprint","https://arxiv.org/abs/2404.08948","Q3 [estimated]","Systematically evaluates LLMs for generating semantically valid text inputs that unblock automated mobile GUI exploration.","Text-input fields block automated GUI exploration when inputs are not semantically valid.","Empirical evaluation of multiple LLMs for GUI text-input generation.","empirical","https://arxiv.org/html/2404.08948"],
["AutoDroid: LLM-powered Task Automation in Android","Hao Wen, Yuanchun Li, Guohong Liu, et al.","2024","ACM MobiCom 2024","https://arxiv.org/abs/2308.15272","Q1 [estimated]","AutoDroid combines LLM commonsense with app-specific knowledge from dynamic analysis to autonomously complete arbitrary tasks on any Android app.","Prior mobile task automation lacked scalable language understanding and needed manual effort.","LLM + automated dynamic analysis to build app knowledge and execute UI tasks.","tool","https://arxiv.org/abs/2308.15272"],
["DroidBot-GPT: GPT-powered UI-grounded Smartphone Task Automation in Android","Hao Wen, Hongming Wang, Jiaxuan Liu, Yuanchun Li","2024","arXiv preprint","https://arxiv.org/abs/2304.07061","Q3 [estimated]","DroidBot-GPT translates GUI state and available actions into NL prompts and asks a GPT-like LLM to choose actions, automating Android app tasks from NL descriptions.","Automating Android UI task execution directly from natural-language goals.","GUI-to-NL prompting loop with an LLM action selector on real Android apps.","tool","https://arxiv.org/html/2304.07061v3"],
["A Realistic Web Environment for Building Autonomous Agents (WebArena)","Shuyan Zhou, Frank F. Xu, Hao Zhu, Xuhui Zhou, et al.","2024","ICLR 2024","https://arxiv.org/abs/2307.13854","Q1 [estimated]","WebArena is a reproducible, self-hostable web environment with long-horizon tasks used to build and benchmark autonomous web agents that execute and are auto-verified.","Lack of realistic, reproducible environments to evaluate autonomous web agents.","Functional web environment + task suite with programmatic success evaluation.","tool","https://arxiv.org/html/2307.13854v1"],
["A Versatile and Autonomous Multi-Agent System for Web Task Execution with Strategic Exploration (WebPilot)","Yao Zhang, Zijian Ma, Yunpu Ma, et al. [estimated]","2024","arXiv preprint","https://arxiv.org/abs/2408.15978","Q3 [estimated]","WebPilot is a multi-agent MCTS-based system for autonomous web task execution, achieving SOTA on WebArena and strong MiniWoB++ results with GPT-4.","Autonomous multi-step web task execution needs strategic exploration and planning.","Multi-agent Monte-Carlo-tree-search planning evaluated on WebArena and MiniWoB++.","tool","https://arxiv.org/html/2408.15978v1"],
["Leveraging Large Language Models to Improve REST API Testing (RESTGPT)","Myeongsoo Kim, Tyler Stennett, Dhruv Shah, Saurabh Sinha, Alessandro Orso","2024","IEEE/ACM ICSE-NIER 2024","https://arxiv.org/abs/2312.00894","Q1 [estimated]","RESTGPT extracts machine-interpretable rules and example values from NL in an API spec, augmenting the OpenAPI spec to drive more effective REST API testing.","Informal/insufficient API documentation limits automated REST API test quality.","LLM rule/value extraction that enriches OpenAPI specs for downstream testing tools.","tool","https://arxiv.org/html/2312.00894v2"],
["Automated REST API Documentation and Testing via LLM-Assisted Request Mutations (RESTSpecIT)","Alix Decrop, Gilles Perrouin, Mike Papadakis, et al. [estimated]","2024","arXiv preprint","https://arxiv.org/abs/2402.05102","Q3 [estimated]","RESTSpecIT infers REST API documentation and performs black-box testing using LLM-assisted request mutations, without a full OpenAPI spec.","REST API testing requires specs that are often missing or informal.","LLM-guided request mutation to infer specs and black-box test REST APIs.","tool","https://arxiv.org/html/2402.05102v1"],
["Effective REST API Testing with Small Language Models (LlamaRestTest)","Myeongsoo Kim, Saurabh Sinha, Alessandro Orso [estimated]","2025","arXiv preprint","https://arxiv.org/abs/2501.08598","Q3 [estimated]","LlamaRestTest fine-tunes small language models for REST API testing, matching/exceeding RESTGPT and tools like RESTler, EvoMaster, and ARAT-RL on real services.","Large-model cost/latency for REST API testing; can small models suffice?","Fine-tuned small LMs evaluated on 12 real services vs SOTA REST testers.","empirical","https://arxiv.org/html/2501.08598v2"],
["Can Language Models Resolve Real-World GitHub Issues? (SWE-bench)","Carlos E. Jimenez, John Yang, Alexander Wettig, Shunyu Yao, et al.","2024","ICLR 2024","https://arxiv.org/abs/2310.06770","Q1 [estimated]","SWE-bench evaluates whether LLMs can resolve real GitHub issues, requiring patches validated by the repository's own test suites; frontier models solve only the simplest issues.","No realistic benchmark for autonomous, test-validated software issue resolution.","Benchmark of 2,294 real issues with execution-based (unit-test) validation of patches.","empirical","https://arxiv.org/abs/2310.06770"],
["Epic-Organized vs. Requirement-Aligned Gherkin: An Empirical Evaluation of LLM-Based Acceptance Criteria Generation","Authors [estimated]","2026","arXiv preprint","https://arxiv.org/abs/2607.01980","Q3 [estimated]","Evaluates whether epic-organized LLM-generated Gherkin acceptance criteria beat requirement-aligned generation on quality and coverage.","Manual authoring of Gherkin BDD acceptance criteria is a requirements-engineering bottleneck.","Empirical comparison of two LLM Gherkin-generation strategies for coverage/quality.","empirical","https://arxiv.org/pdf/2607.01980v1"],
["Generating BDD Acceptance Tests using Large Language Models: An Empirical Study","Authors [estimated]","2024","arXiv preprint","https://arxiv.org/abs/2403.14965","Q3 [estimated]","Shows GPT-3.5/GPT-4 can generate largely error-free BDD acceptance tests, with few-shot prompting improving accuracy and reducing syntax errors.","Automating BDD acceptance-test authoring from requirements with correct Gherkin syntax.","Empirical study of prompting strategies for BDD test generation with syntax/validation analysis.","empirical","https://arxiv.org/pdf/2403.14965"],
["Retrieval-Augmented Generation for Software Testing and Inspection Automation","Authors [estimated]","2026","arXiv preprint","https://arxiv.org/abs/2604.15270","Q3 [estimated]","Applies a RAG pipeline to reduce hallucination in LLM-driven software testing and inspection by injecting supplementary knowledge sources.","LLM hallucination undermines reliability of automated testing/inspection outputs.","RAG-augmented LLM framework for testing and inspection tasks.","tool","https://arxiv.org/html/2604.15270v1"],
["Execution-aware, Feedback-driven Regression Testing Generation with Large Language Models","Authors [estimated]","2025","arXiv preprint","https://arxiv.org/abs/2508.01255","Q3 [estimated]","Addresses the coverage plateau in LLM regression-test generation by making the LLM execution-aware and feedback-driven about program execution.","LLM regression tests stagnate in coverage due to weak reasoning about execution.","Execution-feedback loop that informs the LLM to break through coverage plateaus.","tool","https://arxiv.org/abs/2508.01255v1"],
["Efficient LLM-driven Test Generation Using Mutant Prioritization (PRIMG)","Authors [estimated]","2025","arXiv preprint","https://arxiv.org/abs/2505.05584","Q3 [estimated]","PRIMG prioritizes mutants to guide LLM test generation, reducing test-suite size while maintaining high mutation coverage and outperforming random mutant selection.","Generating high-impact tests without exhaustive, costly mutation-driven generation.","Mutant-prioritization module feeding an LLM test generator, evaluated on mutation coverage.","tool","https://arxiv.org/html/2505.05584v1"],
["TraceLLM: Leveraging Large Language Models with Prompt Engineering for Enhanced Requirements Traceability","Authors [estimated]","2026","arXiv preprint","https://arxiv.org/abs/2602.01253","Q3 [estimated]","TraceLLM uses LLMs with prompt engineering to establish and maintain trace links between requirements and downstream artifacts including tests.","Maintaining requirements-to-artifact traceability (incl. tests) is costly and error-prone.","Prompt-engineered LLM approach for generating/maintaining requirement trace links.","tool","https://arxiv.org/html/2602.01253v1/"],
["On the Diffusion of Test Smells in LLM-Generated Unit Tests","Authors [estimated]","2024","arXiv preprint","https://arxiv.org/abs/2410.10628","Q3 [estimated]","Contrasts LLM-generated tests with human suites and EvoSuite to determine whether LLMs reproduce human-like test smells or synthetic artifacts.","Understanding maintainability/quality problems (test smells) in LLM-generated tests.","Empirical comparison of LLM vs human vs SBST tests for test-smell diffusion.","empirical","https://arxiv.org/html/2410.10628v2"],
["LLM-based Low-Level Integration Test Generation for Java (IntTestGen)","Authors [estimated]","2026","arXiv preprint","https://arxiv.org/abs/2605.26851","Q3 [estimated]","IntTestGen generates low-level integration tests for Java, improving line/branch coverage and mutation score and covering additional dependency code.","Integration testing (beyond isolated units) is under-served by LLM test generators.","LLM-based integration-test generation evaluated on coverage and mutation across two benchmarks.","tool","https://arxiv.org/abs/2605.26851v2"],
["Test vs Mutant: Adversarial LLM Agents for Robust Unit Test Generation","Authors [estimated]","2026","arXiv preprint","https://arxiv.org/abs/2602.08146","Q3 [estimated]","Uses adversarial LLM agents (test-writer vs mutant-maker) to drive robust, high-coverage, compilable unit tests.","LLM tests are readable but often low-coverage and non-compilable.","Adversarial multi-agent test-vs-mutant loop for robust unit test generation.","tool","https://arxiv.org/pdf/2602.08146v1"],
["Enhancing Test Suite Robustness via LLM-Based Generation and Genetic Optimization (EvoGPT)","Authors [estimated]","2025","arXiv preprint","https://arxiv.org/abs/2505.12424","Q3 [estimated]","EvoGPT hybridizes LLM test generation with evolutionary search to produce diverse, bug-revealing unit tests.","LLM-only generation lacks diversity and bug-revealing power of search-based methods.","Hybrid LLM + genetic-algorithm framework for unit test generation.","tool","https://arxiv.org/html/2505.12424v1"],
["A System for Automated Unit Test Generation Using Large Language Models and Assessment of Generated Test Suites","Andrea Lops, Fedelucio Narducci, et al. [estimated]","2024","arXiv preprint","https://arxiv.org/abs/2408.07846","Q3 [estimated]","Builds a scalable system and a Methods2Test-derived dataset to compare LLM-generated tests with human-written tests and assess quality.","Need for scalable systems and datasets to fairly assess LLM test-suite quality.","Automated generation system + new dataset + evaluation methodology.","tool","https://arxiv.org/html/2408.07846v2"],
["Exploratory Study on Private GPTs for LLM-Driven Test Generation in Software and Machine Learning Development","Authors [estimated]","2025","arXiv preprint","https://arxiv.org/abs/2506.06509","Q3 [estimated]","Uses acceptance criteria from epics/stories with private GPTs to produce testable criteria and tests in software and ML development settings.","Turning story/epic acceptance criteria directly into testable artifacts with private LLMs.","Exploratory study of private-GPT-driven test generation from acceptance criteria.","empirical","https://arxiv.org/html/2506.06509v2"],
["A Systematic Literature Review on Large Language Models for Automated Program Repair","Quanjun Zhang, Chunrong Fang, Yang Xie, et al.","2024","arXiv preprint (SLR)","https://arxiv.org/abs/2405.01466","Q3 [estimated]","PRISMA-style SLR of LLM-based automated program repair, including the tight coupling between test-based validation and repair.","Fragmented understanding of LLM-based APR techniques and their test-driven validation.","Systematic literature review of LLM-for-APR studies and methods.","review","https://arxiv.org/html/2405.01466v4"],
["Enhancing Conversation-Based Automated Program Repair via Contrastive Test Case Pairs","Authors [estimated]","2024","arXiv preprint","https://arxiv.org/abs/2403.01971","Q3 [estimated]","Improves conversational LLM program repair using contrastive test-case pairs to better localize and validate fixes.","Conversational APR needs stronger test-driven feedback signals to converge.","Contrastive test-case-pair feedback within a conversational APR loop.","tool","https://arxiv.org/html/2403.01971v1"],
["Correct and Strong REST API Testing with Verified LLM-Inferred Dependencies and Response-Driven Refinement","Authors [estimated]","2026","arXiv preprint","https://arxiv.org/abs/2608.17546","Q3 [estimated]","Validates LLM-inferred REST operation dependencies via execution and refines test sequences from responses, avoiding spurious/infeasible tests.","LLM-inferred API dependencies are often unvalidated, yielding infeasible test sequences.","Execution-verified dependency inference plus response-driven test-sequence refinement.","tool","https://arxiv.org/html/2608.17546v2"],
["LLM-as-a-Judge for Scalable Test Coverage Evaluation","Authors [estimated]","2025","arXiv preprint","https://arxiv.org/abs/2512.01232","Q3 [estimated]","LLM-as-a-Judge (LAJ) is a rubric-driven framework producing structured JSON verdicts to evaluate Gherkin acceptance-test coverage at scale.","Assessing acceptance-test coverage quality at scale is a QA bottleneck.","Rubric-driven LLM judging framework with structured JSON outputs for coverage evaluation.","tool","https://arxiv.org/html/2512.01232v1"],
["Semantic-Aware Gray-Box Game Regression Testing with Large Language Models (SAGE)","Authors [estimated]","2025","arXiv preprint","https://arxiv.org/abs/2512.00560","Q3 [estimated]","SAGE uses LLM semantic analysis of update logs to prioritize regression tests most relevant to version changes, evaluated on Overcooked Plus and Minecraft.","Regression testing must adapt test selection efficiently as software/game versions change.","LLM-based semantic change analysis for test prioritization in gray-box game testing.","tool","https://arxiv.org/html/2512.00560"],
]
for row in NEW:
    add(dict(zip(HEADER, row)))
n_after_new = len(rows)

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=HEADER)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in HEADER})

print(f"existing kept   : {n_existing}")
print(f"after track_E   : {n_after_e} (+{n_after_e - n_existing})")
print(f"after new search: {n_after_new} (+{n_after_new - n_after_e})")
print(f"FINAL_UNIQUE    : {len(rows)}")
