from src.common import (
    resolve_model_id,
    executor_config,
    model_label,
    claude_config,
    tee_to_file,
    summarize_usage,
)
from src.AFlowOptimiser import AFlowOptimiser
from src.TextGradOptimiser import TextGradOptimiser
from src.MiproOptimiser import MiproOptimiser
from src.BilevelOptimiser import BilevelOptimiser
from src.bilevel.inner_base import InnerBudget
import os
import json
import time
import traceback
import argparse
import datetime

def build_method(method, args, model, out_dir, benchmark):

    exec_cfg = executor_config(model)
    if method == "aflow":
        return AFlowOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(out_dir, "aflow"),
            executor_config=exec_cfg,
            optimiser_config=claude_config(),
            graph_path=args.graph_path,
            benchmark=benchmark,
            validation_rounds=args.validation_rounds,
        )
    if method == "textgrad":
        return TextGradOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(out_dir, "textgrad"),
            executor_config=exec_cfg,
            optimiser_config=claude_config(),
            benchmark=benchmark,
        )
    if method == "mipro":
        return MiproOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(out_dir, "mipro"),
            executor_config=exec_cfg,
            optimiser_config=claude_config(),
            benchmark=benchmark,
        )
    if method == "bilevel":
        return BilevelOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(out_dir, "bilevel"),
            executor_config=exec_cfg,
            optimiser_config=claude_config(),
            graph_path=args.graph_path,
            benchmark=benchmark,
            inner=args.inner,
            validation_rounds=args.validation_rounds,
            inner_budget=InnerBudget(
                mipro_candidates=args.inner_mipro_candidates,
                mipro_steps=args.inner_mipro_steps,
                tg_steps=args.inner_tg_steps,
                dev_eval_k=args.dev_eval_k,
                seed=args.seed if args.seed is not None else 42,
            ),
        )
    raise ValueError(f"Unknown method: {method}")

def load_summary(path):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_summary(path, summary):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(summary, f, indent=2)
    os.replace(tmp, path)

