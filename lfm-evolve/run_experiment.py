"""Driver for the multi-seed train+eval experiment (see PLAN.md).

For each seed, runs `main.py` (train all methods x models on GSM8K) then
`evaluate.py` (eval all artifacts x models x benchmarks), both as subprocesses
with --resume, so a crash/interruption anywhere just requires rerunning this
same command -- already-finished cells are skipped. Progress is written
continuously to <base_dir>/PROGRESS.md so the run (which takes days) can be
watched with `watch cat <base_dir>/PROGRESS.md` or `tail -f`.
"""

# src.common must be imported first: it loads .env and silences litellm
# logging (see its docstring). We only need model_label/resolve_model_id
# here; the actual optimiser/evaluator work happens in the main.py/
# evaluate.py subprocesses this script launches.
from src.common import model_label, resolve_model_id

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import threading
import time

from evaluate import ARTIFACT_NAMES

BENCHMARKS = ["gsm8k", "mmlu_pro", "ifeval"]


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return default


def save_json_atomic(path, payload):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Preflight
# --------------------------------------------------------------------------

def preflight(models, base_dir):
    """Cheap up-front checks so a config mistake surfaces in seconds, not
    after hours of compute. Returns True iff everything required passed
    (disk space is a warning only)."""
    print("\n=== Preflight checks ===")
    ok = True

    try:
        import litellm
        resp = litellm.completion(
            model="anthropic/claude-sonnet-4-6",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=4,
        )
        print(f"  [ok] Anthropic API key valid (ping: {resp.choices[0].message.content!r})")
    except Exception as e:
        print(f"  [FAIL] Anthropic API ping failed: {e}")
        ok = False

    for model in models:
        bare = model.split("/")[-1]
        try:
            result = subprocess.run(["ollama", "show", bare], capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"  [FAIL] ollama model not available: {bare}\n{result.stderr.strip()}")
                ok = False
            else:
                print(f"  [ok] ollama model present: {bare}")
        except Exception as e:
            print(f"  [FAIL] ollama show {bare} failed: {e}")
            ok = False

    for name in BENCHMARKS:
        try:
            from src.benchmarks import get_benchmark
            get_benchmark(name, seed=42)
            print(f"  [ok] benchmark loads (data cached): {name}")
        except Exception as e:
            print(f"  [FAIL] benchmark load failed for {name}: {e}")
            ok = False

    try:
        free_gb = shutil.disk_usage(".").free / (1024 ** 3)
        if free_gb < 20:
            print(f"  [WARN] only {free_gb:.1f} GB free disk space -- a multi-day run may fill the disk")
        else:
            print(f"  [ok] {free_gb:.1f} GB free disk space")
    except Exception as e:
        print(f"  [WARN] could not check disk space: {e}")

    print(f"=== Preflight {'PASSED' if ok else 'FAILED'} ===\n")
    return ok


# --------------------------------------------------------------------------
# Subprocess stage runner
# --------------------------------------------------------------------------

def run_subprocess(cmd, log_path):
    """Runs cmd, streaming stdout+stderr live to both the console and
    log_path (so `tail -f log_path` works while the driver runs)."""
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    with open(log_path, "a", buffering=1) as logf:
        header = f"\n=== {datetime.datetime.now().isoformat(timespec='seconds')} : {' '.join(cmd)} ===\n"
        print(header, end="")
        logf.write(header)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in proc.stdout:
            sys.stdout.write(line)
            logf.write(line)
        proc.wait()
        return proc.returncode


def run_stage(base_dir, seed, stage, cmd, driver_state, driver_state_path, progress_cb):
    """Runs one stage (train/eval) for one seed as a subprocess. Returns
    True iff it exited 0; never raises -- the caller decides what a failure
    means for the rest of the run (continue vs. --stop-on-error abort)."""
    seed_key = str(seed)
    driver_state.setdefault("seeds", {}).setdefault(seed_key, {})
    driver_state["current"] = {"seed": seed, "stage": stage}
    started_at = datetime.datetime.now().isoformat(timespec="seconds")
    t0 = time.time()
    driver_state["seeds"][seed_key][stage] = {"status": "running", "started_at": started_at}
    save_json_atomic(driver_state_path, driver_state)
    progress_cb()

    log_path = os.path.join(base_dir, f"seed{seed}", f"{stage}_driver.log")
    returncode = run_subprocess(cmd, log_path)
    elapsed = round(time.time() - t0, 1)

    driver_state["seeds"][seed_key][stage] = {
        "status": "success" if returncode == 0 else "failed",
        "started_at": started_at,
        "ended_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "elapsed_sec": elapsed,
        "returncode": returncode,
        "log": log_path,
    }
    save_json_atomic(driver_state_path, driver_state)
    progress_cb()

    if returncode != 0:
        print(f"\n!!! seed {seed} / {stage} FAILED (returncode={returncode}) after {elapsed}s -- see {log_path}")
    else:
        print(f"--- seed {seed} / {stage} OK in {elapsed}s ---")
    return returncode == 0


