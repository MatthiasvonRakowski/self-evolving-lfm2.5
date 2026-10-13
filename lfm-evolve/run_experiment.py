
from src.common import (
    DEFAULT_OPTIMISER_MODEL, OPTIMISER_MODELFILE, executor_config, is_anthropic_model, model_label, ollama_name,
    optimiser_config,
)

import argparse
import datetime
import json
import os
import re
import shutil
import signal
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

def ollama_placement(names):
    """{name: PROCESSOR column of `ollama ps`} for the loaded models in `names`, e.g. '100% GPU'."""
    try:
        out = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return {}
    placement = {}
    for line in out.splitlines()[1:]:
        fields = line.split()
        where = re.search(r"\d+%(?:/\d+%)?\s+(?:CPU/GPU|GPU|CPU)", line)
        if fields and where and fields[0].split(":")[0] in names:
            placement[fields[0].split(":")[0]] = where.group(0)
    return placement

def preflight(models, base_dir, optimiser_model, benchmarks):
    print("\n=== Preflight checks ===")
    ok = True
    from evoagentx.models import LiteLLM

    # Executors first, on purpose: Ollama gives the VRAM to whichever model loads first. With the
    # 16B optimiser loaded first on the 8 GB card, the executor got 5 of its 17 layers on the GPU and
    # ran at 12 tokens/s instead of 146 (2026-10-13: 29 min instead of 3.5 min per 100 dev problems).
    executors = [ollama_name(m) for m in models]
    for model in models:
        bare = ollama_name(model)
        try:
            result = subprocess.run(["ollama", "show", bare], capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"  [FAIL] ollama model not available: {bare}\n{result.stderr.strip()}")
                ok = False
                continue
            reply = LiteLLM(config=executor_config(model)).generate(
                prompt="Reply with the single word: ready", parse_mode="str").content
            print(f"  [ok] executor {bare} answers (reply: {reply.strip()[:40]!r})")
        except Exception as e:
            print(f"  [FAIL] executor {bare} does not answer: {e}")
            ok = False

    try:
        reply = LiteLLM(config=optimiser_config(optimiser_model)).generate(
            prompt="Reply with the single word: ready", parse_mode="str").content
        where = "Anthropic API" if is_anthropic_model(optimiser_model) else "local Ollama"
        print(f"  [ok] optimiser {optimiser_model} answers via {where} (reply: {reply.strip()[:40]!r})")
    except Exception as e:
        hint = ("" if is_anthropic_model(optimiser_model) else
                f" -- the default optimiser is built with: ollama pull deepseek-coder-v2:16b && "
                f"ollama create {DEFAULT_OPTIMISER_MODEL} -f {OPTIMISER_MODELFILE}")
        print(f"  [FAIL] optimiser {optimiser_model} does not answer: {e}{hint}")
        ok = False

    loaded = executors + ([] if is_anthropic_model(optimiser_model) else [ollama_name(optimiser_model)])
    for name, where in ollama_placement(loaded).items():
        if where == "100% GPU" or name not in executors:
            print(f"  [ok] {name} is loaded {where}")
        else:
            print(f"  [WARN] executor {name} is loaded {where}: the optimiser took the VRAM first, expect the "
                  f"run to be several times slower. Unload both (ollama stop {ollama_name(optimiser_model)}; "
                  f"ollama stop {name}) and start again so the executor loads first; OLLAMA_KEEP_ALIVE=-1 in "
                  f"the Ollama service keeps the placement for the whole run.")

    for name in benchmarks:
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

def run_subprocess(cmd, log_path):
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

def generate_progress_md(base_dir, seeds, models, methods, driver_started_at, benchmarks=None):
    benchmarks = benchmarks or BENCHMARKS
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

    lines.append("## Training (status / elapsed / API cost; $0 with a local optimiser)")
    lines.append("")
    lines.append("| seed | benchmark | model | " + " | ".join(methods) + " |")
    lines.append("|---" * (3 + len(methods)) + "|")
    total_train_sec = 0.0
    total_claude_cost = 0.0
    for seed in seeds:
        train_summary = load_json(os.path.join(base_dir, f"seed{seed}", "train", "run_summary.json"), {})
        for benchmark in benchmarks:
            by_model = train_summary.get(benchmark, {})
            for label in labels:
                row = [str(seed), benchmark, label]
                for method in methods:
                    cell = by_model.get(label, {}).get(method, {})
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
                  f"API cost ${total_claude_cost:.2f}")
    lines.append("")

    lines.append("## Evaluation (cells done / total, failures)")
    lines.append("")
    lines.append("| seed | done | invalid | failed | total |")
    lines.append("|---|---|---|---|---|")
    # evaluate.py is only asked for the baseline plus the requested methods (see eval_cmd below).
    artifacts = [a for a in ARTIFACT_NAMES if a == "baseline" or a in methods]
    total_expected = len(benchmarks) * len(models) * len(artifacts)
    for seed in seeds:
        eval_summary = load_json(os.path.join(base_dir, f"seed{seed}", "eval", "eval_summary.json"), {})
        done = failed = invalid = 0
        for bmk, by_model in eval_summary.items():
            if bmk == "_meta":
                continue
            for label, by_artifact in by_model.items():
                for artifact, cell in by_artifact.items():
                    status = cell.get("status")
                    if status == "success":
                        done += 1
                    elif status == "invalid":
                        invalid += 1
                    elif status == "failed":
                        failed += 1
        lines.append(f"| {seed} | {done} | {invalid} | {failed} | {total_expected} |")
    lines.append("")

    os.makedirs(base_dir, exist_ok=True)
    tmp = os.path.join(base_dir, f"PROGRESS.md.tmp.{threading.get_ident()}")
    with open(tmp, "w") as f:
        f.write("\n".join(lines))
    os.replace(tmp, os.path.join(base_dir, "PROGRESS.md"))

