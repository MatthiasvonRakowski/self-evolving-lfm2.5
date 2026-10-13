"""Compare transformer and non-transformer models on the seed (baseline) workflows.

Every model answers the same test questions with the same prompts and scorer, so the
accuracy differences are paired. A separate sequential probe measures speed and memory
through Ollama's native API, one model loaded at a time.

    python compare_models.py --models lfm2.5-16k qwen3-1.7b-16k llama3.2:1b granite4:1b-h --seeds 42 43 44

Each seed draws a different set of test questions, so several seeds show whether a gap between
models holds beyond one sample. Speed and memory do not depend on the questions; they are
measured once, on the first seed's questions.
"""
from src.common import model_label, ollama_name

import argparse
import asyncio
import datetime
import importlib
import itertools
import json
import os
import signal
import statistics
import sys
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

import evaluate as evaluate_module
from aggregate_results import bootstrap_ci, holm, mcnemar_exact, sign_flip_test
from evaluate import DEFAULT_MAX_ERROR_RATE, run_cell, save_json_atomic
from src.architectures import ARCHITECTURES, GROUP_ORDER
from src.benchmarks import BENCHMARK_NAMES, get_benchmark

OLLAMA_URL = "http://localhost:11434"


def ollama(path, payload=None, timeout=600):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(OLLAMA_URL + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def same_ollama_model(a, b):
    tag = lambda n: n if ":" in n else n + ":latest"
    return tag(a) == tag(b)


def describe_model(model, overrides):
    show = ollama("/api/show", {"model": ollama_name(model)})
    info = show.get("model_info", {})
    details = show.get("details", {})
    arch = info.get("general.architecture", details.get("family", "?"))
    group, description = ARCHITECTURES.get(arch, ("unknown", "not in ARCHITECTURES"))
    if model in overrides:
        group, description = overrides[model], f"{description} (set by --arch)"
    num_ctx = None
    for line in show.get("parameters", "").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "num_ctx":
            num_ctx = int(parts[1])
    return {
        "model": model,
        "label": model_label(model),
        "architecture": arch,
        "group": group,
        "description": description,
        "parameters": info.get("general.parameter_count"),
        "parameter_size": details.get("parameter_size"),
        "quantization": details.get("quantization_level"),
        "num_ctx": num_ctx,
    }


def seed_prompt(benchmark_name):
    module = importlib.import_module(f"src.aflow_workflow.{benchmark_name}.prompt")
    for name, value in vars(module).items():
        if name.isupper() and isinstance(value, str):
            return value
    raise ValueError(f"no prompt constant in src.aflow_workflow.{benchmark_name}.prompt")


def unload_all():
    for loaded in ollama("/api/ps").get("models", []):
        ollama("/api/generate", {"model": loaded["name"], "keep_alive": 0})
    for _ in range(30):
        if not ollama("/api/ps").get("models"):
            return
        time.sleep(1)


def speed_probe(model, benchmarks, args, status=None):
    name = ollama_name(model)
    unload_all()
    options = {"temperature": 0, "seed": args.seed, "num_predict": args.max_new_tokens}
    warm = ollama("/api/generate", {"model": name, "prompt": "Hello", "stream": False,
                                    "options": options})
    cold_load_s = warm.get("load_duration", 0) / 1e9

    prompts = []
    for benchmark_name in benchmarks:
        instruction = seed_prompt(benchmark_name)
        data = get_benchmark(benchmark_name, seed=args.seed, n_test=args.n_test).get_test_data()
        prompts += [(benchmark_name, instruction + ex["problem"]) for ex in data[:args.speed_samples]]

    samples = []
    for i, (benchmark_name, prompt) in enumerate(prompts):
        if status:
            status.progress(i, len(prompts))
        t0 = time.perf_counter()
        r = ollama("/api/generate", {"model": name, "prompt": prompt,
                                     "stream": False, "options": options})
        wall = time.perf_counter() - t0
        samples.append({
            "benchmark": benchmark_name,
            "prompt_tokens": r.get("prompt_eval_count", 0),
            "output_tokens": r.get("eval_count", 0),
            # Thinking models (qwen3) return their reasoning separately; it still costs time.
            "output_chars": len(r.get("response", "")) + len(r.get("thinking", "")),
            "thinking_chars": len(r.get("thinking", "")),
            "prefill_s": r.get("prompt_eval_duration", 0) / 1e9,
            "decode_s": r.get("eval_duration", 0) / 1e9,
            "latency_s": wall,
        })

    loaded = next((m for m in ollama("/api/ps").get("models", [])
                   if same_ollama_model(m.get("name", ""), name)), {})
    return {
        "cold_load_s": cold_load_s,
        "memory_bytes": loaded.get("size"),
        "vram_bytes": loaded.get("size_vram"),
        "context_length": loaded.get("context_length"),
        "samples": samples,
    }


def summarize_speed(probe):
    s = probe["samples"]
    if not s:
        return {}

    def med(values):
        values = [v for v in values if v is not None]
        return statistics.median(values) if values else None

    return {
        "n": len(s),
        "decode_tok_s": med([x["output_tokens"] / x["decode_s"] for x in s if x["decode_s"] > 0]),
        "prefill_tok_s": med([x["prompt_tokens"] / x["prefill_s"] for x in s if x["prefill_s"] > 0]),
        "prefill_s": med([x["prefill_s"] for x in s]),
        "latency_s": med([x["latency_s"] for x in s]),
        "latency_p90_s": float(np.percentile([x["latency_s"] for x in s], 90)),
        "output_tokens": med([x["output_tokens"] for x in s]),
        "output_chars_s": med([x["output_chars"] / x["latency_s"] for x in s if x["latency_s"] > 0]),
        "cold_load_s": probe["cold_load_s"],
        "memory_gb": probe["memory_bytes"] / 1e9 if probe["memory_bytes"] else None,
        "vram_gb": probe["vram_bytes"] / 1e9 if probe["vram_bytes"] is not None else None,
        "context_length": probe["context_length"],
    }


def cell_scores(cell):
    metric = cell.get("main_metric")
    return {str(r["id"]): float(r["metrics"].get(metric, 0.0))
            for r in cell.get("records", []) if r and not r.get("execution_error")}


def pooled_scores(cells_by_seed):
    """Question-level scores of every seed, keyed "seed:id" so seeds never collide."""
    return {f"{seed}:{qid}": score
            for seed, cell in cells_by_seed.items() for qid, score in cell_scores(cell).items()}


def pairwise(benchmark_name, cells, infos, all_pairs, rng):
    """cells: {model: {seed: cell}} for valid cells. Pairs are pooled over seeds."""
    family = []
    for a_model, b_model in itertools.combinations(cells, 2):
        a_info, b_info = infos[a_model], infos[b_model]
        cross = a_info["group"] != b_info["group"]
        if not cross and not all_pairs:
            continue
        # Put the non-transformer first so "diff" reads as non-transformer minus transformer.
        if GROUP_ORDER[a_info["group"]] > GROUP_ORDER[b_info["group"]]:
            a_model, b_model = b_model, a_model
        sa, sb = pooled_scores(cells[a_model]), pooled_scores(cells[b_model])
        ids = sorted(set(sa) & set(sb))
        if not ids:
            continue
        a = np.array([sa[i] for i in ids])
        b = np.array([sb[i] for i in ids])
        diff = a - b
        binary = set(np.unique(np.concatenate([a, b]))) <= {0.0, 1.0}
        per_seed = {}
        for seed in sorted(set(cells[a_model]) & set(cells[b_model])):
            ka, kb = cell_scores(cells[a_model][seed]), cell_scores(cells[b_model][seed])
            common = set(ka) & set(kb)
            if common:
                per_seed[seed] = float(np.mean([ka[i] - kb[i] for i in common]))
        family.append({
            "benchmark": benchmark_name, "model_a": a_model, "model_b": b_model,
            "cross_architecture": cross, "n_pairs": len(ids), "per_seed_diff": per_seed,
            "seeds_a_ahead": sum(d > 0 for d in per_seed.values()),
            "seeds_b_ahead": sum(d < 0 for d in per_seed.values()),
            "score_a": float(a.mean()), "score_b": float(b.mean()),
            "diff": float(diff.mean()), "diff_ci": bootstrap_ci(diff, rng),
            "test": "McNemar exact" if binary else "paired sign-flip",
            "p_value": mcnemar_exact(a, b) if binary else sign_flip_test(diff, rng),
        })
    for row, adjusted in zip(family, holm([r["p_value"] for r in family])):
        row["p_holm"] = adjusted
    return family


def fmt(value, spec=".1f", missing="–"):
    return missing if value is None else format(value, spec)


def write_report(path, infos, accuracy, speed, comparisons, args):
    models = sorted(infos, key=lambda m: (GROUP_ORDER[infos[m]["group"]], m))
    lines = [f"# Architecture comparison ({datetime.date.today().isoformat()})", ""]
    lines.append(f"Seed workflows (no optimisation), seeds {' '.join(map(str, args.seeds))}, n_test {args.n_test} "
                 f"per seed, same questions for every model within a seed.")
    lines.append("")

    lines += ["## Models", "",
              "| model | group | architecture | params | quant | num_ctx |",
              "|---|---|---|---|---|---|"]
    for m in models:
        i = infos[m]
        lines.append(f"| {m} | {i['group']} | {i['architecture']} ({i['description']}) | "
                     f"{i['parameter_size'] or '–'} | {i['quantization'] or '–'} | "
                     f"{i['num_ctx'] or 'default'} |")
    quants = {infos[m]["quantization"] for m in models}
    if len(quants) > 1:
        lines += ["", f"> Quantisation differs between models ({', '.join(sorted(map(str, quants)))}). "
                      "Accuracy, speed and memory all depend on it."]
    contexts = {speed[m].get("context_length") for m in models if speed.get(m)}
    if len(contexts) > 1:
        lines += ["", f"> Context length differs between models ({', '.join(sorted(map(str, contexts)))}). "
                      "Memory includes the cache for that context; use Modelfiles with the same num_ctx."]
    if any(infos[m]["group"] == "unknown" for m in models):
        lines += ["", "> Some architectures are unknown. Add them to ARCHITECTURES or pass "
                      "`--arch model=transformer|non-transformer`."]
    lines.append("")

    if accuracy:
        lines += ["## Accuracy", "",
                  "Mean over seeds (± std across seeds when there are several), with a 95% bootstrap "
                  "interval over all questions of all seeds.", "",
                  "| model | group | " + " | ".join(args.benchmarks) + " |",
                  "|---|---|" + "---|" * len(args.benchmarks)]
        for m in models:
            row = [m, infos[m]["group"]]
            for b in args.benchmarks:
                cell = accuracy.get(b, {}).get(m)
                if not cell:
                    row.append("–")
                    continue
                lo, hi = cell["ci"]
                std = f" ±{cell['seed_std']:.3f}" if cell.get("seed_std") is not None else ""
                text = f"{fmt(cell['mean_score'], '.3f')}{std} [{fmt(lo, '.3f')}, {fmt(hi, '.3f')}]"
                if cell["status"] == "invalid":
                    text = f"INVALID ({cell['error_rate']:.0%} errors)"
                else:
                    if cell["invalid_seeds"]:
                        text += f" ({len(cell['invalid_seeds'])} seed(s) invalid)"
                    if cell["n_errors"]:
                        text += f" ({cell['n_errors']} err)"
                row.append(text)
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    if comparisons:
        lines += ["## Paired comparisons", "",
                  "Same questions for both models, pooled over seeds. diff = A − B; p is Holm-corrected "
                  "within each benchmark. Cross-architecture pairs put the non-transformer as A. "
                  "\"Seeds A/B ahead\" counts the seeds in which each model scored higher.", "",
                  "| benchmark | A | B | cross-arch | n | A | B | diff [95% CI] | test | p (Holm) | seeds A/B ahead |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for c in comparisons:
            lo, hi = c["diff_ci"]
            star = " *" if c["p_holm"] < 0.05 else ""
            lines.append(
                f"| {c['benchmark']} | {c['model_a']} | {c['model_b']} | "
                f"{'yes' if c['cross_architecture'] else 'no'} | {c['n_pairs']} | "
                f"{c['score_a']:.3f} | {c['score_b']:.3f} | "
                f"{c['diff']:+.3f} [{fmt(lo, '+.3f')}, {fmt(hi, '+.3f')}] | {c['test']} | "
                f"{c['p_holm']:.4f}{star} | {c['seeds_a_ahead']}/{c['seeds_b_ahead']} of "
                f"{len(c['per_seed_diff'])} |")
        lines.append("")

    if speed:
        lines += ["## Speed", "",
                  f"Sequential requests through Ollama's `/api/generate`, one model loaded at a time, "
                  f"{args.speed_samples} questions per benchmark, temperature 0, at most "
                  f"{args.max_new_tokens} new tokens. Medians. Tokenisers differ between models, "
                  "so tokens/s is not strictly comparable; latency per question and output chars/s are.",
                  "",
                  "| model | group | decode tok/s | prefill tok/s | prefill s | latency s (p50 / p90) "
                  "| output tokens | output chars/s | cold load s |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for m in models:
            s = speed.get(m)
            if not s:
                continue
            lines.append(
                f"| {m} | {infos[m]['group']} | {fmt(s['decode_tok_s'])} | {fmt(s['prefill_tok_s'])} | "
                f"{fmt(s['prefill_s'], '.3f')} | {fmt(s['latency_s'], '.2f')} / "
                f"{fmt(s['latency_p90_s'], '.2f')} | {fmt(s['output_tokens'], '.0f')} | "
                f"{fmt(s['output_chars_s'])} | {fmt(s['cold_load_s'], '.2f')} |")
        lines += ["", "## Memory", "",
                  "Loaded size from `/api/ps`. It includes the KV cache / recurrent state for the "
                  "context length shown, which is where non-transformer layers save memory.", "",
                  "| model | group | total GB | on GPU GB | context length |",
                  "|---|---|---|---|---|"]
        for m in models:
            s = speed.get(m)
            if not s:
                continue
            lines.append(f"| {m} | {infos[m]['group']} | {fmt(s['memory_gb'], '.2f')} | "
                         f"{fmt(s['vram_gb'], '.2f')} | {s['context_length'] or '–'} |")
        lines.append("")

    Path(path).write_text("\n".join(lines))


class RunStatus:
    """Progress of the current run in <output_dir>/status.json, read live by tui.py."""

    def __init__(self, path, tasks, args):
        self.path = path
        self._last_write = 0.0
        self.data = {
            "pid": os.getpid(),
            "state": "running",
            "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "config": {"models": args.models, "benchmarks": args.benchmarks, "n_test": args.n_test,
                       "seeds": args.seeds, "speed_samples": args.speed_samples},
            "current": None,
            "progress": None,
            "tasks": tasks,
            "error": None,
        }
        self.write()

    def start(self, task):
        task.update(status="running", started=time.time())
        self.data["current"] = task
        self.data["progress"] = None
        self.write()

    def finish(self, task, status, **extra):
        task.update(status=status, elapsed_s=round(time.time() - task.get("started", time.time()), 1),
                    **extra)
        self.data["current"] = None
        self.data["progress"] = None
        self.write()

    def progress(self, done, total):
        self.data["progress"] = {"done": done, "total": total}
        self.write(throttle=1.0)

    def end(self, state, error=None):
        self.data.update(state=state, error=error, current=None, progress=None,
                         ended_at=datetime.datetime.now().isoformat(timespec="seconds"))
        self.write()

    def write(self, throttle=0.0):
        now = time.time()
        if throttle and now - self._last_write < throttle:
            return
        self._last_write = now
        self.data["updated_at"] = now
        save_json_atomic(self.path, self.data)


def track_accuracy_progress(status):
    # run_cell builds its own benchmark; wrap it so each scored answer reports progress.
    original = evaluate_module.get_benchmark

    def wrapped(*a, **k):
        benchmark = original(*a, **k)
        total = len(benchmark.get_test_data())
        scored = [0]
        inner = benchmark.evaluate

        def evaluate(prediction, label):
            scored[0] += 1
            status.progress(scored[0], total)
            return inner(prediction, label)

        benchmark.evaluate = evaluate
        return benchmark

    evaluate_module.get_benchmark = wrapped


def is_valid(cell, args):
    return cell["error_rate"] <= args.max_error_rate


def accuracy_entry(cells_by_seed, args, rng):
    """One model on one benchmark, over every finished seed. Invalid seeds are left out."""
    valid = {seed: c for seed, c in cells_by_seed.items() if is_valid(c, args)}
    means = [c["mean_score"] for c in valid.values()]
    n = sum(c["n"] for c in cells_by_seed.values())
    n_errors = sum(c["n_errors"] for c in cells_by_seed.values())
    any_cell = next(iter(cells_by_seed.values()))
    return {
        "mean_score": statistics.mean(means) if means else None,
        "seed_std": statistics.stdev(means) if len(means) > 1 else None,
        "main_metric": any_cell["main_metric"],
        "ci": bootstrap_ci(list(pooled_scores(valid).values()), rng),
        "per_seed": {seed: {"mean_score": c["mean_score"], "error_rate": c["error_rate"],
                            "status": "success" if is_valid(c, args) else "invalid"}
                     for seed, c in sorted(cells_by_seed.items())},
        "valid_seeds": sorted(valid),
        "invalid_seeds": sorted(set(cells_by_seed) - set(valid)),
        "n": n, "n_errors": n_errors, "error_rate": n_errors / n if n else 1.0,
        "status": "success" if valid else "invalid",
    }


def write_outputs(out, infos, cells, speed, args):
    """cells: {benchmark: {model: {seed: cell}}}."""
    rng = np.random.default_rng(0)
    accuracy, comparisons = {}, []
    for benchmark_name, by_model in cells.items():
        accuracy[benchmark_name] = {m: accuracy_entry(by_seed, args, rng) for m, by_seed in by_model.items()}
        valid = {m: {seed: c for seed, c in by_seed.items() if is_valid(c, args)}
                 for m, by_seed in by_model.items()}
        valid = {m: by_seed for m, by_seed in valid.items() if by_seed}
        comparisons += pairwise(benchmark_name, valid, infos, args.all_pairs, rng)
    save_json_atomic(out / "comparison.json",
                     {"models": infos, "accuracy": accuracy, "speed": speed, "comparisons": comparisons})
    write_report(out / "report.md", infos, accuracy, speed, comparisons, args)


def stop_on_sigterm(signum, frame):
    # The TUI's "stop" sends SIGTERM; treat it like Ctrl-C so status.json ends as "stopped".
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description="Compare transformer and non-transformer models.")
    parser.add_argument("--models", nargs="+", required=True,
                        help="Ollama model names, e.g. lfm2.5-16k qwen3-1.7b-16k llama3.2:1b")
    parser.add_argument("--arch", nargs="*", default=[], metavar="MODEL=GROUP",
                        help="Override the detected group, e.g. mymodel=non-transformer")
    parser.add_argument("--benchmarks", nargs="+", choices=BENCHMARK_NAMES, default=BENCHMARK_NAMES)
    parser.add_argument("--n-test", type=int, default=300, dest="n_test")
    parser.add_argument("--seeds", "--seed", nargs="+", type=int, default=[42], dest="seeds",
                        help="One accuracy run per seed; each seed draws different test questions.")
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--speed-samples", type=int, default=20, dest="speed_samples",
                        help="Questions per benchmark for the speed probe (0 disables it).")
    parser.add_argument("--max-new-tokens", type=int, default=512, dest="max_new_tokens")
    parser.add_argument("--skip-accuracy", action="store_true", dest="skip_accuracy")
    parser.add_argument("--all-pairs", action="store_true", dest="all_pairs",
                        help="Also test same-architecture pairs (default: cross-architecture only).")
    parser.add_argument("--max-error-rate", type=float, default=DEFAULT_MAX_ERROR_RATE,
                        dest="max_error_rate")
    parser.add_argument("--output-dir", type=str, default="compare-results", dest="output_dir")
    parser.add_argument("--force", action="store_true", help="Re-run cells that already exist.")
    args = parser.parse_args()
    args.trained_on = None
    args.seed = args.seeds[0]  # speed probe and run_cell read args.seed

    overrides = {}
    for item in args.arch:
        model, _, group = item.partition("=")
        if group not in ("transformer", "non-transformer"):
            parser.error(f"--arch {item}: group must be 'transformer' or 'non-transformer'")
        overrides[model] = group

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    tasks = []
    if args.speed_samples > 0:
        tasks += [{"kind": "speed", "benchmark": None, "model": m, "status": "pending"}
                  for m in args.models]
    if not args.skip_accuracy:
        tasks += [{"kind": "accuracy", "seed": seed, "benchmark": b, "model": m, "status": "pending"}
                  for seed in args.seeds for b in args.benchmarks for m in args.models]
    status = RunStatus(out / "status.json", tasks, args)
    signal.signal(signal.SIGTERM, stop_on_sigterm)

    try:
        run(args, overrides, out, tasks, status)
    except KeyboardInterrupt:
        status.end("stopped")
        sys.exit(130)
    except BaseException as e:
        status.end("failed", error=f"{e}\n{traceback.format_exc()}")
        raise
    status.end("done")
    print(f"\nReport: {out / 'report.md'}")


