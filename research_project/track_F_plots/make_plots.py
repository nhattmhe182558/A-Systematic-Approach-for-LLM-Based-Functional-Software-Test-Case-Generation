"""
make_plots.py  (Track F)
========================

Generate diagrams from REAL logged data only. Nothing is fabricated; every value
traces to a file under research_project/ or web_testing_capstone_enhance-nhat/.
If a data source is missing, the corresponding plot is SKIPPED with a printed
note (we do not invent numbers).

Outputs PNGs into research_project/track_F_plots/figures/.

Figures:
  F1  Generation: total tokens per (model x case study)         [Track C usage summaries]
  F2  Generation: USD cost per (model x case study)             [Track C, placeholder rates]
  F3  Generation: tokens by pipeline module (FullTeaching)      [Track C usage summaries]
  F4  Generation: wall-clock time per run                       [Track C manifests]
  F5  Execution: success vs fail by business process            [Track D summary json]
  F6  Execution: action-type success rates                      [Track D summary json]
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESEARCH_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = RESEARCH_ROOT.parent
TRACK_C_LOGS = RESEARCH_ROOT / "track_C_intellitest_run" / "logs"
EXEC_SUMMARY = PROJECT_ROOT / "web_testing_capstone_enhance-nhat" / "my_method_evaluation_summary.json"
FIG_DIR = Path(__file__).resolve().parent / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, GREEN, RED = "#1F4E78", "#E1701A", "#2E8B57", "#C0392B"


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save(fig, name):
    path = FIG_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path.name}")


def gen_summaries():
    """Collect per-run generation usage summaries that exist."""
    out = {}
    # Full-teaching summaries live in usage_<MODEL>_summary.json (latest run per model).
    for key, label in [("DEEPSEEK_V4_FLASH", "flash"), ("DEEPSEEK_V4_PRO", "pro"),
                       ("DOLA_SEED_2_1", "dola")]:
        s = load_json(TRACK_C_LOGS / f"usage_{key}_summary.json")
        if s:
            out[label] = s
    return out


def fig_generation(summaries):
    if not summaries:
        print("  [skip] no generation usage summaries found")
        return
    labels = list(summaries.keys())
    tokens = [summaries[k]["total_tokens"] for k in labels]
    costs = [summaries[k]["usd_cost_placeholder"] for k in labels]

    # F1 tokens
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, tokens, color=[BLUE, ORANGE, GREEN][:len(labels)])
    ax.set_title("Generation: total tokens per model (latest FullTeaching run)")
    ax.set_ylabel("total tokens")
    for i, v in enumerate(tokens):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=8)
    save(fig, "F1_generation_tokens_per_model.png")

    # F2 cost
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, costs, color=[BLUE, ORANGE, GREEN][:len(labels)])
    ax.set_title("Generation: USD cost per model (PLACEHOLDER rates)")
    ax.set_ylabel("USD (placeholder)")
    for i, v in enumerate(costs):
        ax.text(i, v, f"${v:.2f}", ha="center", va="bottom", fontsize=8)
    save(fig, "F2_generation_cost_per_model.png")

    # F3 tokens by module (prefer flash, else first available)
    pick = summaries.get("flash") or next(iter(summaries.values()))
    mods = pick.get("tokens_by_module", {})
    if mods:
        fig, ax = plt.subplots(figsize=(7, 4))
        names = list(mods.keys())
        vals = list(mods.values())
        ax.barh(names[::-1], vals[::-1], color=BLUE)
        ax.set_title("Generation: tokens by pipeline module (FullTeaching)")
        ax.set_xlabel("tokens")
        save(fig, "F3_generation_tokens_by_module.png")


def fig_gen_time():
    """Wall-clock per run from manifests."""
    runs = []
    for mf in sorted(TRACK_C_LOGS.glob("manifest_*.json")):
        m = load_json(mf)
        if m:
            runs.append((f"{m['model_key'].replace('DEEPSEEK_V4_','').replace('_','')}\n{m['doc_stem'][:12]}",
                         m["elapsed_s"] / 60.0))
    if not runs:
        print("  [skip] no generation manifests found")
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([r[0] for r in runs], [r[1] for r in runs], color=GREEN)
    ax.set_title("Generation: wall-clock time per run")
    ax.set_ylabel("minutes")
    for i, r in enumerate(runs):
        ax.text(i, r[1], f"{r[1]:.0f}m", ha="center", va="bottom", fontsize=8)
    save(fig, "F4_generation_time_per_run.png")


def fig_execution():
    s = load_json(EXEC_SUMMARY)
    if not s:
        print("  [skip] execution summary not found")
        return
    # F5 success vs fail by business process
    bp = s.get("by_business_process", {})
    if bp:
        names = list(bp.keys())
        passed = [bp[n]["passed"] for n in names]
        failed = [bp[n]["failed"] for n in names]
        fig, ax = plt.subplots(figsize=(8, 4))
        x = range(len(names))
        ax.bar(x, passed, label="passed", color=GREEN)
        ax.bar(x, failed, bottom=passed, label="failed", color=RED)
        ax.set_xticks(list(x))
        ax.set_xticklabels([n.replace("business_process_", "BP") for n in names])
        ax.set_title(f"Execution: pass/fail by business process "
                     f"(overall {s['success_rate']:.1f}% success, N={s['total_test_cases']})")
        ax.set_ylabel("test cases")
        ax.legend()
        save(fig, "F5_execution_passfail_by_bp.png")

    # F6 action-type success rates
    ast = s.get("action_statistics", {}).get("success_by_action_type", {})
    if ast:
        types = list(ast.keys())
        rates = [100.0 * ast[t]["success"] / ast[t]["total"] if ast[t]["total"] else 0 for t in types]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(types, rates, color=ORANGE)
        ax.set_title("Execution: success rate by action type")
        ax.set_ylabel("% success")
        ax.set_ylim(0, 100)
        for i, v in enumerate(rates):
            ax.text(i, v, f"{v:.0f}%", ha="center", va="bottom", fontsize=8)
        save(fig, "F6_execution_action_type_success.png")


def main():
    print("Track F: generating plots from REAL logged data...")
    summaries = gen_summaries()
    fig_generation(summaries)
    fig_gen_time()
    fig_execution()
    print(f"Done. Figures in {FIG_DIR}")


if __name__ == "__main__":
    main()
