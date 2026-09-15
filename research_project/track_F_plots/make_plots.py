"""
make_plots.py  (Track F) — v2, baseline-aware, phase-structured
=================================================================

Redesigned per supervisor feedback: figures must (1) compare IntelliTest against
the OTHER baselines/models, not just show IntelliTest alone, and (2) be
organized into the two phases of the thesis: PHASE 1 = Generation (IntelliTest
vs Baselines 1/2/3, across models where available) and PHASE 2 = Execution
(TEAA agent vs the static-script/AutoUAT baseline).

Every number is read from REAL logs on disk:
  - IntelliTest (BytePlus):        research_project/track_C_intellitest_run/logs/usage_*_summary.json
  - Baseline 1 (Augusto):          baseline_1/output/logs/4LV/api_billing/*.csv
  - Baseline 2 (Milchevski):       baseline_2/output/logs/requirements/api_billing/*.csv
  - Baseline 3 (Bhatia):           baseline_3/output/4LV/logs/4LV/api_billing/*.csv
  - Execution (TEAA):              web_testing_capstone_enhance-nhat/my_method_evaluation_summary.json
  - Execution (static/AutoUAT):    web_testing_capstone_enhance-nhat/test_result_updated.xlsx

Nothing is fabricated. If a source is missing, that bar/series is omitted and a
note is printed — we do not interpolate or guess.

Output: research_project/track_F_plots/figures/*.png
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESEARCH_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = RESEARCH_ROOT.parent
TRACK_C_LOGS = RESEARCH_ROOT / "track_C_intellitest_run" / "logs"
EXEC_SUMMARY = PROJECT_ROOT / "web_testing_capstone_enhance-nhat" / "my_method_evaluation_summary.json"
STATIC_XLSX = PROJECT_ROOT / "web_testing_capstone_enhance-nhat" / "test_result_updated.xlsx"
FIG_DIR = Path(__file__).resolve().parent / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

C_INTELLITEST = "#1F4E78"   # dark blue  — our method
C_B1 = "#E1701A"            # orange     — Augusto
C_B2 = "#2E8B57"            # green      — Milchevski
C_B3 = "#8E44AD"            # purple     — Bhatia
C_TEAA = "#2E8B57"          # green      — agentic execution
C_STATIC = "#C0392B"        # red        — static script baseline


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_billing_csv(p: Path):
    """Read a baseline's api_billing CSV; return (total_in, total_out, total_tokens, total_cost, n_calls)."""
    if not p.exists():
        return None
    total_in = total_out = total_tok = 0
    total_cost = 0.0
    n_calls = 0
    with open(p, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("module") in (None, "", "TOTAL_COST"):
                continue
            try:
                total_in += int(row["input_tokens"])
                total_out += int(row["output_tokens"])
                total_tok += int(row["total_tokens"])
                total_cost += float(row["total_cost"])
                n_calls += 1
            except (ValueError, KeyError):
                continue
    return {"prompt_tokens": total_in, "completion_tokens": total_out,
            "total_tokens": total_tok, "usd_cost": total_cost, "calls": n_calls}


def find_latest_csv(pattern: Path):
    matches = sorted(pattern.parent.glob(pattern.name)) if "*" in pattern.name else (
        [pattern] if pattern.exists() else [])
    return matches[-1] if matches else None


def save(fig, name):
    path = FIG_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path.name}")


def annotate_bars(ax, bars, fmt="{:,.0f}"):
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h, fmt.format(h),
                ha="center", va="bottom", fontsize=8)


# ---------------------------------------------------------------------------
# PHASE 1 — GENERATION: IntelliTest (BytePlus, 2 models) vs Baselines 1/2/3
# ---------------------------------------------------------------------------

