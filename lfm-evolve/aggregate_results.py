"""Aggregates a multi-seed run_experiment.py output into mean +/- std tables.

Walks <base_dir>/seed*/{train,eval}/{run_summary,eval_summary}.json. Runnable
standalone at any point mid-experiment -- reports k (seeds actually
available) per cell rather than assuming every seed finished.
"""

import argparse
import csv
import glob
import json
import os
import statistics
from collections import defaultdict

ARTIFACT_ORDER = ["baseline", "aflow", "textgrad", "mipro", "bilevel"]


def load_json(path, default=None):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return default if default is not None else {}


def save_json_atomic(path, payload):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    os.replace(tmp, path)


def discover_seeds(base_dir):
    seeds = []
    for d in sorted(glob.glob(os.path.join(base_dir, "seed*"))):
        name = os.path.basename(d)
        try:
            seeds.append(int(name[len("seed"):]))
        except ValueError:
            continue
    return sorted(seeds)


def mean_std(values):
    n = len(values)
    if n == 0:
        return None, None, 0
    mean = sum(values) / n
    std = statistics.stdev(values) if n > 1 else 0.0
    return mean, std, n


def collect(base_dir):
    """Returns (seeds, eval_rows, train_rows). eval_rows/train_rows only
    include cells whose status is 'success' -- missing/failed cells simply
    reduce k for that (benchmark, model, artifact) group."""
    seeds = discover_seeds(base_dir)
    eval_rows = []
    train_rows = []

    for seed in seeds:
        seed_dir = os.path.join(base_dir, f"seed{seed}")
        eval_summary = load_json(os.path.join(seed_dir, "eval", "eval_summary.json"), {})
        train_summary = load_json(os.path.join(seed_dir, "train", "run_summary.json"), {})

        for benchmark_name, by_model in eval_summary.items():
            if benchmark_name == "_meta":
                continue
            for label, by_artifact in by_model.items():
                for artifact, cell in by_artifact.items():
                    if cell.get("status") != "success":
                        continue
                    eval_rows.append({
                        "seed": seed,
                        "benchmark": benchmark_name,
                        "model": label,
                        "artifact": artifact,
                        "score": cell.get("mean_score"),
                        "n": cell.get("n"),
                    })

        for label, by_method in train_summary.items():
            if label == "_meta":
                continue
            for method, cell in by_method.items():
                if cell.get("status") != "success":
                    continue
                anthropic = (cell.get("usage") or {}).get("anthropic", {})
                train_rows.append({
                    "seed": seed,
                    "model": label,
                    "method": method,
                    "elapsed_sec": cell.get("elapsed_sec", 0) or 0,
                    "claude_cost_usd": anthropic.get("cost_usd", 0) or 0,
                    "claude_prompt_tokens": anthropic.get("prompt_tokens", 0) or 0,
                    "claude_completion_tokens": anthropic.get("completion_tokens", 0) or 0,
                })

    return seeds, eval_rows, train_rows


