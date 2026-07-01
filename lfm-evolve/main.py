from src.AFlowOptimiser import AFlowOptimiser
from src.TextGradOptimiser import TextGradOptimiser
from src.MiproOptimiser import MiproOptimiser
import os
import json
import time
import traceback
import argparse
import datetime
import sys
import contextlib
import dotenv
from evoagentx.models import LiteLLMConfig, LiteLLM
import litellm

litellm.turn_off_message_logging = True
litellm.success_callback = []
litellm.failure_callback = []
litellm._async_success_callback = []
litellm._async_failure_callback = []


class _Tee:
    """Write to several streams at once (console + per-run log file)."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)
            s.flush()

    def flush(self):
        for s in self.streams:
            s.flush()


@contextlib.contextmanager
def tee_to_file(log_path):
    """Duplicate stdout+stderr into log_path for the duration of the block,
    while still printing to the console."""
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    f = open(log_path, "a", buffering=1)
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = _Tee(old_out, f)
    sys.stderr = _Tee(old_err, f)
    try:
        yield
    finally:
        sys.stdout, sys.stderr = old_out, old_err
        f.close()

# Load env once, up front, so ANTHROPIC_API_KEY is available everywhere below.
dotenv.load_dotenv()
os.environ["ANTHROPIC_API_BASE"] = "https://api.anthropic.com"  # extra safety; harmless

# Default local executor model (your custom 16k-context LFM2.5 Modelfile build).
# Any value(s) passed via --models override this.
DEFAULT_EXECUTOR_MODEL = "ollama_chat/lfm2.5-16k"

# ---------------------------------------------------------------------------
# DURABLE FIX for the global litellm.api_base leak.
#
# EvoAgentX requires api_base for local models and, on init, sets the
# module-global `litellm.api_base = config.api_base`. That global overrides
# both per-instance api_base and the ANTHROPIC_API_BASE env var, so any local
# (Ollama) model would otherwise hijack every later Anthropic call and route it
# to localhost. We wrap init_model to null the global after EVERY model init,
# so the executor and optimiser can coexist and AFlow rebuilding the executor
# mid-run can't re-poison it. Local still reaches Ollama via litellm's default
# ollama host; Anthropic reaches its real endpoint.
# ---------------------------------------------------------------------------
_orig_init_model = LiteLLM.init_model


def _init_model_no_global_base(self):
    _orig_init_model(self)
    litellm.api_base = None


LiteLLM.init_model = _init_model_no_global_base
# ---------------------------------------------------------------------------


def resolve_model_id(model=None):
    """Full litellm model id. None -> LFM2.5 default. Bare Ollama names like
    'qwen3:1.7b' get the 'ollama_chat/' prefix so they work from the CLI."""
    model_id = model or DEFAULT_EXECUTOR_MODEL
    if "/" not in model_id:
        model_id = f"ollama_chat/{model_id}"
    return model_id


def executor_config(model=None):
    """Local executor model via Ollama."""
    return LiteLLMConfig(
        model=resolve_model_id(model),
        is_local=True,
        api_base="http://localhost:11434",
    )


def model_label(model=None):
    """Short, filesystem-safe label for a model (used for output dirs and the
    summary keys). e.g. 'qwen3:1.7b' -> 'qwen3_1.7b'."""
    raw = model or DEFAULT_EXECUTOR_MODEL
    short = raw.split("/")[-1]
    return short.replace(":", "_").replace("/", "_").replace(".", "_").replace("-", "_")

def claude_config():
    """Cloud optimiser model (Claude Sonnet 4.6)."""
    return LiteLLMConfig(
        model="anthropic/claude-sonnet-4-6",
        anthropic_key=os.environ["ANTHROPIC_API_KEY"],
    )


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
        )
    if method == "textgrad":
        return TextGradOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(out_dir, "textgrad"),
            executor_config=exec_cfg,
            optimiser_config=claude_config(),
        )
    if method == "mipro":
        return MiproOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(out_dir, "mipro"),
            executor_config=exec_cfg,
            optimiser_config=claude_config(),
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
    argparser.add_argument("--graph_path", type=str, default="src/aflow_workflow", help="Path to the graph file.")
    argparser.add_argument(
        "--models", nargs="+", default=[None],
        help="One or more executor models to optimise (Ollama model names, e.g. "
             "'qwen3:1.7b' 'llama3.2:1b'). If omitted, defaults to LFM2.5. Each "
             "model must already be pulled in Ollama. Results are saved under "
             "<output_dir>/<model>/<method>/.",
    )
    argparser.add_argument(
        "--method", nargs="+",
        choices=["aflow", "textgrad", "mipro"],
        default=["aflow", "textgrad", "mipro"],  # run ALL three by default
        help="Optimiser(s) to run. Can specify multiple.",
    )
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