def main():
    argparser = argparse.ArgumentParser(description="Run optimisers on benchmarks.")
    argparser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")
    argparser.add_argument("--rounds", type=int, default=None, help="Number of optimization rounds to run.")
    argparser.add_argument("--output_dir", type=str, default="output", help="Directory to save optimization results.")
    argparser.add_argument(
        "--graph_path", type=str, default=None,
        help="Path to the AFlow seed graph directory. Defaults to "
             "src/aflow_workflow/<benchmark>/ (per --benchmark) when omitted.",
    )
    argparser.add_argument(
        "--models", nargs="+", default=[None],
        help="One or more executor models to optimise (Ollama model names, e.g. "
             "'qwen3:1.7b' 'llama3.2:1b'). If omitted, defaults to LFM2.5. Each "
             "model must already be pulled in Ollama. Results are saved under "
             "<output_dir>/<model>/<method>/.",
    )
    argparser.add_argument(
        "--method", nargs="+",
        choices=["aflow", "textgrad", "mipro", "bilevel"],
        default=["aflow", "textgrad", "mipro"],
        help="Optimiser(s) to run. Can specify multiple.",
    )
    argparser.add_argument(
        "--benchmarks", nargs="+", choices=["gsm8k", "mmlu_pro", "ifeval"],
        default=["gsm8k"], dest="benchmarks",
        help="Benchmark(s) to optimise on. Each one gets its own trained artifact "
             "under <output_dir>/<benchmark>/<model>/<method>/, so every benchmark "
             "is evaluated against an artifact actually optimised for it.",
    )
    argparser.add_argument(
        "--validation_rounds", type=int, default=3,
        help="Validation passes per round used to rank rounds. At 1 the best round "
             "is picked from a single noisy dev pass over up to --rounds candidates.",
    )
    argparser.add_argument(
        "--inner", choices=["mipro", "textgrad", "mipro+textgrad", "none"],
        default="mipro+textgrad",
        help="[bilevel] Inner prompt optimiser(s) run on each candidate workflow.",
    )
    argparser.add_argument("--inner_mipro_candidates", type=int, default=4,
                           help="[bilevel] MIPRO instruction candidates per inner run.")
    argparser.add_argument("--inner_mipro_steps", type=int, default=4,
                           help="[bilevel] MIPRO optimisation steps per inner run.")
    argparser.add_argument("--inner_tg_steps", type=int, default=2,
                           help="[bilevel] TextGrad-lite refinement steps per inner run.")
    argparser.add_argument("--dev_eval_k", type=int, default=40,
                           help="[bilevel] Dev-subsample size used to score inner candidates.")
    argparser.add_argument(
        "--resume", action="store_true",
        help="Skip model+method combinations already marked 'success' in run_summary.json.",
    )
    argparser.add_argument(
        "--stop_on_error", action="store_true",
        help="Stop the whole run on the first failure (default: continue).",
    )
    args = argparser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    summary_path = os.path.join(args.output_dir, "run_summary.json")
    summary = load_summary(summary_path)
    summary["_meta"] = {
        "models": [resolve_model_id(m) for m in args.models],
        "methods": args.method,
        "benchmarks": args.benchmarks,
        "seed": args.seed,
        "rounds": args.rounds,
        "validation_rounds": args.validation_rounds,
        "last_launch": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    save_summary(summary_path, summary)

    print(f"\n=== Batch run ===")
    print(f"Models     : {[resolve_model_id(m) for m in args.models]}")
    print(f"Methods    : {args.method}")
    print(f"Benchmarks : {args.benchmarks}")
    print(f"Output     : {args.output_dir}/<benchmark>/<model>/<method>/")
    print(f"Resume     : {args.resume} | Stop on error: {args.stop_on_error}\n")

    for benchmark in args.benchmarks:
        summary.setdefault(benchmark, {})

        print(f"\n@@@@@@@@@@ BENCHMARK: {benchmark} @@@@@@@@@@")

        for model in args.models:
            label = model_label(model)
            resolved = resolve_model_id(model)
            model_out = os.path.join(args.output_dir, benchmark, label)
            summary[benchmark].setdefault(label, {})

            print(f"\n########## MODEL: {resolved}  (dir: {benchmark}/{label}) ##########")

            for method in args.method:
                if args.resume and summary[benchmark][label].get(method, {}).get("status") == "success":
                    print(f"--- Skipping {benchmark}/{label}/{method} (already succeeded; --resume) ---")
                    continue

                print(f"\n=== Running {benchmark} / {label} / {method} ===")
                started_at = datetime.datetime.now().isoformat(timespec="seconds")
                t0 = time.time()

                summary[benchmark][label][method] = {
                    "status": "running",
                    "started_at": started_at,
                    "executor_model": resolved,
                    "benchmark": benchmark,
                }
                save_summary(summary_path, summary)

                log_path = os.path.join(model_out, "logs", f"{method}.log")
                usage_log_path = os.path.join(model_out, "usage", f"{method}.jsonl")
                os.environ["LLM_USAGE_LOG"] = usage_log_path
                try:
                    with tee_to_file(log_path):
                        opt = build_method(method, args, model, model_out, benchmark)
                        opt.run()
                    elapsed = round(time.time() - t0, 1)
                    summary[benchmark][label][method] = {
                        "status": "success",
                        "started_at": started_at,
                        "elapsed_sec": elapsed,
                        "executor_model": resolved,
                        "benchmark": benchmark,
                        "log": log_path,
                        "usage": summarize_usage(usage_log_path),
                    }
                    save_summary(summary_path, summary)
                    print(f"--- {benchmark}/{label}/{method} finished OK in {elapsed}s (log: {log_path}) ---")

                except Exception as e:
                    elapsed = round(time.time() - t0, 1)
                    tb = traceback.format_exc()
                    try:
                        with open(log_path, "a") as lf:
                            lf.write("\n=== FAILED ===\n" + tb + "\n")
                    except Exception:
                        pass
                    summary[benchmark][label][method] = {
                        "status": "failed",
                        "started_at": started_at,
                        "elapsed_sec": elapsed,
                        "executor_model": resolved,
                        "benchmark": benchmark,
                        "error": str(e),
                        "traceback": tb,
                        "log": log_path,
                        "usage": summarize_usage(usage_log_path),
                    }
                    save_summary(summary_path, summary)
                    print(f"\n!!! {benchmark}/{label}/{method} FAILED after {elapsed}s: {e}")
                    print("--- continuing (see run_summary.json for the traceback) ---")
                    if args.stop_on_error:
                        print("--- --stop_on_error set: aborting everything ---")
                        _print_final(summary, args)
                        return
                finally:
                    os.environ.pop("LLM_USAGE_LOG", None)

    _print_final(summary, args)

def _print_final(summary, args):
    print("\n=== SUMMARY ===")
    for benchmark in args.benchmarks:
        print(f"  == {benchmark} ==")
        for model in args.models:
            label = model_label(model)
            print(f"  [{resolve_model_id(model)}]")
            for method in args.method:
                info = summary.get(benchmark, {}).get(label, {}).get(method, {})
                status = info.get("status", "not run")
                elapsed = info.get("elapsed_sec")
                line = f"    {method:<9} : {status}"
                if elapsed is not None:
                    line += f"  ({elapsed}s)"
                if status == "failed":
                    line += f"  -> {info.get('error', '')[:100]}"
                print(line)
    summary_path = os.path.join(args.output_dir, "run_summary.json")
    print(f"\nFull details saved to: {summary_path}\n")

if __name__ == "__main__":
    main()
