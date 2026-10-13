"""Read the state of a run_experiment.py run (train + eval per seed) for tui.py. No curses here."""
import datetime
import json
import statistics
import time
from pathlib import Path

from src.naming import model_label

METHODS = ["aflow", "textgrad", "mipro", "bilevel"]
ROUND_METHODS = {"aflow", "bilevel"}


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def since(iso):
    try:
        return time.time() - datetime.datetime.fromisoformat(iso).timestamp()
    except (TypeError, ValueError):
        return None


def driver(base_dir, alive):
    state = read_json(Path(base_dir) / "driver_state.json")
    if state and state.get("state") in ("running", "preflight") and not alive(state.get("pid")):
        state["state"] = "crashed"
    return state


def plan(state):
    args = (state or {}).get("args") or {}
    return {
        "seeds": args.get("seeds", []),
        "models": args.get("models", []),
        "methods": args.get("methods", []),
        "benchmarks": args.get("train_benchmarks", []),
        "rounds": args.get("rounds"),
        "optimiser_model": args.get("optimiser_model"),
    }


def tokens(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e3 else str(n)


def optimiser_tokens(usage, optimiser_model):
    """Tokens the optimiser used in one training run (the executor is local too, so split by model)."""
    if not optimiser_model:
        return 0
    name = optimiser_model.split("/")[-1]
    return sum(u.get("prompt_tokens", 0) + u.get("completion_tokens", 0)
               for model, u in ((usage or {}).get("by_model") or {}).items()
               if model.split("/")[-1] == name)


def tasks(base_dir, state):
    """Every train and eval step of the run, in execution order, with its status."""
    base_dir, p = Path(base_dir), plan(state)
    live = state and state.get("state") in ("running", "preflight")
    current = (state or {}).get("current") or {}
    rows = []
    for seed in p["seeds"]:
        train = read_json(base_dir / f"seed{seed}" / "train" / "run_summary.json") or {}
        for benchmark in p["benchmarks"]:
            for model in p["models"]:
                label = model_label(model)
                for method in p["methods"]:
                    info = train.get(benchmark, {}).get(label, {}).get(method, {})
                    status = {"success": "done", "failed": "failed", "running": "running"}.get(
                        info.get("status"), "pending")
                    if status == "running" and not live:
                        status = "interrupted"
                    row = {"seed": seed, "stage": "train", "benchmark": benchmark, "model": model,
                           "label": label, "item": method, "status": status,
                           "elapsed_s": info.get("elapsed_sec"), "summary": "", "progress": None}
                    if status == "running":
                        row["elapsed_s"] = since(info.get("started_at"))
                    cost = ((info.get("usage") or {}).get("anthropic") or {}).get("cost_usd")
                    used = optimiser_tokens(info.get("usage"), p["optimiser_model"])
                    if used:
                        row["summary"] = f"optimiser {tokens(used)} tok"
                    if cost:
                        row["summary"] += f" API ${cost:.2f}"
                    if status == "failed":
                        row["summary"] = (info.get("error") or "")[:80]
                    if method in ROUND_METHODS and status in ("running", "done", "interrupted") and p["rounds"]:
                        out = base_dir / f"seed{seed}" / "train" / benchmark / label / method
                        done = len([d for d in out.glob("round_*") if d.is_dir()]) if out.exists() else 0
                        row["progress"] = (min(done, p["rounds"]), p["rounds"])
                        if status != "failed" and not row["summary"]:
                            row["summary"] = f"round {done}/{p['rounds']}"
                    rows.append(row)

        evaluation = read_json(base_dir / f"seed{seed}" / "eval" / "eval_summary.json") or {}
        eval_running = live and current.get("seed") == seed and current.get("stage") == "eval"
        marked_running = False
        for benchmark in p["benchmarks"]:
            for model in p["models"]:
                label = model_label(model)
                for artifact in ["baseline"] + [m for m in METHODS if m in p["methods"]]:
                    info = evaluation.get(benchmark, {}).get(label, {}).get(artifact, {})
                    status = {"success": "done", "invalid": "invalid", "failed": "failed",
                              "unavailable": "no artifact"}.get(info.get("status"), "pending")
                    # evaluate.py only records finished cells: the first pending one is the live one.
                    if status == "pending" and eval_running and not marked_running:
                        status, marked_running = "running", True
                    summary = ""
                    if info.get("mean_score") is not None:
                        summary = f"{info['mean_score']:.3f} ({info.get('error_rate', 0):.0%} err)"
                    rows.append({"seed": seed, "stage": "eval", "benchmark": benchmark, "model": model,
                                 "label": label, "item": artifact, "status": status,
                                 "elapsed_s": info.get("elapsed_sec"), "summary": summary, "progress": None})
    return rows


def scores(base_dir, state):
    """{(benchmark, label, artifact): {"scores": [per seed], "invalid": n}} from every seed's eval."""
    out = {}
    for seed in plan(state)["seeds"]:
        evaluation = read_json(Path(base_dir) / f"seed{seed}" / "eval" / "eval_summary.json") or {}
        for benchmark, by_label in evaluation.items():
            for label, by_artifact in by_label.items():
                for artifact, cell in by_artifact.items():
                    entry = out.setdefault((benchmark, label, artifact), {"scores": [], "invalid": 0})
                    if cell.get("status") == "success":
                        entry["scores"].append(cell["mean_score"])
                    elif cell.get("status") == "invalid":
                        entry["invalid"] += 1
    return out


def training(base_dir, state):
    """{(benchmark, label, method): {"elapsed": [...], "cost": total, "optimiser_tokens": total, "failed": n}}."""
    optimiser_model = plan(state)["optimiser_model"]
    out = {}
    for seed in plan(state)["seeds"]:
        train = read_json(Path(base_dir) / f"seed{seed}" / "train" / "run_summary.json") or {}
        for benchmark, by_label in train.items():
            if benchmark.startswith("_"):
                continue
            for label, by_method in by_label.items():
                for method, info in by_method.items():
                    entry = out.setdefault((benchmark, label, method),
                                           {"elapsed": [], "cost": 0.0, "optimiser_tokens": 0, "failed": 0})
                    if info.get("status") == "success":
                        entry["elapsed"].append(info.get("elapsed_sec") or 0)
                    elif info.get("status") == "failed":
                        entry["failed"] += 1
                    cost = ((info.get("usage") or {}).get("anthropic") or {}).get("cost_usd")
                    entry["cost"] += cost or 0.0
                    entry["optimiser_tokens"] += optimiser_tokens(info.get("usage"), optimiser_model)
    return out


def mean_std(values):
    if not values:
        return None, None
    return statistics.mean(values), (statistics.stdev(values) if len(values) > 1 else None)


def final_results(base_dir):
    path = Path(base_dir) / "final_results.json"
    data = read_json(path)
    if data is not None:
        data["_mtime"] = path.stat().st_mtime
    return data