# --------------------------------------------------------------------------
# PROGRESS.md
# --------------------------------------------------------------------------

def generate_progress_md(base_dir, seeds, models, methods, driver_started_at):
    """Regenerated purely from on-disk state (driver_state.json + each
    seed's run_summary.json/eval_summary.json), so it's crash-safe and can be
    reconstructed even if the driver process died and was restarted."""
    driver_state = load_json(os.path.join(base_dir, "driver_state.json"), {})
    current = driver_state.get("current", {})
    labels = [model_label(m) for m in models]

    lines = ["# Experiment Progress", ""]
    lines.append(f"- Driver started: {driver_started_at}")
    lines.append(f"- Last updated: {datetime.datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- Current: seed={current.get('seed')} stage={current.get('stage')}")
    if current.get("seed") is not None and current.get("stage"):
        log_path = os.path.join(base_dir, f"seed{current['seed']}", f"{current['stage']}_driver.log")
        lines.append(f"- Live log: `tail -f {log_path}`")
    lines.append("")

    lines.append("## Training (status / elapsed / Claude cost)")
    lines.append("")
    lines.append("| seed | model | " + " | ".join(methods) + " |")
    lines.append("|---" * (2 + len(methods)) + "|")
    total_train_sec = 0.0
    total_claude_cost = 0.0
    for seed in seeds:
        train_summary = load_json(os.path.join(base_dir, f"seed{seed}", "train", "run_summary.json"), {})
        for label in labels:
            row = [str(seed), label]
            for method in methods:
                cell = train_summary.get(label, {}).get(method, {})
                status = cell.get("status", "pending")
                elapsed = cell.get("elapsed_sec")
                cost = cell.get("usage", {}).get("anthropic", {}).get("cost_usd")
                if elapsed:
                    total_train_sec += elapsed
                if cost:
                    total_claude_cost += cost
                parts = [status]
                if elapsed is not None:
                    parts.append(f"{elapsed:.0f}s")
                if cost:
                    parts.append(f"${cost:.2f}")
                row.append(" / ".join(parts))
            lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append(f"**Totals so far:** training wall time {total_train_sec / 3600:.1f}h, "
                  f"Claude cost ${total_claude_cost:.2f}")
    lines.append("")

    lines.append("## Evaluation (cells done / total, failures)")
    lines.append("")
    lines.append("| seed | done | failed | total |")
    lines.append("|---|---|---|---|")
    total_expected = len(BENCHMARKS) * len(models) * len(ARTIFACT_NAMES)
    for seed in seeds:
        eval_summary = load_json(os.path.join(base_dir, f"seed{seed}", "eval", "eval_summary.json"), {})
        done = failed = 0
        for bmk, by_model in eval_summary.items():
            if bmk == "_meta":
                continue
            for label, by_artifact in by_model.items():
                for artifact, cell in by_artifact.items():
                    if cell.get("status") == "success":
                        done += 1
                    elif cell.get("status") == "failed":
                        failed += 1
        lines.append(f"| {seed} | {done} | {failed} | {total_expected} |")
    lines.append("")

    # Unique tmp filename: this runs from both the periodic background thread
    # and directly from run_stage() on every stage transition, so two
    # concurrent writers sharing one tmp path could unlink/replace out from
    # under each other.
    os.makedirs(base_dir, exist_ok=True)
    tmp = os.path.join(base_dir, f"PROGRESS.md.tmp.{threading.get_ident()}")
    with open(tmp, "w") as f:
        f.write("\n".join(lines))
    os.replace(tmp, os.path.join(base_dir, "PROGRESS.md"))


