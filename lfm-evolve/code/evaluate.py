from src.common import resolve_model_id, executor_config, model_label

import argparse
import asyncio
import datetime
import importlib
import json
import os
import re
import sys
import time
import types
from collections import defaultdict
from pathlib import Path
from typing import Callable, List, Optional

from evoagentx.agents import AgentManager
from evoagentx.evaluators import Evaluator
from evoagentx.models import LiteLLM
from evoagentx.workflow import SequentialWorkFlowGraph

from src.benchmarks import BENCHMARK_NAMES, get_benchmark

ARTIFACT_NAMES = ["baseline", "aflow", "textgrad", "mipro", "bilevel"]

ARTIFACT_PATHS = {
    "lfm2_5_16k": {
        "aflow": "results/lfm-results/aflow-results/workflows/good_run/aflow/round_22",
        "textgrad": "results/lfm-results/textgrad-results/workflows/tg_all/textgrad/GSM8KSplits_textgrad_best.json",
        "mipro": "results/lfm-results/mipro-results/workflows/mipro1/mipro/best_program.json",
    },
    "qwen3_1_7b": {
        "aflow": "results/comparaison-results/qwen3_1_7b/aflow/round_7",
        "textgrad": "results/comparaison-results/qwen3_1_7b/textgrad/GSM8KSplits_textgrad_best.json",
        "mipro": "results/comparaison-results/qwen3_1_7b/mipro/best_program.json",
    },
}

def load_aflow_artifact(round_dir) -> Callable:
    round_dir = Path(round_dir)
    prompt_src = (round_dir / "prompt.py").read_text()
    graph_src = (round_dir / "graph.py").read_text()
    uid = abs(hash(str(round_dir.resolve())))

    prompt_mod_name = f"_aflow_artifact_prompt_{uid}"
    prompt_mod = types.ModuleType(prompt_mod_name)
    exec(compile(prompt_src, str(round_dir / "prompt.py"), "exec"), prompt_mod.__dict__)
    sys.modules[prompt_mod_name] = prompt_mod

    fixed_src = re.sub(
        r"^import .*\.prompt as prompt_custom\s*$",
        f"import sys as _sys; prompt_custom = _sys.modules[{prompt_mod_name!r}]",
        graph_src, count=1, flags=re.MULTILINE,
    )
    graph_mod = types.ModuleType(f"_aflow_artifact_graph_{uid}")
    exec(compile(fixed_src, str(round_dir / "graph.py"), "exec"), graph_mod.__dict__)
    return graph_mod.Workflow

def load_baseline_workflow_class(benchmark_name: str) -> Callable:
    module = importlib.import_module(f"src.aflow_workflow.{benchmark_name}.graph")
    return module.Workflow

def resolve_round_dir(base: Path) -> Optional[Path]:
    base = Path(base)
    best_round_path = base / "best_round.json"
    if best_round_path.exists():
        with open(best_round_path) as f:
            best_round = json.load(f)["best_round"]
        round_dir = base / f"round_{best_round}"
        return round_dir if round_dir.exists() else None

    results_path = base / "results.json"
    if not results_path.exists():
        return None
    with open(results_path) as f:
        results = json.load(f)
    scores = defaultdict(list)
    for r in results:
        if "round" in r and "score" in r:
            scores[r["round"]].append(r["score"])
    if not scores:
        return None
    best_round = max(scores, key=lambda rnd: sum(scores[rnd]) / len(scores[rnd]))
    round_dir = base / f"round_{best_round}"
    return round_dir if round_dir.exists() else None

async def run_workflow_class(workflow_cls: Callable, benchmark, executor_llm: LiteLLM,
                              concurrency: int) -> List[dict]:
    workflow = workflow_cls(name=benchmark.name, llm_config=executor_llm.config, benchmark=benchmark)
    data = benchmark.get_test_data()
    semaphore = asyncio.Semaphore(concurrency)
    records = [None] * len(data)

    async def run_one(i, example):
        async with semaphore:
            try:
                prediction = await workflow(example["problem"])
            except Exception as e:
                prediction = f"<error: {e}>"
            metrics = benchmark.evaluate(prediction, benchmark.get_label(example))
            records[i] = {"id": benchmark.get_id(example), "prediction": prediction, "metrics": metrics}

    await asyncio.gather(*(run_one(i, ex) for i, ex in enumerate(data)))
    return records