def write_final_results_md(path, seeds, eval_rows, train_rows):
    score_groups = defaultdict(list)  # (benchmark, model, artifact) -> [(seed, score)]
    for row in eval_rows:
        score_groups[(row["benchmark"], row["model"], row["artifact"])].append((row["seed"], row["score"]))

    lines = ["# Final Results", "", f"Seeds discovered: {seeds}", ""]

    benchmarks = sorted({b for (b, _, _) in score_groups})
    for benchmark in benchmarks:
        models = sorted({m for (b, m, _) in score_groups if b == benchmark})
        artifacts = [a for a in ARTIFACT_ORDER if any((benchmark, m, a) in score_groups for m in models)]

        lines.append(f"## {benchmark}")
        lines.append("")
        lines.append("| model | " + " | ".join(artifacts) + " |")
        lines.append("|---" * (1 + len(artifacts)) + "|")
        for model in models:
            row = [model]
            for artifact in artifacts:
                values = score_groups.get((benchmark, model, artifact), [])
                scores = [s for _, s in values if s is not None]
                mean, std, k = mean_std(scores)
                row.append("-" if k == 0 else f"{mean:.4f} ± {std:.4f} (n={k})")
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

        lines.append("<details><summary>Per-seed values</summary>")
        lines.append("")
        for model in models:
            for artifact in artifacts:
                values = sorted(score_groups.get((benchmark, model, artifact), []))
                if not values:
                    continue
                detail = ", ".join(f"seed{s}={sc:.4f}" for s, sc in values)
                lines.append(f"- {model} / {artifact}: {detail}")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("## Training time & Claude cost (per model x method, across available seeds)")
    lines.append("")
    train_groups = defaultdict(list)
    for row in train_rows:
        train_groups[(row["model"], row["method"])].append(row)
    models_t = sorted({m for (m, _) in train_groups})
    methods_t = sorted({meth for (_, meth) in train_groups})
    lines.append("| model | method | seeds (k) | mean elapsed | total elapsed | mean claude cost | total claude cost |")
    lines.append("|---|---|---|---|---|---|---|")
    grand_elapsed = 0.0
    grand_cost = 0.0
    for model in models_t:
        for method in methods_t:
            rows = train_groups.get((model, method), [])
            if not rows:
                continue
            elapsed_vals = [r["elapsed_sec"] for r in rows]
            cost_vals = [r["claude_cost_usd"] for r in rows]
            grand_elapsed += sum(elapsed_vals)
            grand_cost += sum(cost_vals)
            lines.append(
                f"| {model} | {method} | {len(rows)} "
                f"| {sum(elapsed_vals) / len(rows) / 60:.1f} min "
                f"| {sum(elapsed_vals) / 3600:.2f} h "
                f"| ${sum(cost_vals) / len(rows):.3f} "
                f"| ${sum(cost_vals):.2f} |"
            )
    lines.append("")
    lines.append(f"**Grand totals:** training wall time {grand_elapsed / 3600:.2f} h, "
                  f"Claude cost ${grand_cost:.2f}")
    lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))


def write_json_csv(base_dir, seeds, eval_rows, train_rows):
    train_index = {(r["seed"], r["model"], r["method"]): r for r in train_rows}
    csv_rows = []
    for row in eval_rows:
        method = row["artifact"] if row["artifact"] != "baseline" else None
        train_info = train_index.get((row["seed"], row["model"], method), {}) if method else {}
        csv_rows.append({
            "seed": row["seed"],
            "benchmark": row["benchmark"],
            "model": row["model"],
            "artifact": row["artifact"],
            "score": row["score"],
            "n": row.get("n"),
            "train_elapsed_sec": train_info.get("elapsed_sec"),
            "claude_cost_usd": train_info.get("claude_cost_usd"),
            "claude_prompt_tokens": train_info.get("claude_prompt_tokens"),
            "claude_completion_tokens": train_info.get("claude_completion_tokens"),
        })

    save_json_atomic(os.path.join(base_dir, "final_results.json"), {
        "seeds": seeds,
        "eval_rows": eval_rows,
        "train_rows": train_rows,
        "csv_rows": csv_rows,
    })

    fieldnames = ["seed", "benchmark", "model", "artifact", "score", "n",
                  "train_elapsed_sec", "claude_cost_usd",
                  "claude_prompt_tokens", "claude_completion_tokens"]
    with open(os.path.join(base_dir, "final_results.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)


def main():
    parser = argparse.ArgumentParser(description="Aggregate multi-seed train+eval results into mean+/-std tables.")
    parser.add_argument("--base-dir", type=str, default="runs", dest="base_dir")
    args = parser.parse_args()

    seeds, eval_rows, train_rows = collect(args.base_dir)
    if not seeds:
        print(f"No seed* directories found under {args.base_dir}; nothing to aggregate.")
        return

    write_final_results_md(os.path.join(args.base_dir, "FINAL_RESULTS.md"), seeds, eval_rows, train_rows)
    write_json_csv(args.base_dir, seeds, eval_rows, train_rows)

    print(f"Aggregated {len(seeds)} seed(s): {seeds}")
    print(f"  {os.path.join(args.base_dir, 'FINAL_RESULTS.md')}")
    print(f"  {os.path.join(args.base_dir, 'final_results.json')}")
    print(f"  {os.path.join(args.base_dir, 'final_results.csv')}")


if __name__ == "__main__":
    main()
