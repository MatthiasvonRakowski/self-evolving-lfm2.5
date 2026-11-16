"""Re-score the saved MMLU-Pro predictions with a lenient answer parser, next to the strict one.

In transfer mode the baseline is the GSM8K seed workflow, whose prompt asks for a `#### <answer>`
line, while MMLU-Pro's own question text asks for "The answer is (X)". The strict parser
(src/benchmarks/mmlu_pro.py) accepts only the latter, so a large share of answers in every column,
baseline included, counts as wrong although the model did choose a letter (`#### F`, `\\boxed{I}`).
This script reads the cell files evaluate.py wrote, scores each prediction strictly and leniently,
and writes one table with both accuracies, both parse rates, and the paired McNemar tests on the
lenient score. No model is called.

    python rescore_mmlu_pro.py --base-dir runs --seeds 42 43 44 45 46

Needs the cached test split (~/.evoagentx/data/mmlu_pro/test.jsonl) for the gold letters, since the
cell files store only the prediction and the strict metric.
"""
import argparse
import csv
import json
import os
import re
import statistics
from collections import defaultdict

import numpy as np

from aggregate_results import bootstrap_ci, holm, load_json, mcnemar_exact

LETTERS = "ABCDEFGHIJ"

# Mirror of ANSWER_PATTERNS in src/benchmarks/mmlu_pro.py. Importing that module pulls in evoagentx
# (minutes on the box); the sanity check in score_cell() reports any drift between the two.
STRICT_PATTERNS = [
    re.compile(r"(?i:answer\s+is):?\s*\**\(?([A-J])\)?(?![A-Za-z])"),
    re.compile(r"[Aa]nswer:?\s*\**\(?([A-J])\)?(?![A-Za-z])"),
    re.compile(r"\(([A-J])\)\s*\.?\s*$"),
    re.compile(r"^\s*\**\(?([A-J])\)?\**\s*\.?\s*$", re.MULTILINE),
]

# Forms the transfer artifacts produce that the strict parser rejects: the GSM8K answer line and a
# LaTeX box, optionally with parentheses, bold or \text{} around the letter.
LENIENT_EXTRA = [
    re.compile(r"####\s*\**\(?([A-J])\)?\**(?![A-Za-z])"),
    re.compile(r"\\boxed\{\s*(?:\\text\{)?\s*\**\(?([A-J])\)?\**(?:\s*\})?\s*\}"),
]

COMPARISONS = [("aflow", "baseline"), ("mipro", "baseline")]


def extract(text, patterns):
    text = str(text)
    for pattern in patterns:
        matches = pattern.findall(text)
        if matches:
            return matches[-1].upper()
    return None


def extract_strict(text):
    return extract(text, STRICT_PATTERNS)


def extract_lenient(text):
    letter = extract_strict(text)
    return letter if letter is not None else extract(text, LENIENT_EXTRA)


def load_labels(path):
    labels = {}
    with open(os.path.expanduser(path)) as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                labels[str(row["question_id"])] = str(row["answer"]).upper()
    return labels


def score_cell(cell_path, labels):
    """Per-id strict and lenient scores of one cell file, execution errors left out as in
    aggregate_results.load_cell_scores. Returns None when the file has no records."""
    data = load_json(cell_path, {})
    records = [r for r in data.get("records") or [] if r and not r.get("execution_error")]
    if not records:
        return None
    strict, lenient, strict_parsed, lenient_parsed, drift, missing = {}, {}, 0, 0, 0, 0
    for record in records:
        rid = str(record["id"])
        gold = labels.get(rid)
        if gold is None:
            missing += 1
            continue
        s = extract_strict(record["prediction"])
        l = extract_lenient(record["prediction"])
        strict[rid] = 1.0 if s == gold else 0.0
        lenient[rid] = 1.0 if l == gold else 0.0
        strict_parsed += s is not None
        lenient_parsed += l is not None
        stored = record.get("metrics", {}).get("acc")
        if stored is not None and float(stored) != strict[rid]:
            drift += 1
    return {
        "n": len(strict), "strict": strict, "lenient": lenient,
        "strict_acc": sum(strict.values()) / len(strict) if strict else float("nan"),
        "lenient_acc": sum(lenient.values()) / len(lenient) if lenient else float("nan"),
        "strict_parse_rate": strict_parsed / len(strict) if strict else float("nan"),
        "lenient_parse_rate": lenient_parsed / len(lenient) if lenient else float("nan"),
        "drift": drift, "missing_label": missing,
    }


def collect(base_dir, seeds, labels, benchmark="mmlu_pro"):
    """One row per successful cell of `benchmark` in `seeds`, with per-id scores attached."""
    rows = []
    for seed in seeds:
        summary = load_json(os.path.join(base_dir, f"seed{seed}", "eval", "eval_summary.json"), {})
        for model, artifacts in sorted(summary.get(benchmark, {}).items()):
            for artifact, cell in sorted(artifacts.items()):
                if cell.get("status") != "success":
                    continue
                path = os.path.join(base_dir, f"seed{seed}", "eval", benchmark, model, f"{artifact}.json")
                scored = score_cell(path, labels)
                if scored is None:
                    continue
                rows.append({"seed": seed, "model": model, "artifact": artifact, "path": path, **scored})
    return rows