def start_progress_thread(base_dir, seeds, models, methods, driver_started_at,
                           benchmarks=None, interval=60):
    stop_event = threading.Event()

    def loop():
        while not stop_event.is_set():
            try:
                generate_progress_md(base_dir, seeds, models, methods, driver_started_at, benchmarks)
            except Exception as e:
                print(f"[progress] update failed: {e}")
            stop_event.wait(interval)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return stop_event, thread

def main():
    parser = argparse.ArgumentParser(description="Multi-seed repeated train+eval experiment driver.")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44, 45, 46])
    parser.add_argument("--models", nargs="+", default=["lfm2.5-16k", "qwen3-1.7b-16k"])
    parser.add_argument("--methods", nargs="+", default=["aflow", "textgrad", "mipro", "bilevel"])
    parser.add_argument("--train-benchmarks", nargs="+", choices=BENCHMARKS, default=BENCHMARKS,
                         dest="train_benchmarks",
                         help="Benchmarks to train on. Each is trained and evaluated against its own "
                              "artifact and its own seed-workflow baseline.")
    parser.add_argument("--validation_rounds", type=int, default=3,
                         help="Validation passes per round used to rank rounds during training.")
    parser.add_argument("--max-error-rate", type=float, default=0.02, dest="max_error_rate",
                         help="Eval cells exceeding this execution-error rate are marked invalid.")
    parser.add_argument("--rounds", type=int, default=20,
                         help="AFlow/bilevel: maximum rounds (EvoAgentX stops earlier on convergence unless "
                              "--fixed-rounds). TextGrad/MIPRO: number of steps.")
    parser.add_argument("--fixed-rounds", action="store_true", dest="fixed_rounds",
                         help="[aflow/bilevel] Run exactly --rounds rounds; no convergence stop.")
    parser.add_argument("--skip-internal-test", action="store_true", dest="skip_internal_test",
                         help="Skip each optimiser's own pass over the test questions; evaluate.py scores "
                              "every artifact on the same split anyway. Always on for --smoke.")
    parser.add_argument("--n-test", type=int, default=300, dest="n_test")
    parser.add_argument("--base-dir", type=str, default="runs", dest="base_dir")
    parser.add_argument("--smoke", action="store_true",
                         help="Tiny end-to-end sanity run: seed 42 only, --rounds 2, --n-test 20, "
                              "base-dir runs_smoke, cheap bilevel inner budget.")
    parser.add_argument("--skip-preflight", action="store_true", dest="skip_preflight")
    parser.add_argument("--stop-on-error", action="store_true", dest="stop_on_error")
    parser.add_argument("--optimiser-model", default=DEFAULT_OPTIMISER_MODEL, dest="optimiser_model",
                         help="Model that rewrites workflows and prompts: a local Ollama model by default, "
                              "or 'anthropic/...' for Claude.")
    parser.add_argument("--inner", choices=["mipro", "textgrad", "mipro+textgrad", "none"], default=None,
                         help="[bilevel] Inner prompt optimiser(s); main.py's default when omitted.")
    for flag, help_text in [("mipro-candidates", "MIPRO instruction candidates per inner run"),
                            ("mipro-steps", "MIPRO optimisation steps per inner run"),
                            ("tg-steps", "TextGrad-lite refinement steps per inner run"),
                            ("tune-k", "train examples drawn per round for inner tuning"),
                            ("select-k", "dev examples used to accept or reject inner candidates")]:
        parser.add_argument(f"--inner-{flag}", type=int, default=None,
                            dest="inner_" + flag.replace("-", "_"),
                            help=f"[bilevel] {help_text}; main.py's default when omitted.")
    args = parser.parse_args()

    if args.smoke:
        args.seeds = [42]
        args.rounds = 2
        args.n_test = 20
        args.train_benchmarks = args.train_benchmarks[:1]
        args.validation_rounds = 1
        args.skip_internal_test = True
        if args.base_dir == "runs":
            args.base_dir = "runs_smoke"

    base_dir = args.base_dir
    os.makedirs(base_dir, exist_ok=True)

    # pid + state let tui.py follow the run and tell a live run from a dead one.
    driver_state_path = os.path.join(base_dir, "driver_state.json")
    driver_state = load_json(driver_state_path, {})
    driver_started_at = driver_state.get("started_at") or datetime.datetime.now().isoformat(timespec="seconds")
    driver_state.update(started_at=driver_started_at, args=vars(args), pid=os.getpid(),
                        state="preflight", ended_at=None,
                        launched_at=datetime.datetime.now().isoformat(timespec="seconds"))
    save_json_atomic(driver_state_path, driver_state)
    signal.signal(signal.SIGTERM, stop_on_sigterm)

    try:
        state = run_seeds(args, base_dir, driver_state, driver_state_path, driver_started_at)
    except KeyboardInterrupt:
        state = "stopped"
    except BaseException:
        driver_state.update(state="failed", ended_at=datetime.datetime.now().isoformat(timespec="seconds"))
        save_json_atomic(driver_state_path, driver_state)
        raise
    driver_state.update(state=state, current=None,
                        ended_at=datetime.datetime.now().isoformat(timespec="seconds"))
    save_json_atomic(driver_state_path, driver_state)
    if state == "stopped":
        sys.exit(130)
    if state == "preflight_failed":
        sys.exit(1)