async def run_mipro_predictor(prompt_template: str, benchmark, executor_llm: LiteLLM,
                               concurrency: int) -> List[dict]:
    data = benchmark.get_test_data()
    semaphore = asyncio.Semaphore(concurrency)
    records = [None] * len(data)

    async def run_one(i, example):
        async with semaphore:
            problem = example["problem"]
            if "{{problem}}" in prompt_template:
                filled = prompt_template.replace("{{problem}}", problem)
            else:
                filled = prompt_template.replace("{problem}", problem)
            try:
                response = await executor_llm.async_generate(prompt=filled, parse_mode="str")
                prediction = response.content
            except Exception as e:
                prediction = f"<error: {e}>"
            metrics = benchmark.evaluate(prediction, benchmark.get_label(example))
            records[i] = {"id": benchmark.get_id(example), "prediction": prediction, "metrics": metrics}

    await asyncio.gather(*(run_one(i, ex) for i, ex in enumerate(data)))
    return records

def run_textgrad_predictor(path: str, benchmark, executor_llm: LiteLLM, concurrency: int) -> List[dict]:
    graph = SequentialWorkFlowGraph.from_file(path)
    agent_manager = AgentManager()
    agent_manager.add_agents_from_workflow(graph, executor_llm.config)
    evaluator = Evaluator(
        llm=executor_llm,
        agent_manager=agent_manager,
        collate_func=lambda example: {"problem": example["problem"]},
        num_workers=concurrency,
        verbose=True,
    )
    evaluator.evaluate(graph=graph, benchmark=benchmark, eval_mode="test")
    return [
        {"id": example_id, "prediction": rec["prediction"], "metrics": rec["metrics"]}
        for example_id, rec in evaluator._evaluation_records.items()
    ]

def resolve_artifact_source(artifact: str, benchmark_name: str, label: str, args) -> Optional[str]:
    if artifact == "baseline":
        return "src.aflow_workflow." + benchmark_name
    if artifact == "bilevel":
        round_dir = resolve_round_dir(Path(args.optimizer_output_dir) / label / "bilevel")
        return str(round_dir) if round_dir else None
    if getattr(args, "artifacts_from_output", False):
        base = Path(args.optimizer_output_dir) / label / artifact
        if artifact == "aflow":
            round_dir = resolve_round_dir(base)
            return str(round_dir) if round_dir else None
        if artifact == "textgrad":
            matches = sorted(base.glob("*_textgrad_best.json"))
            if not matches:
                matches = sorted(base.glob("*_textgrad_final.json"))
            return str(matches[0]) if matches else None
        if artifact == "mipro":
            path = base / "best_program.json"
            return str(path) if path.exists() else None
    return ARTIFACT_PATHS.get(label, {}).get(artifact)

async def run_cell(benchmark_name: str, model: str, artifact: str, args) -> Optional[dict]:
    label = model_label(model)
    source = resolve_artifact_source(artifact, benchmark_name, label, args)
    if source is None:
        print(f"  [skip] {benchmark_name}/{label}/{artifact}: no artifact available for this model")
        return None

    benchmark = get_benchmark(benchmark_name, seed=args.seed, n_test=args.n_test)
    executor_llm = LiteLLM(config=executor_config(model))

    if artifact == "baseline":
        workflow_cls = load_baseline_workflow_class(benchmark_name)
        records = await run_workflow_class(workflow_cls, benchmark, executor_llm, args.concurrency)
    elif artifact in ("aflow", "bilevel"):
        workflow_cls = load_aflow_artifact(source)
        records = await run_workflow_class(workflow_cls, benchmark, executor_llm, args.concurrency)
    elif artifact == "mipro":
        with open(source) as f:
            prompt_template = json.load(f)["prompt"]
        records = await run_mipro_predictor(prompt_template, benchmark, executor_llm, args.concurrency)
    elif artifact == "textgrad":
        records = run_textgrad_predictor(source, benchmark, executor_llm, args.concurrency)
    else:
        raise ValueError(f"Unknown artifact: {artifact}")

    main_metric = getattr(benchmark, "MAIN_METRIC", None)
    scores = [r["metrics"].get(main_metric, 0.0) for r in records if r] if main_metric else []
    mean_score = sum(scores) / len(scores) if scores else 0.0

    return {
        "benchmark": benchmark_name,
        "model": resolve_model_id(model),
        "model_label": label,
        "artifact": artifact,
        "artifact_source": str(source),
        "n": len(records),
        "main_metric": main_metric,
        "mean_score": mean_score,
        "records": records,
    }

def save_json_atomic(path, payload):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    os.replace(tmp, path)