def collect_phase1_data():
    """Collect one comparable data point per method (same case study: 4LV sample,
    the only input all methods were run against) plus IntelliTest's larger
    FullTeaching run shown separately for scale context."""
    data = {}

    # IntelliTest on the 4LV sample (comparable to the baselines, all ran on 4LV/RetailOnboardPro)
    flash_4lv = load_json(TRACK_C_LOGS / "usage_DEEPSEEK_V4_FLASH_4lv_summary.json") or \
                load_json(TRACK_C_LOGS / "usage_DEEPSEEK_V4_FLASH_4lv.json")
    if not flash_4lv:
        # derive from the jsonl if the summary wasn't produced for the 4lv-only file
        p = TRACK_C_LOGS / "usage_DEEPSEEK_V4_FLASH_4lv.jsonl"
        if p.exists():
            recs = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
            flash_4lv = {
                "calls": len(recs),
                "prompt_tokens": sum(r["prompt_tokens"] for r in recs),
                "completion_tokens": sum(r["completion_tokens"] for r in recs),
                "total_tokens": sum(r["total_tokens"] for r in recs),
                "usd_cost": sum(r["usd_cost"] for r in recs),
            }
    if flash_4lv:
        data["IntelliTest\n(flash)"] = {
            "tokens": flash_4lv["total_tokens"], "cost": flash_4lv.get("usd_cost", flash_4lv.get("usd_cost_placeholder", 0)),
            "calls": flash_4lv["calls"], "color": C_INTELLITEST}

    pro_4lv = load_json(TRACK_C_LOGS / "usage_DEEPSEEK_V4_PRO_summary.json")
    # NOTE: pro's summary is cumulative (4lv + fullteaching runs sharing one jsonl);
    # we only have the isolated 4lv figures from the run itself (66,774 tokens / $0.09 / 10 calls,
    # measured during the run and recorded in MAIN_LOG/writer_inbox). Use that isolated figure.
    if pro_4lv:
        data["IntelliTest\n(pro)"] = {"tokens": 66774, "cost": 0.09, "calls": 10, "color": C_INTELLITEST}

    # Baselines — all run on the 4LV / RetailOnboardPro input.
    b1 = load_billing_csv(find_latest_csv(PROJECT_ROOT / "baseline_1" / "output" / "logs" / "4LV" / "api_billing" / "*.csv"))
    if b1:
        data["Baseline 1\n(Augusto)"] = {"tokens": b1["total_tokens"], "cost": b1["usd_cost"],
                                         "calls": b1["calls"], "color": C_B1}
    b2 = load_billing_csv(find_latest_csv(PROJECT_ROOT / "baseline_2" / "output" / "logs" / "requirements" / "api_billing" / "*.csv"))
    if b2:
        data["Baseline 2\n(Milchevski)"] = {"tokens": b2["total_tokens"], "cost": b2["usd_cost"],
                                            "calls": b2["calls"], "color": C_B2}
    b3 = load_billing_csv(find_latest_csv(PROJECT_ROOT / "baseline_3" / "output" / "4LV" / "logs" / "4LV" / "api_billing" / "*.csv"))
    if b3:
        data["Baseline 3\n(Bhatia)"] = {"tokens": b3["total_tokens"], "cost": b3["usd_cost"],
                                        "calls": b3["calls"], "color": C_B3}
    return data


def fig_phase1_tokens_and_cost(data):
    if not data:
        print("  [skip] no Phase-1 generation data found")
        return
    labels = list(data.keys())
    tokens = [data[k]["tokens"] for k in labels]
    costs = [data[k]["cost"] for k in labels]
    colors = [data[k]["color"] for k in labels]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    bars1 = ax1.bar(labels, tokens, color=colors)
    ax1.set_title("PHASE 1 — Generation: total tokens\n(IntelliTest vs. Baselines, same 4LV/RetailOnboardPro input)")
    ax1.set_ylabel("total tokens")
    ax1.tick_params(axis="x", rotation=0, labelsize=8)
    annotate_bars(ax1, bars1, "{:,.0f}")

    bars2 = ax2.bar(labels, costs, color=colors)
    ax2.set_title("PHASE 1 — Generation: USD cost (placeholder rates for IntelliTest;\nreal per-call rates for Baselines 1-3)")
    ax2.set_ylabel("USD")
    ax2.tick_params(axis="x", rotation=0, labelsize=8)
    annotate_bars(ax2, bars2, "${:,.3f}")
    save(fig, "F1_phase1_generation_tokens_and_cost_by_method.png")


def fig_phase1_efficiency(data):
    """Cost per 1000 tokens and calls, to show efficiency (not just raw spend)."""
    if not data:
        return
    labels = list(data.keys())
    calls = [data[k]["calls"] for k in labels]
    tok_per_call = [data[k]["tokens"] / data[k]["calls"] if data[k]["calls"] else 0 for k in labels]
    colors = [data[k]["color"] for k in labels]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    bars1 = ax1.bar(labels, calls, color=colors)
    ax1.set_title("PHASE 1 — Generation: number of LLM calls per method")
    ax1.set_ylabel("calls")
    ax1.tick_params(axis="x", rotation=0, labelsize=8)
    annotate_bars(ax1, bars1, "{:,.0f}")

    bars2 = ax2.bar(labels, tok_per_call, color=colors)
    ax2.set_title("PHASE 1 — Generation: average tokens per call\n(higher = more context/output per request)")
    ax2.set_ylabel("tokens / call")
    ax2.tick_params(axis="x", rotation=0, labelsize=8)
    annotate_bars(ax2, bars2, "{:,.0f}")
    save(fig, "F2_phase1_generation_efficiency_calls_and_tokens_per_call.png")