def stop_on_sigterm(signum, frame):
    # tui.py stops a run with SIGTERM to the process group; unwind so driver_state ends as "stopped".
    raise KeyboardInterrupt

def run_seeds(args, base_dir, driver_state, driver_state_path, driver_started_at):
    if not args.skip_preflight:
        if not preflight(args.models, base_dir, args.optimiser_model, args.train_benchmarks):
            print("Preflight failed -- aborting (pass --skip-preflight to override).")
            return "preflight_failed"
    driver_state["state"] = "running"
    save_json_atomic(driver_state_path, driver_state)

    stop_event, progress_thread = start_progress_thread(
        base_dir, args.seeds, args.models, args.methods, driver_started_at,
        benchmarks=args.train_benchmarks,
    )
    progress_cb = lambda: generate_progress_md(
        base_dir, args.seeds, args.models, args.methods, driver_started_at, args.train_benchmarks)

    try:
        for seed in args.seeds:
            seed_dir = os.path.join(base_dir, f"seed{seed}")
            train_dir = os.path.join(seed_dir, "train")
            eval_dir = os.path.join(seed_dir, "eval")

            train_cmd = [
                # -u: the child writes into a pipe, which Python block-buffers; logs would lag behind the run.
                sys.executable, "-u", "main.py",
                "--seed", str(seed),
                "--rounds", str(args.rounds),
                "--benchmarks", *args.train_benchmarks,
                "--validation_rounds", str(args.validation_rounds),
                "--models", *args.models,
                "--method", *args.methods,
                "--output_dir", train_dir,
                "--optimiser_model", args.optimiser_model,
                "--resume",
            ]
            inner_budget = {}
            if args.smoke:
                inner_budget = {"mipro_candidates": 1, "mipro_steps": 1, "tg_steps": 1,
                                "tune_k": 6, "select_k": 3}
            for key in ("mipro_candidates", "mipro_steps", "tg_steps", "tune_k", "select_k"):
                if getattr(args, "inner_" + key) is not None:
                    inner_budget[key] = getattr(args, "inner_" + key)
            for key, value in inner_budget.items():
                train_cmd += [f"--inner_{key}", str(value)]
            if args.inner:
                train_cmd += ["--inner", args.inner]
            if args.fixed_rounds:
                train_cmd.append("--fixed_rounds")
            if args.skip_internal_test:
                train_cmd.append("--skip_internal_test")
            train_ok = run_stage(base_dir, seed, "train", train_cmd, driver_state, driver_state_path, progress_cb)
            if not train_ok and args.stop_on_error:
                print("--- --stop-on-error set: aborting after train failure ---")
                break

            eval_cmd = [
                sys.executable, "-u", "evaluate.py",
                "--seed", str(seed),
                "--n-test", str(args.n_test),
                "--benchmarks", *args.train_benchmarks,
                "--models", *args.models,
                "--artifacts", *[a for a in ARTIFACT_NAMES if a == "baseline" or a in args.methods],
                "--max-error-rate", str(args.max_error_rate),
                "--optimizer_output_dir", train_dir,
                "--output_dir", eval_dir,
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
    return "done"

if __name__ == "__main__":
    main()
