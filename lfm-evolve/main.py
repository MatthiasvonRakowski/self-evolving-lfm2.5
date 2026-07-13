# src.common must be imported first: it loads .env, silences litellm logging
# and applies the LiteLLM api_base monkeypatch (see its docstring).
from src.common import (
    resolve_model_id,
    executor_config,
    model_label,
    claude_config,
    tee_to_file,
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


def build_method(method, args, model, out_dir):
    """Construct the optimiser for a given method + executor model. Built lazily
    so a bad config for one combination doesn't stop the others."""
    exec_cfg = executor_config(model)
    if method == "aflow":
        return AFlowOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(out_dir, "aflow"),
            executor_config=exec_cfg,
            optimiser_config=claude_config(),
            graph_path=args.graph_path,
            benchmark=args.benchmark,
        )
    if method == "textgrad":
        return TextGradOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(out_dir, "textgrad"),
            executor_config=exec_cfg,
            optimiser_config=claude_config(),
            benchmark=args.benchmark,
        )
    if method == "mipro":
        return MiproOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(out_dir, "mipro"),
            executor_config=exec_cfg,
            optimiser_config=claude_config(),
            benchmark=args.benchmark,
        )
    if method == "bilevel":
        return BilevelOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(out_dir, "bilevel"),
            executor_config=exec_cfg,
            optimiser_config=claude_config(),
            graph_path=args.graph_path,
            benchmark=args.benchmark,
            inner=args.inner,
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
    """Write the summary atomically so a crash mid-write can't corrupt it."""
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
        default=["aflow", "textgrad", "mipro"],  # run the three baselines by default
        help="Optimiser(s) to run. Can specify multiple.",
    )
    argparser.add_argument(
        "--benchmark", choices=["gsm8k", "mmlu_pro", "ifeval"], default="gsm8k",
        help="Benchmark to optimise on (default: gsm8k).",
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
        "seed": args.seed,
        "rounds": args.rounds,
        "last_launch": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    save_summary(summary_path, summary)

    print(f"\n=== Batch run ===")
    print(f"Models   : {[resolve_model_id(m) for m in args.models]}")
    print(f"Methods  : {args.method}")
    print(f"Output   : {args.output_dir}/<model>/<method>/")
    print(f"Resume   : {args.resume} | Stop on error: {args.stop_on_error}\n")

    # Outer loop over models, inner loop over methods.
    for model in args.models:
        label = model_label(model)
        resolved = resolve_model_id(model)
        model_out = os.path.join(args.output_dir, label)
        summary.setdefault(label, {})

        print(f"\n########## MODEL: {resolved}  (dir: {label}) ##########")

        for method in args.method:
            # Resume: skip this model+method if it already succeeded.
            if args.resume and summary[label].get(method, {}).get("status") == "success":
                print(f"--- Skipping {label}/{method} (already succeeded; --resume) ---")
                continue

            print(f"\n=== Running {label} / {method} ===")
            started_at = datetime.datetime.now().isoformat(timespec="seconds")
            t0 = time.time()

            summary[label][method] = {
                "status": "running",
                "started_at": started_at,
                "executor_model": resolved,
            }
            save_summary(summary_path, summary)

            log_path = os.path.join(model_out, "logs", f"{method}.log")
            try:
                with tee_to_file(log_path):
                    opt = build_method(method, args, model, model_out)
                    opt.run()
                elapsed = round(time.time() - t0, 1)
                summary[label][method] = {
                    "status": "success",
                    "started_at": started_at,
                    "elapsed_sec": elapsed,
                    "executor_model": resolved,
                    "log": log_path,
                }
                save_summary(summary_path, summary)
                print(f"--- {label}/{method} finished OK in {elapsed}s (log: {log_path}) ---")

            except Exception as e:
                elapsed = round(time.time() - t0, 1)
                tb = traceback.format_exc()
                # Also append the traceback into this run's own log file.
                try:
                    with open(log_path, "a") as lf:
                        lf.write("\n=== FAILED ===\n" + tb + "\n")
                except Exception:
                    pass
                summary[label][method] = {
                    "status": "failed",
                    "started_at": started_at,
                    "elapsed_sec": elapsed,
                    "executor_model": resolved,
                    "error": str(e),
                    "traceback": tb,
                    "log": log_path,
                }
                save_summary(summary_path, summary)
                print(f"\n!!! {label}/{method} FAILED after {elapsed}s: {e}")
                print("--- continuing (see run_summary.json for the traceback) ---")
                if args.stop_on_error:
                    print("--- --stop_on_error set: aborting everything ---")
                    _print_final(summary, args)
                    return

    _print_final(summary, args)


def _print_final(summary, args):
    print("\n=== SUMMARY ===")
    for model in args.models:
        label = model_label(model)
        print(f"  [{resolve_model_id(model)}]")
        for method in args.method:
            info = summary.get(label, {}).get(method, {})
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