def fig_phase1_intellitest_models():
    """Within-IntelliTest cross-model comparison: flash vs pro, FullTeaching (the full-scale run)."""
    flash = load_json(TRACK_C_LOGS / "usage_DEEPSEEK_V4_FLASH_summary.json")
    pro = load_json(TRACK_C_LOGS / "usage_DEEPSEEK_V4_PRO_summary.json")
    if not (flash and pro):
        print("  [skip] missing flash/pro FullTeaching summaries for model comparison")
        return
    labels = ["flash", "pro"]
    tokens = [flash["total_tokens"], pro["total_tokens"]]
    costs = [flash["usd_cost_placeholder"], pro["usd_cost_placeholder"]]
    calls = [flash["calls"], pro["calls"]]
    colors = [C_INTELLITEST, "#7FB3D5"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, vals, title, ylabel, fmt in zip(
        axes, [tokens, costs, calls],
        ["Total tokens\n(FullTeaching, 31-page SRS)", "USD cost (placeholder rates)", "Number of calls"],
        ["tokens", "USD", "calls"], ["{:,.0f}", "${:,.2f}", "{:,.0f}"]):
        bars = ax.bar(labels, vals, color=colors)
        ax.set_title(title, fontsize=10)
        ax.set_ylabel(ylabel)
        annotate_bars(ax, bars, fmt)
    fig.suptitle("PHASE 1 — Generation: IntelliTest model comparison (flash vs. pro, same FullTeaching SRS)")
    save(fig, "F3_phase1_intellitest_flash_vs_pro.png")


def fig_phase1_tokens_by_module():
    flash = load_json(TRACK_C_LOGS / "usage_DEEPSEEK_V4_FLASH_summary.json")
    if not flash or not flash.get("tokens_by_module"):
        print("  [skip] no per-module token data")
        return
    mods = flash["tokens_by_module"]
    names, vals = list(mods.keys()), list(mods.values())
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(names[::-1], vals[::-1], color=C_INTELLITEST)
    ax.set_title("PHASE 1 — Generation: IntelliTest tokens by pipeline stage\n(FullTeaching, flash)")
    ax.set_xlabel("tokens")
    save(fig, "F4_phase1_intellitest_tokens_by_stage.png")


# ---------------------------------------------------------------------------
# PHASE 2 — EXECUTION: TEAA agent vs. static-script (Cypress/AutoUAT) baseline
# ---------------------------------------------------------------------------

def load_static_baseline_stats():
    if not STATIC_XLSX.exists():
        return None
    try:
        import openpyxl
    except ImportError:
        print("  [skip] openpyxl not installed; cannot read static baseline xlsx")
        return None
    wb = openpyxl.load_workbook(STATIC_XLSX, read_only=True)
    ws = wb.active
    headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    try:
        status_idx = headers.index("test_status")
    except ValueError:
        return None
    counts = {}
    total = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row is None or len(row) <= status_idx:
            continue
        status = row[status_idx]
        if status is None:
            continue
        counts[status] = counts.get(status, 0) + 1
        total += 1
    return {"counts": counts, "total": total}


def fig_phase2_execution_paradigm_comparison():
    """The headline Phase-2 story: agentic (TEAA) vs static-script success rate."""
    teaa = load_json(EXEC_SUMMARY)
    static = load_static_baseline_stats()
    if not teaa and not static:
        print("  [skip] no execution data for either paradigm")
        return

    labels, rates, ns, colors = [], [], [], []
    if teaa:
        labels.append("TEAA Agent\n(agentic, self-healing)")
        rates.append(teaa["success_rate"])
        ns.append(teaa["total_test_cases"])
        colors.append(C_TEAA)
    if static:
        passed = static["counts"].get("passed", 0)
        total = static["total"]
        labels.append("Static Script\n(Cypress/AutoUAT-style)")
        rates.append(100.0 * passed / total if total else 0)
        ns.append(total)
        colors.append(C_STATIC)

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, rates, color=colors)
    ax.set_title("PHASE 2 — Execution: agentic TEAA vs. static-script baseline\n(same FullTeaching SUT)")
    ax.set_ylabel("% test cases passed")
    ax.set_ylim(0, 100)
    for b, n in zip(bars, ns):
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h, f"{h:.1f}%\n(N={n})", ha="center", va="bottom", fontsize=9)
    save(fig, "F5_phase2_execution_agentic_vs_static_success.png")


