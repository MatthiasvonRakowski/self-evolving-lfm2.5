
import argparse
import json
import os
from collections import Counter
from pathlib import Path

ERROR_PREFIX = "<error:"

DEFAULT_MAX_ERROR_RATE = 0.02

def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def is_error(record):
    if record.get("execution_error"):
        return True
    prediction = record.get("prediction")
    return isinstance(prediction, str) and prediction.startswith(ERROR_PREFIX)

def error_signature(record):
    prediction = record.get("prediction") or ""
    if not isinstance(prediction, str):
        return "non-string prediction"
    text = prediction[len(ERROR_PREFIX):].strip().rstrip(">")
    for marker in ("litellm.Timeout", "APIConnectionError", "NameError", "AttributeError",
                    "KeyError", "TypeError", "ValueError"):
        if marker in text:
            return marker
    return text[:60]

def rescore_cell(cell_path, max_error_rate):
    data = load_json(cell_path)
    if not data or "records" not in data:
        return None
    records = [r for r in data["records"] if r]
    if not records:
        return None

    errors = [r for r in records if is_error(r)]
    error_rate = len(errors) / len(records)
    main_metric = data.get("main_metric")

    clean = [r for r in records if not is_error(r)]
    clean_scores = [r["metrics"].get(main_metric, 0.0) for r in clean] if main_metric else []
    clean_mean = sum(clean_scores) / len(clean_scores) if clean_scores else None
    parse_failures = sum(1 for r in records if r.get("metrics", {}).get("parse_failed"))

    return {
        "benchmark": data.get("benchmark"),
        "model_label": data.get("model_label"),
        "artifact": data.get("artifact"),
        "artifact_source": data.get("artifact_source"),
        "n": len(records),
        "main_metric": main_metric,
        "reported_mean_score": data.get("mean_score"),
        "n_errors": len(errors),
        "error_rate": error_rate,
        "parse_failures": parse_failures,
        "mean_score_excluding_errors": clean_mean,
        "n_scored": len(clean),
        "status": "invalid" if error_rate > max_error_rate else "success",
        "error_kinds": dict(Counter(error_signature(r) for r in errors).most_common(3)),
        "path": str(cell_path),
    }

def main():
    parser = argparse.ArgumentParser(
        description="Re-score existing eval cells with an execution-error gate. "
                    "Reads runs/ without modifying it and writes a corrected report elsewhere.")
    parser.add_argument("--base-dir", default="runs", dest="base_dir")
    parser.add_argument("--output-dir", default="rescored", dest="output_dir")
    parser.add_argument("--max-error-rate", type=float, default=DEFAULT_MAX_ERROR_RATE,
                         dest="max_error_rate")
    parser.add_argument("--trained-on", default=None, dest="trained_on",
                         help="Benchmark the artifacts in this run were trained on. Cells for any "
                              "other benchmark are reported as cross-task transfer.")
    args = parser.parse_args()

    base = Path(args.base_dir)
    cells = sorted(base.glob("seed*/eval/*/*/*.json"))
    if not cells:
        print(f"No eval cells found under {base}/seed*/eval/<benchmark>/<model>/<artifact>.json")
        return

    rows = []
    for cell_path in cells:
        row = rescore_cell(cell_path, args.max_error_rate)
        if row is None:
            continue
        parts = cell_path.parts
        row["seed"] = next((p for p in parts if p.startswith("seed")), "?")
        if args.trained_on:
            row["trained_on"] = args.trained_on
            row["transfer"] = row["benchmark"] != args.trained_on
        rows.append(row)

    os.makedirs(args.output_dir, exist_ok=True)
    json_path = os.path.join(args.output_dir, "rescored_summary.json")
    with open(json_path, "w") as f:
        json.dump(rows, f, indent=2)

    invalid = [r for r in rows if r["status"] == "invalid"]
    suspect = [r for r in rows if r["status"] == "success" and r["error_rate"] > 0]

    lines = ["# Re-scored evaluation summary", ""]
    lines.append(f"- Source: `{base}` (not modified)")
    lines.append(f"- Cells examined: {len(rows)}")
    lines.append(f"- Invalid (execution-error rate > {args.max_error_rate:.1%}): {len(invalid)}")
    lines.append(f"- Usable but with some errors: {len(suspect)}")
    if args.trained_on:
        transfer = [r for r in rows if r.get("transfer")]
        lines.append(f"- Cross-task transfer cells (trained on {args.trained_on}): {len(transfer)}")
    lines.append("")

    if invalid:
        lines.append("## Invalid cells")
        lines.append("")
        lines.append("| seed | benchmark | model | artifact | reported | errors | kinds |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in sorted(invalid, key=lambda r: -r["error_rate"]):
            kinds = ", ".join(f"{k} x{v}" for k, v in r["error_kinds"].items())
            lines.append(
                f"| {r['seed']} | {r['benchmark']} | {r['model_label']} | {r['artifact']} | "
                f"{r['reported_mean_score']:.4f} | {r['n_errors']}/{r['n']} "
                f"({r['error_rate']:.1%}) | {kinds} |")
        lines.append("")

    lines.append("## All cells")
    lines.append("")
    header = "| seed | benchmark | model | artifact | status | reported | excl. errors | errors |"
    if args.trained_on:
        header = header[:-1] + " transfer |"
    lines.append(header)
    lines.append("|---" * (9 if args.trained_on else 8) + "|")
    for r in sorted(rows, key=lambda r: (r["seed"], r["benchmark"], r["model_label"], r["artifact"])):
        clean = f"{r['mean_score_excluding_errors']:.4f}" if r["mean_score_excluding_errors"] is not None else "-"
        reported = f"{r['reported_mean_score']:.4f}" if r["reported_mean_score"] is not None else "-"
        row = (f"| {r['seed']} | {r['benchmark']} | {r['model_label']} | {r['artifact']} | "
               f"{r['status']} | {reported} | {clean} (n={r['n_scored']}) | "
               f"{r['n_errors']}/{r['n']} |")
        if args.trained_on:
            row = row[:-1] + (" yes |" if r.get("transfer") else " no |")
        lines.append(row)
    lines.append("")

    md_path = os.path.join(args.output_dir, "rescored_summary.md")
    with open(md_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Examined {len(rows)} cells from {base} (unmodified).")
    print(f"  invalid (>{args.max_error_rate:.1%} execution errors): {len(invalid)}")
    print(f"  usable but with some errors: {len(suspect)}")
    print(f"\nWrote {md_path}")
    print(f"Wrote {json_path}")

if __name__ == "__main__":
    main()