def write_summary_md(summary: dict, path: str):
    lines = ["# Evaluation summary", ""]
    for benchmark_name, by_model in summary.items():
        if benchmark_name == "_meta":
            continue
        lines.append(f"## {benchmark_name}")
        model_labels = sorted(by_model.keys())
        artifacts = sorted({a for m in by_model.values() for a in m.keys()})
        lines.append("| artifact | " + " | ".join(model_labels) + " |")
        lines.append("|---" * (len(model_labels) + 1) + "|")
        for artifact in artifacts:
            row = [artifact]
            for label in model_labels:
                cell = by_model.get(label, {}).get(artifact)
                if cell is None:
                    row.append("-")
                elif cell.get("status") == "success":
                    row.append(f"{cell['mean_score']:.4f}")
                else:
                    row.append(cell.get("status", "?"))
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))

def main():
    parser = argparse.ArgumentParser(description="Cross-benchmark evaluation of optimizer artifacts.")
    parser.add_argument("--benchmarks", nargs="+", choices=BENCHMARK_NAMES, default=BENCHMARK_NAMES)
    parser.add_argument("--models", nargs="+", default=[None],
                         help="Ollama model names, e.g. 'lfm2.5-16k' 'qwen3:1.7b'.")
    parser.add_argument("--artifacts", nargs="+", choices=ARTIFACT_NAMES, default=ARTIFACT_NAMES)
    parser.add_argument("--n-test", type=int, default=300, dest="n_test")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--concurrency", type=int, default=6,
                         help="Max concurrent local-model calls (keep local to avoid overwhelming Ollama).")
    parser.add_argument("--output_dir", type=str, default="eval-results")
    parser.add_argument("--optimizer_output_dir", type=str, default="output",
                         help="Where main.py wrote optimizer runs, used to resolve the 'bilevel' artifact "
                              "(<optimizer_output_dir>/<model_label>/bilevel/) and, with "
                              "--artifacts_from_output, aflow/textgrad/mipro too.")
    parser.add_argument("--artifacts_from_output", action="store_true",
                         help="Resolve aflow/textgrad/mipro artifacts fresh from --optimizer_output_dir "
                              "instead of the hardcoded ARTIFACT_PATHS (old pre-trained artifacts). "
                              "baseline is unaffected.")
    parser.add_argument("--resume", action="store_true", help="Skip cells already marked 'success'.")
    args = parser.parse_args()

    summary_path = os.path.join(args.output_dir, "eval_summary.json")
    summary = {}
    if os.path.exists(summary_path):
        try:
            with open(summary_path) as f:
                summary = json.load(f)
        except Exception:
            summary = {}

    for benchmark_name in args.benchmarks:
        summary.setdefault(benchmark_name, {})
        for model in args.models:
            label = model_label(model)
            summary[benchmark_name].setdefault(label, {})
            for artifact in args.artifacts:
                cell_path = os.path.join(args.output_dir, benchmark_name, label, f"{artifact}.json")

                if args.resume and summary[benchmark_name][label].get(artifact, {}).get("status") == "success":
                    print(f"--- Skipping {benchmark_name}/{label}/{artifact} (already succeeded; --resume) ---")
                    continue

                print(f"\n=== {benchmark_name} / {label} / {artifact} ===")
                started_at = datetime.datetime.now().isoformat(timespec="seconds")
                t0 = time.time()
                try:
                    result = asyncio.run(run_cell(benchmark_name, model, artifact, args))
                except Exception as e:
                    import traceback
                    print(f"!!! FAILED: {e}")
                    summary[benchmark_name][label][artifact] = {
                        "status": "failed", "error": str(e),
                        "traceback": traceback.format_exc(),
                        "started_at": started_at,
                        "elapsed_sec": round(time.time() - t0, 1),
                    }
                    save_json_atomic(summary_path, summary)
                    continue

                if result is None:
                    summary[benchmark_name][label][artifact] = {
                        "status": "unavailable",
                        "started_at": started_at,
                        "elapsed_sec": round(time.time() - t0, 1),
                    }
                    save_json_atomic(summary_path, summary)
                    continue

                save_json_atomic(cell_path, result)
                summary[benchmark_name][label][artifact] = {
                    "status": "success",
                    "mean_score": result["mean_score"],
                    "main_metric": result["main_metric"],
                    "n": result["n"],
                    "artifact_source": result["artifact_source"],
                    "path": cell_path,
                    "started_at": started_at,
                    "elapsed_sec": round(time.time() - t0, 1),
                }
                save_json_atomic(summary_path, summary)
                print(f"  -> mean {result['main_metric']}: {result['mean_score']:.4f}  (n={result['n']})")

    write_summary_md(summary, os.path.join(args.output_dir, "summary.md"))
    print(f"\nDone. Summary: {summary_path}")
    print(f"Table: {os.path.join(args.output_dir, 'summary.md')}")

if __name__ == "__main__":
    main()
