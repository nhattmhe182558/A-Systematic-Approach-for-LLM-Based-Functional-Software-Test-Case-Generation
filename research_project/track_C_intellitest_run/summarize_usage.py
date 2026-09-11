"""
summarize_usage.py  (Track C)
=============================

Aggregate a per-run usage JSONL (written by the instrumented DeepSeekProvider)
into totals: calls, prompt/completion/total tokens, USD cost (placeholder rates),
summed latency, and a per-module token breakdown.

Usage:
  python summarize_usage.py logs/usage_DEEPSEEK_V4_FLASH.jsonl
Writes <same-stem>_summary.json next to the input and prints a report.
"""
import collections
import json
import sys
from pathlib import Path


def summarize(path: Path) -> dict:
    recs = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_mod = collections.Counter()
    by_mod_calls = collections.Counter()
    for r in recs:
        by_mod[r["module"]] += r["total_tokens"]
        by_mod_calls[r["module"]] += 1
    summary = {
        "source": str(path),
        "calls": len(recs),
        "prompt_tokens": sum(r["prompt_tokens"] for r in recs),
        "completion_tokens": sum(r["completion_tokens"] for r in recs),
        "total_tokens": sum(r["total_tokens"] for r in recs),
        "usd_cost_placeholder": round(sum(r["usd_cost"] for r in recs), 6),
        "sum_latency_s": round(sum(r["latency_s"] for r in recs), 1),
        "failed_calls": sum(1 for r in recs if r["status"] != "SUCCESS"),
        "tokens_by_module": dict(by_mod.most_common()),
        "calls_by_module": dict(by_mod_calls.most_common()),
        "pricing_placeholder": True,
    }
    return summary


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: python summarize_usage.py <usage.jsonl>")
    path = Path(sys.argv[1])
    s = summarize(path)
    out = path.with_name(path.stem + "_summary.json")
    out.write_text(json.dumps(s, indent=2), encoding="utf-8")
    print(f"=== Full-pipeline usage: {path.name} ===")
    print(f"Calls              : {s['calls']} ({s['failed_calls']} failed)")
    print(f"Prompt tokens      : {s['prompt_tokens']:,}")
    print(f"Completion tokens  : {s['completion_tokens']:,}")
    print(f"TOTAL tokens       : {s['total_tokens']:,}")
    print(f"USD cost (placehldr): {s['usd_cost_placeholder']:.4f}")
    print(f"Summed latency     : {s['sum_latency_s']}s")
    print("Tokens by module   :")
    for m, t in s["tokens_by_module"].items():
        print(f"   {m:32} {t:>10,}")
    print(f"Summary written to : {out}")


if __name__ == "__main__":
    main()