def start_progress_thread(base_dir, seeds, models, methods, driver_started_at, interval=60):
    stop_event = threading.Event()

    def loop():
        while not stop_event.is_set():
            try:
                generate_progress_md(base_dir, seeds, models, methods, driver_started_at)
            except Exception as e:
                print(f"[progress] update failed: {e}")
            stop_event.wait(interval)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return stop_event, thread


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Multi-seed repeated train+eval experiment driver.")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44, 45, 46])
    parser.add_argument("--models", nargs="+", default=["lfm2.5-16k", "qwen3-1.7b-16k"])
    parser.add_argument("--methods", nargs="+", default=["aflow", "textgrad", "mipro", "bilevel"])
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--n-test", type=int, default=300, dest="n_test")
    parser.add_argument("--base-dir", type=str, default="runs", dest="base_dir")
    parser.add_argument("--smoke", action="store_true",
                         help="Tiny end-to-end sanity run: seed 42 only, --rounds 2, --n-test 20, "
                              "base-dir runs-smoke, cheap bilevel inner budget.")
    parser.add_argument("--skip-preflight", action="store_true", dest="skip_preflight")
    parser.add_argument("--stop-on-error", action="store_true", dest="stop_on_error")
    args = parser.parse_args()

    if args.smoke:
        args.seeds = [42]
        args.rounds = 2
        args.n_test = 20
        if args.base_dir == "runs":
            args.base_dir = "runs-smoke"

    base_dir = args.base_dir
    os.makedirs(base_dir, exist_ok=True)

    if not args.skip_preflight:
        if not preflight(args.models, base_dir):
            print("Preflight failed -- aborting (pass --skip-preflight to override).")
            sys.exit(1)

    driver_state_path = os.path.join(base_dir, "driver_state.json")
    driver_state = load_json(driver_state_path, {})
    driver_started_at = driver_state.get("started_at") or datetime.datetime.now().isoformat(timespec="seconds")
    driver_state["started_at"] = driver_started_at
    driver_state["args"] = vars(args)
    save_json_atomic(driver_state_path, driver_state)

    stop_event, progress_thread = start_progress_thread(
        base_dir, args.seeds, args.models, args.methods, driver_started_at,
    )
    progress_cb = lambda: generate_progress_md(base_dir, args.seeds, args.models, args.methods, driver_started_at)

    try:
        for seed in args.seeds:
            seed_dir = os.path.join(base_dir, f"seed{seed}")
            train_dir = os.path.join(seed_dir, "train")
            eval_dir = os.path.join(seed_dir, "eval")

            train_cmd = [
                sys.executable, "main.py",
                "--seed", str(seed),
                "--rounds", str(args.rounds),
                "--benchmark", "gsm8k",
                "--models", *args.models,
                "--method", *args.methods,
                "--output_dir", train_dir,
                "--resume",
            ]
            if args.smoke:
                train_cmd += [
                    "--inner_mipro_candidates", "1",
                    "--inner_mipro_steps", "1",
                    "--inner_tg_steps", "1",
                    "--dev_eval_k", "3",
                ]
            train_ok = run_stage(base_dir, seed, "train", train_cmd, driver_state, driver_state_path, progress_cb)
            if not train_ok and args.stop_on_error:
                print("--- --stop-on-error set: aborting after train failure ---")
                break

            eval_cmd = [
                sys.executable, "evaluate.py",
                "--seed", str(seed),
                "--n-test", str(args.n_test),
                "--benchmarks", *BENCHMARKS,
                "--models", *args.models,
                "--artifacts", *ARTIFACT_NAMES,
                "--optimizer_output_dir", train_dir,
                "--output_dir", eval_dir,
                "--artifacts_from_output",
                "--resume",
            ]
            eval_ok = run_stage(base_dir, seed, "eval", eval_cmd, driver_state, driver_state_path, progress_cb)
            if not eval_ok and args.stop_on_error:
                print("--- --stop-on-error set: aborting after eval failure ---")
                break
    finally:
        stop_event.set()
        progress_cb()

    print("\n=== All seeds finished; running aggregator ===")
    agg_cmd = [sys.executable, "aggregate_results.py", "--base-dir", base_dir]
    subprocess.run(agg_cmd)


if __name__ == "__main__":
    main()
