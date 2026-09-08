# Baseline 1 — Augusto et al.

Replication of the exploratory-study baseline from:

> C. Augusto, J. Morán, A. Bertolino, C. de la Riva, J. Tuya,
> *"Software System Testing assisted by Large Language Models: An Exploratory
> Study"*, ICTSS 2024.

The original replication package (`retorch-llm-rp`) is written in **Java**.
This folder is a faithful **Python port** so it runs the same way as the other
baselines, with **Gemini or DeepSeek** support. The prompts are kept verbatim
from the Java `RQ1Experimentation` / `RQ2Experimentation` sources.

## Approach (two stages)

- **RQ1 — Test Scenarios:** generate test scenarios from the user requirements
  using a Few-Shot + Chain-of-Thought prompt and a scenario example.
- **RQ2 — System Test Cases:** scenario titles are extracted from the RQ1
  output; for each, a leave-one-out cross-validation is performed over the
  example system test cases (the file is split on `//TC`, and the example at
  index `i % 5 + 1` is removed), then a Few-Shot + CoT prompt asks for that one
  test case.

Generation config matches the original: `temperature=0.1`, `top_p=1.0`,
`max_output_tokens=32768`.

## Files

```
baseline_1/
├── main.py            # RQ1 + RQ2 stages, verbatim prompts, cross-validation
├── provider.py        # Gemini / DeepSeek single-shot generation
├── logger_utils.py    # token/cost/timing logging
├── requirements.txt
├── .env.example
├── input/
│   ├── inputUserRequirements_en.txt   # user requirements (FullTeaching)
│   ├── inputTestScenarioExample.txt   # scenario example (few-shot)
│   ├── inputSystemTestCases.txt       # example system test cases (//TC-split)
│   └── inputTestScenarios.txt         # RQ1 output goes here (empty until RQ1)
└── output/            # RQ1/ and RQ2/ prompt + response files, logs
```

## Setup & run

```bash
pip install -r requirements.txt
cp .env.example .env        # add your API key(s)

# Stage 1: generate scenarios
python main.py --stage rq1 --provider gemini

# Review output/RQ1/RQ1_GenerateTestScenarios.txt, then paste the chosen
# scenarios into input/inputTestScenarios.txt

# Stage 2: generate system test cases
python main.py --stage rq2 --provider gemini

# Or run both back-to-back (RQ2 uses whatever is in inputTestScenarios.txt):
python main.py --stage all --provider deepseek
```

> Note: as in the original, `inputTestScenarios.txt` starts empty. RQ2 reads its
> scenario titles from that file, so populate it from the RQ1 output first
> (the two stages are decoupled on purpose for manual scenario selection).

## Output

`output/RQ1/` and `output/RQ2/` contain the exact prompt sent (`*-prompt*.txt`)
and the model response per experiment, plus a `logs/` folder with the run log,
per-day API-billing CSV, and execution-timing log.