def paired(rows, key):
    """McNemar tests of each method against the baseline on the `key` ("strict"/"lenient") per-id
    scores, Holm-corrected within each seed x model family, as aggregate_results does."""
    rng = np.random.default_rng(0)
    by_cell = {(r["seed"], r["model"], r["artifact"]): r[key] for r in rows}
    families = defaultdict(list)
    for (seed, model, artifact) in by_cell:
        families[(seed, model)].append(artifact)
    comparisons = []
    for (seed, model), artifacts in sorted(families.items()):
        family = []
        for method, reference in COMPARISONS:
            if method not in artifacts or reference not in artifacts:
                continue
            a_scores, b_scores = by_cell[(seed, model, method)], by_cell[(seed, model, reference)]
            ids = sorted(set(a_scores) & set(b_scores))
            if not ids:
                continue
            a = np.array([a_scores[i] for i in ids])
            b = np.array([b_scores[i] for i in ids])
            family.append({
                "seed": seed, "model": model, "method": method, "reference": reference,
                "n_pairs": len(ids), "diff": float((a - b).mean()),
                "diff_ci": bootstrap_ci(a - b, rng), "p_value": mcnemar_exact(a, b),
            })
        for row, adjusted in zip(family, holm([r["p_value"] for r in family])):
            row["p_holm"] = adjusted
        comparisons.extend(family)
    return comparisons


def mean_std_text(values):
    if not values:
        return "-"
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return f"{mean:.4f} ± {std:.4f} (n={len(values)})"


def render(rows, strict_cmp, lenient_cmp, seeds):
    models = sorted({r["model"] for r in rows})
    artifacts = [a for a in ("baseline", "aflow", "mipro") if any(r["artifact"] == a for r in rows)]
    group = defaultdict(list)
    for r in rows:
        group[(r["model"], r["artifact"])].append(r)

    lines = ["# MMLU-Pro re-scored: strict vs lenient answer parsing", "",
             f"Seeds: {list(seeds)}. Strict = the scorer used by evaluate.py (\"The answer is (X)\" and "
             "close variants). Lenient = strict plus the GSM8K `#### X` line and `\\boxed{X}`, the forms "
             "the GSM8K-trained workflows make the models produce. Execution errors are left out of both, "
             "as in FINAL_RESULTS.md.", ""]
    for key, title in (("lenient_acc", "Lenient accuracy"), ("strict_acc", "Strict accuracy"),
                       ("lenient_parse_rate", "Lenient parse rate"), ("strict_parse_rate", "Strict parse rate")):
        lines += [f"## {title} (mean ± std over seeds)", "", "| model | " + " | ".join(artifacts) + " |",
                  "|---" * (1 + len(artifacts)) + "|"]
        for model in models:
            cells = [mean_std_text([r[key] for r in group[(model, a)]]) for a in artifacts]
            lines.append(f"| {model} | " + " | ".join(cells) + " |")
        lines.append("")

    for title, comparisons in (("lenient", lenient_cmp), ("strict", strict_cmp)):
        sig = [c for c in comparisons if c["p_holm"] < 0.05]
        counts = {m: (sum(1 for c in sig if c["method"] == m and c["diff"] > 0),
                      sum(1 for c in sig if c["method"] == m and c["diff"] < 0)) for m, _ in COMPARISONS}
        summary = ", ".join(f"{m}: {p} up / {n} down" for m, (p, n) in counts.items())
        lines += [f"## Paired comparisons on the {title} score (McNemar exact, Holm within seed x model)", "",
                  f"Significant at 0.05: {summary}.", "",
                  "| seed | model | comparison | n pairs | difference [95% CI] | p | p (Holm) |",
                  "|---|---|---|---|---|---|---|"]
        for c in comparisons:
            low, high = c["diff_ci"]
            marker = " *" if c["p_holm"] < 0.05 else ""
            lines.append(f"| {c['seed']} | {c['model']} | {c['method']} vs {c['reference']} | {c['n_pairs']} "
                         f"| {c['diff']:+.4f} [{low:+.3f}, {high:+.3f}] | {c['p_value']:.4f} | {c['p_holm']:.4f}{marker} |")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-dir", default="runs", dest="base_dir")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44, 45, 46])
    parser.add_argument("--data", default="~/.evoagentx/data/mmlu_pro/test.jsonl",
                        help="Cached MMLU-Pro test split (question_id -> answer).")
    parser.add_argument("--out", default=None, help="Markdown report (default <base-dir>/MMLU_PRO_RESCORED.md).")
    args = parser.parse_args()

    labels = load_labels(args.data)
    rows = collect(args.base_dir, args.seeds, labels)
    if not rows:
        raise SystemExit("no successful mmlu_pro cells found")
    drift = sum(r["drift"] for r in rows)
    missing = sum(r["missing_label"] for r in rows)
    if drift or missing:
        print(f"!! {drift} record(s) where the strict re-score differs from the stored metric, "
              f"{missing} record(s) without a gold label -- check the parser copy and the data file")

    strict_cmp = paired(rows, "strict")
    lenient_cmp = paired(rows, "lenient")
    report = render(rows, strict_cmp, lenient_cmp, args.seeds)
    out = args.out or os.path.join(args.base_dir, "MMLU_PRO_RESCORED.md")
    with open(out, "w") as f:
        f.write(report)
    with open(os.path.splitext(out)[0] + ".csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["seed", "model", "artifact", "n", "strict_acc", "lenient_acc",
                         "strict_parse_rate", "lenient_parse_rate"])
        for r in rows:
            writer.writerow([r["seed"], r["model"], r["artifact"], r["n"], f"{r['strict_acc']:.4f}",
                             f"{r['lenient_acc']:.4f}", f"{r['strict_parse_rate']:.4f}",
                             f"{r['lenient_parse_rate']:.4f}"])
    print(report.split("## Strict accuracy")[0])
    print(f"Written: {out} and {os.path.splitext(out)[0] + '.csv'}")


if __name__ == "__main__":
    main()