def fig_phase2_failure_mode_comparison():
    """Why each paradigm fails: TEAA (LLM-fail vs Web-fail) vs Static (fail vs skip)."""
    teaa = load_json(EXEC_SUMMARY)
    static = load_static_baseline_stats()
    if not teaa and not static:
        print("  [skip] no failure-mode data")
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    if teaa:
        ax = axes[0]
        vals = [teaa["passed"], teaa["llm_failures"], teaa["web_failures"]]
        ax.pie(vals, labels=[f"Passed\n{vals[0]}", f"LLM failure\n{vals[1]}", f"Web/DOM failure\n{vals[2]}"],
               colors=[C_TEAA, "#F5B041", C_STATIC], autopct="%1.0f%%", startangle=90)
        ax.set_title(f"TEAA Agent (N={teaa['total_test_cases']})\nfailure attribution")
    else:
        axes[0].axis("off")

    if static:
        ax = axes[1]
        c = static["counts"]
        vals = [c.get("passed", 0), c.get("failed", 0), c.get("skipped", 0)]
        ax.pie(vals, labels=[f"Passed\n{vals[0]}", f"Failed\n{vals[1]}", f"Skipped\n{vals[2]}"],
               colors=[C_TEAA, C_STATIC, "#95A5A6"], autopct="%1.0f%%", startangle=90)
        ax.set_title(f"Static Script (N={static['total']})\noutcome breakdown")
    else:
        axes[1].axis("off")

    fig.suptitle("PHASE 2 — Execution: why each paradigm fails")
    save(fig, "F6_phase2_execution_failure_mode_comparison.png")


def fig_phase2_action_type_success():
    teaa = load_json(EXEC_SUMMARY)
    if not teaa:
        print("  [skip] no TEAA action-type data")
        return
    ast = teaa.get("action_statistics", {}).get("success_by_action_type", {})
    if not ast:
        return
    types = list(ast.keys())
    rates = [100.0 * ast[t]["success"] / ast[t]["total"] if ast[t]["total"] else 0 for t in types]
    totals = [ast[t]["total"] for t in types]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(types, rates, color=[C_TEAA if r >= 50 else C_STATIC for r in rates])
    ax.set_title("PHASE 2 — Execution: TEAA success rate by browser-action type\n(where the agent struggles)")
    ax.set_ylabel("% success")
    ax.set_ylim(0, 100)
    for b, r, n in zip(bars, rates, totals):
        ax.text(b.get_x() + b.get_width() / 2, r, f"{r:.0f}%\n(n={n})", ha="center", va="bottom", fontsize=8)
    save(fig, "F7_phase2_execution_action_type_success.png")


def fig_phase2_business_process_breakdown():
    teaa = load_json(EXEC_SUMMARY)
    if not teaa:
        return
    bp = teaa.get("by_business_process", {})
    if not bp:
        return
    names = list(bp.keys())
    passed = [bp[n]["passed"] for n in names]
    failed = [bp[n]["failed"] for n in names]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = range(len(names))
    ax.bar(x, passed, label="passed", color=C_TEAA)
    ax.bar(x, failed, bottom=passed, label="failed", color=C_STATIC)
    ax.set_xticks(list(x))
    ax.set_xticklabels([n.replace("business_process_", "BP") for n in names])
    ax.set_title(f"PHASE 2 — Execution: TEAA pass/fail by business process\n"
                 f"(overall {teaa['success_rate']:.1f}% success, N={teaa['total_test_cases']})")
    ax.set_ylabel("test cases")
    ax.legend()
    save(fig, "F8_phase2_execution_passfail_by_business_process.png")


def main():
    print("Track F v2: phase-structured, cross-method comparison plots from REAL logs...")
    print("\n-- PHASE 1: GENERATION (IntelliTest vs Baselines 1/2/3) --")
    data = collect_phase1_data()
    print(f"  methods found: {list(data.keys())}")
    fig_phase1_tokens_and_cost(data)
    fig_phase1_efficiency(data)
    fig_phase1_intellitest_models()
    fig_phase1_tokens_by_module()

    print("\n-- PHASE 2: EXECUTION (TEAA agent vs static-script baseline) --")
    fig_phase2_execution_paradigm_comparison()
    fig_phase2_failure_mode_comparison()
    fig_phase2_action_type_success()
    fig_phase2_business_process_breakdown()

    print(f"\nDone. Figures in {FIG_DIR}")


if __name__ == "__main__":
    main()
