"""Concurrent-writer-safe updates of the JSON summaries (run_summary.json, eval_summary.json).

main.py and evaluate.py each keep one summary per seed. With run_experiment.py --per-model several
processes work on the same seed at once, one per executor model, and a process that dumps its whole
in-memory copy would erase the cells the others have written. update_json re-reads the file under an
inter-process lock, lets the caller patch only its own cells, and writes it back atomically.
"""
import fcntl
import json
import os


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {} if default is None else default


def update_json(path, mutate):
    """Apply `mutate(data)` to the JSON object stored at `path`, serialised across processes.

    Returns the updated object. The lock file lives next to the JSON file; fcntl.flock is released
    when the file descriptor closes, so a process that dies mid-update cannot leave it held.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = read_json(path)
        if not isinstance(data, dict):
            data = {}
        mutate(data)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, path)
        return data


def set_cell(path, keys, value):
    """Set summary[k1][k2]...[kn] = value, creating the intermediate dicts."""
    def mutate(data):
        node = data
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value
    return update_json(path, mutate)