def run(args, overrides, out, tasks, status):
    # One event loop for the whole run: litellm caches its HTTP clients per loop, and a loop per
    # cell left them to be closed from the wrong loop ("attached to a different loop" noise).
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        _run(args, overrides, out, tasks, status, loop)
    finally:
        loop.close()


def _run(args, overrides, out, tasks, status, loop):
    infos = {}
    for model in args.models:
        try:
            infos[model] = describe_model(model, overrides)
        except urllib.error.HTTPError:
            raise SystemExit(f"Model '{model}' is not in Ollama. Run: ollama pull {ollama_name(model)}")
        except urllib.error.URLError as e:
            raise SystemExit(f"Cannot reach Ollama at {OLLAMA_URL} ({e.reason}). "
                             "Is `ollama serve` running?")
        i = infos[model]
        print(f"  {model}: {i['architecture']} -> {i['group']} "
              f"({i['parameter_size']}, {i['quantization']}, num_ctx {i['num_ctx'] or 'default'})")
    save_json_atomic(out / "models.json", infos)

    speed, cells = {}, {}
    track_accuracy_progress(status)
    for task in tasks:
        model, label = task["model"], model_label(task["model"])
        if task["kind"] == "speed":
            path = out / "speed" / f"{label}.json"
            cached = path.exists() and not args.force
            status.start(task)
            if cached:
                probe = json.loads(path.read_text())
            else:
                print(f"\n=== speed / {model} ===")
                probe = speed_probe(model, args.benchmarks, args, status)
                save_json_atomic(path, probe)
                unload_all()
            speed[model] = summarize_speed(probe)
            s = speed[model]
            print(f"  decode {fmt(s.get('decode_tok_s'))} tok/s, latency {fmt(s.get('latency_s'), '.2f')} s, "
                  f"memory {fmt(s.get('memory_gb'), '.2f')} GB")
            status.finish(task, "cached" if cached else "done",
                          summary=f"{fmt(s.get('decode_tok_s'))} tok/s, {fmt(s.get('latency_s'), '.2f')} s")
        else:
            benchmark_name, seed = task["benchmark"], task["seed"]
            path = out / f"seed{seed}" / benchmark_name / f"{label}.json"
            cached = path.exists() and not args.force
            status.start(task)
            try:
                if cached:
                    cell = json.loads(path.read_text())
                else:
                    print(f"\n=== seed {seed} / {benchmark_name} / {model} ===")
                    args.seed = seed
                    cell = loop.run_until_complete(run_cell(benchmark_name, model, "baseline", args))
                    save_json_atomic(path, cell)
            except Exception as e:
                print(f"!!! FAILED seed {seed} / {benchmark_name} / {model}: {e}")
                traceback.print_exc()
                status.finish(task, "failed", summary=str(e)[:200])
                continue
            cells.setdefault(benchmark_name, {}).setdefault(model, {})[seed] = cell
            invalid = cell["error_rate"] > args.max_error_rate
            print(f"  -> {cell['main_metric']}: {cell['mean_score']:.4f} (errors {cell['error_rate']:.1%})")
            state = "invalid" if invalid else ("cached" if cached else "done")
            status.finish(task, state, summary=f"{cell['mean_score']:.3f} ({cell['error_rate']:.0%} err)")
        write_outputs(out, infos, cells, speed, args)
    write_outputs(out, infos, cells, speed, args)


if __name__ == "__main__":
    main()
