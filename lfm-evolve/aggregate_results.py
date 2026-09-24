
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
    seeds = discover_seeds(base_dir)
    eval_rows = []
    train_rows = []
    invalid_rows = []

    for seed in seeds:
        seed_dir = os.path.join(base_dir, f"seed{seed}")
        eval_summary = load_json(os.path.join(seed_dir, "eval", "eval_summary.json"), {})
        train_summary = load_json(os.path.join(seed_dir, "train", "run_summary.json"), {})

        for benchmark_name, by_model in eval_summary.items():
            if benchmark_name == "_meta":
                continue
            for label, by_artifact in by_model.items():
                for artifact, cell in by_artifact.items():
                    status = cell.get("status")
                    if status != "success":
                        if status == "invalid":
                            invalid_rows.append({
                                "seed": seed,
                                "benchmark": benchmark_name,
                                "model": label,
                                "artifact": artifact,
                                "reported_score": cell.get("mean_score"),
                                "error_rate": cell.get("error_rate"),
                                "reason": cell.get("invalid_reason", ""),
                            })
                        continue
                    eval_rows.append({
                        "seed": seed,
                        "benchmark": benchmark_name,
                        "model": label,
                        "artifact": artifact,
                        "score": cell.get("mean_score"),
                        "n": cell.get("n"),
                        "error_rate": cell.get("error_rate", 0.0),
                        "trained_on": cell.get("trained_on", benchmark_name),
                        "transfer": bool(cell.get("transfer", False)),
                    })

        for train_benchmark, by_label in _iter_train_benchmarks(train_summary):
            for label, by_method in by_label.items():
                if label == "_meta":
                    continue
                for method, cell in by_method.items():
                    if not isinstance(cell, dict) or cell.get("status") != "success":
                        continue
                    anthropic = (cell.get("usage") or {}).get("anthropic", {})
                    train_rows.append({
                        "seed": seed,
                        "benchmark": train_benchmark,
                        "model": label,
                        "method": method,
                        "elapsed_sec": cell.get("elapsed_sec", 0) or 0,
                        "claude_cost_usd": anthropic.get("cost_usd", 0) or 0,
                        "claude_prompt_tokens": anthropic.get("prompt_tokens", 0) or 0,
                        "claude_completion_tokens": anthropic.get("completion_tokens", 0) or 0,
                    })

    return seeds, eval_rows, train_rows, invalid_rows

def _iter_train_benchmarks(train_summary):
    for key, value in train_summary.items():
        if key == "_meta" or not isinstance(value, dict):
            continue
        nested = [v for v in value.values() if isinstance(v, dict)]
        is_benchmark_level = bool(nested) and all(
            all(isinstance(inner, dict) for inner in v.values()) and "status" not in v
            for v in nested
        )
        if is_benchmark_level:
            yield key, value
        else:
            yield None, {key: value}

def write_final_results_md(path, seeds, eval_rows, train_rows, invalid_rows=()):
    score_groups = defaultdict(list)
    for row in eval_rows:
        score_groups[(row["benchmark"], row["model"], row["artifact"])].append((row["seed"], row["score"]))

    lines = ["# Final Results", "", f"Seeds discovered: {seeds}", ""]
    if invalid_rows:
        lines.append(f"{len(invalid_rows)} cell(s) were excluded as invalid "
                     f"(too many execution errors to be a usable score):")
        lines.append("")
        lines.append("| seed | benchmark | model | artifact | reported | reason |")
        lines.append("|---|---|---|---|---|---|")
        for r in sorted(invalid_rows, key=lambda r: -(r.get("error_rate") or 0)):
            reported = r.get("reported_score")
            reported = f"{reported:.4f}" if isinstance(reported, (int, float)) else "-"
            lines.append(f"| {r['seed']} | {r['benchmark']} | {r['model']} | {r['artifact']} "
                         f"| {reported} | {r.get('reason','')} |")
        lines.append("")

    transfer_rows = [r for r in eval_rows if r.get("transfer")]
    if transfer_rows:
        pairs = sorted({(r["trained_on"], r["benchmark"]) for r in transfer_rows})
        lines.append("Cross-task transfer cells present (artifact not optimised on the benchmark "
                     "it is scored on): " + ", ".join(f"{a} -> {b}" for a, b in pairs))
        lines.append("")

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

def write_json_csv(base_dir, seeds, eval_rows, train_rows, invalid_rows=()):
    train_index = {}
    for r in train_rows:
        train_index[(r["seed"], r.get("benchmark"), r["model"], r["method"])] = r
        train_index.setdefault((r["seed"], None, r["model"], r["method"]), r)

    csv_rows = []
    for row in eval_rows:
        method = row["artifact"] if row["artifact"] != "baseline" else None
        trained_on = row.get("trained_on", row["benchmark"])
        train_info = {}
        if method:
            train_info = (train_index.get((row["seed"], trained_on, row["model"], method))
                          or train_index.get((row["seed"], None, row["model"], method))
                          or {})
        csv_rows.append({
            "seed": row["seed"],
            "benchmark": row["benchmark"],
            "trained_on": trained_on,
            "transfer": row.get("transfer", False),
            "model": row["model"],
            "artifact": row["artifact"],
            "score": row["score"],
            "n": row.get("n"),
            "error_rate": row.get("error_rate", 0.0),
            "train_elapsed_sec": train_info.get("elapsed_sec"),
            "claude_cost_usd": train_info.get("claude_cost_usd"),
            "claude_prompt_tokens": train_info.get("claude_prompt_tokens"),
            "claude_completion_tokens": train_info.get("claude_completion_tokens"),
        })

    save_json_atomic(os.path.join(base_dir, "final_results.json"), {
        "seeds": seeds,
        "eval_rows": eval_rows,
        "train_rows": train_rows,
        "invalid_rows": list(invalid_rows),
        "csv_rows": csv_rows,
    })

    fieldnames = ["seed", "benchmark", "trained_on", "transfer", "model", "artifact",
                  "score", "n", "error_rate",
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

    seeds, eval_rows, train_rows, invalid_rows = collect(args.base_dir)
    if not seeds:
        print(f"No seed* directories found under {args.base_dir}; nothing to aggregate.")
        return

    write_final_results_md(os.path.join(args.base_dir, "FINAL_RESULTS.md"), seeds,
                           eval_rows, train_rows, invalid_rows)
    write_json_csv(args.base_dir, seeds, eval_rows, train_rows, invalid_rows)

    if invalid_rows:
        print(f"  !! {len(invalid_rows)} cell(s) excluded as invalid (execution errors)")
    print(f"Aggregated {len(seeds)} seed(s): {seeds}")
    print(f"  {os.path.join(args.base_dir, 'FINAL_RESULTS.md')}")
    print(f"  {os.path.join(args.base_dir, 'final_results.json')}")
    print(f"  {os.path.join(args.base_dir, 'final_results.csv')}")

if __name__ == "__main__":
    main()
