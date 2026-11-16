"""rescore_mmlu_pro.py: lenient parsing must rescue the GSM8K-style and boxed answers and nothing else,
and the strict re-score must reproduce what evaluate.py stored."""
import json

import rescore_mmlu_pro as rescore


def test_lenient_accepts_hash_line_and_boxed_only():
    assert rescore.extract_strict("Reasoning.\n\nThe answer is (B).") == "B"
    assert rescore.extract_strict("The final numerical answer is:\n#### F") is None
    assert rescore.extract_lenient("The final numerical answer is:\n#### F") == "F"
    assert rescore.extract_lenient("so the correct answer is:\n$\\boxed{E}$") == "E"
    assert rescore.extract_lenient("$\\boxed{\\text{(I)}}$") == "I"
    assert rescore.extract_lenient("#### **J**") == "J"
    assert rescore.extract_lenient("Step 6: Choose the correct option\nThe answer is (X)") is None
    assert rescore.extract_lenient("E. VLDL and HD") is None


def _write_cell(tmp_path, seed, model, artifact, predictions, labels):
    cell_dir = tmp_path / f"seed{seed}" / "eval" / "mmlu_pro" / model
    cell_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for i, (pred, gold) in enumerate(zip(predictions, labels)):
        strict = rescore.extract_strict(pred)
        records.append({"id": i, "prediction": pred, "execution_error": False,
                        "metrics": {"acc": 1.0 if strict == gold else 0.0}})
    (cell_dir / f"{artifact}.json").write_text(json.dumps({"records": records, "main_metric": "acc"}))


def test_collect_scores_both_ways_and_pairs_against_baseline(tmp_path):
    labels = ["B", "C", "D", "A"]
    data = tmp_path / "test.jsonl"
    data.write_text("".join(json.dumps({"question_id": i, "answer": g}) + "\n" for i, g in enumerate(labels)))
    _write_cell(tmp_path, 42, "m", "baseline",
                ["The answer is (B).", "#### C", "$\\boxed{D}$", "no idea"], labels)
    _write_cell(tmp_path, 42, "m", "aflow",
                ["The answer is (B).", "#### C", "#### D", "#### A"], labels)
    summary = {"mmlu_pro": {"m": {"baseline": {"status": "success"}, "aflow": {"status": "success"},
                                  "mipro": {"status": "failed"}}}}
    (tmp_path / "seed42" / "eval" / "eval_summary.json").write_text(json.dumps(summary))

    rows = rescore.collect(str(tmp_path), [42], rescore.load_labels(str(data)))
    by_artifact = {r["artifact"]: r for r in rows}
    assert set(by_artifact) == {"baseline", "aflow"}  # the failed mipro cell is left out
    base = by_artifact["baseline"]
    assert base["strict_acc"] == 0.25 and base["lenient_acc"] == 0.75
    assert base["strict_parse_rate"] == 0.25 and base["lenient_parse_rate"] == 0.75
    assert base["drift"] == 0 and base["missing_label"] == 0
    assert by_artifact["aflow"]["lenient_acc"] == 1.0

    (comparison,) = rescore.paired(rows, "lenient")
    assert comparison["method"] == "aflow" and comparison["n_pairs"] == 4
    assert comparison["diff"] == 0.25 and 0 <= comparison["p_holm"] <= 1

    report = rescore.render(rows, rescore.paired(rows, "strict"), [comparison], [42])
    assert "## Lenient accuracy" in report and "| m | 0.7500" in report
