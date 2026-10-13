"""Terminal UI: pick models, launch a run, follow it, read the results.

    python tui.py [--output-dir compare-results] [--base-dir runs]

Two modes, switched at the top of Setup:
  * Compare architectures -> compare_models.py (seed workflows, accuracy + speed + memory)
  * Optimise              -> run_experiment.py (train aflow/textgrad/mipro/bilevel, then evaluate)

Runs are separate processes that write their state to disk (status.json / driver_state.json),
so the TUI can be closed and reopened while they keep going.
"""
import argparse
import curses
import json
import os
import signal
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import tui_optimise as opt
from src.architectures import ARCHITECTURES, GROUP_ORDER
from src.naming import DEFAULT_OPTIMISER_MODEL, OPTIMISER_MODELFILE, model_label

HERE = Path(__file__).resolve().parent
OLLAMA_URL = "http://localhost:11434"
BENCHMARKS = sorted(p.name for p in (HERE / "src" / "aflow_workflow").iterdir()
                    if (p / "graph.py").exists())
TABS = ["Setup", "Status", "Results", "Comparison"]
FINISHED = {"done", "cached", "invalid", "failed", "no artifact"}
MODES = {"compare": "Compare architectures (seed workflows)",
         "optimise": "Optimise (train + evaluate: bilevel, aflow, …)"}
INNER_CHOICES = ("mipro+textgrad", "mipro", "textgrad", "none")

# (key, label, default, kind, step for ←/→). kind is int/float/str/bool, or a tuple of choices.
COMPARE_OPTIONS = [
    ("n_test", "Test questions per benchmark", 300, int, 10),
    ("speed_samples", "Speed-probe questions per benchmark (0 = off)", 20, int, 5),
    ("max_new_tokens", "Max new tokens in speed probe", 512, int, 64),
    ("concurrency", "Concurrent requests (accuracy)", 6, int, 1),
    ("compare_seeds", "Seeds (space-separated; each draws other questions)", "42", str, None),
    ("max_error_rate", "Max error rate before a cell is invalid", 0.02, float, 0.01),
    ("output_dir", "Output folder (the other tabs read it too)", "compare-results", str, None),
    ("skip_accuracy", "Skip accuracy (speed/memory only)", False, bool, None),
    ("all_pairs", "Also test same-architecture pairs", False, bool, None),
    ("force", "Re-run cells that already have results", False, bool, None),
]

OPTIMISE_OPTIONS = [
    ("optimiser_model", "Optimiser model (local; anthropic/… = Claude)", DEFAULT_OPTIMISER_MODEL, str, None),
    ("seeds", "Seeds (space-separated)", "42", str, None),
    ("rounds", "AFlow / bilevel rounds (maximum unless fixed)", 20, int, 1),
    ("fixed_rounds", "Run exactly that many rounds (no convergence stop)", False, bool, None),
    ("validation_rounds", "Validation passes per round", 3, int, 1),
    ("skip_internal_test", "Skip the optimisers' own test passes (evaluate.py scores them)", False, bool, None),
    ("n_test", "Test questions per benchmark", 300, int, 10),
    ("inner", "[bilevel] inner optimiser", INNER_CHOICES[0], INNER_CHOICES, None),
    ("inner_mipro_candidates", "[bilevel] MIPRO candidates per inner run", 4, int, 1),
    ("inner_mipro_steps", "[bilevel] MIPRO steps per inner run", 4, int, 1),
    ("inner_tg_steps", "[bilevel] TextGrad steps per inner run", 2, int, 1),
    ("inner_tune_k", "[bilevel] train examples for inner tuning", 80, int, 10),
    ("inner_select_k", "[bilevel] dev examples to accept a candidate", 100, int, 10),
    ("max_error_rate", "Max error rate before a cell is invalid", 0.02, float, 0.01),
    ("base_dir", "Output folder (the other tabs read it too)", "runs", str, None),
    ("smoke", "Smoke test (1 seed, 2 rounds, 20 questions)", False, bool, None),
    ("skip_preflight", "Skip preflight checks", False, bool, None),
    ("stop_on_error", "Stop everything on the first failure", False, bool, None),
]

HELP = [
    ("Anywhere", ""),
    ("q  Esc  Ctrl-C", "quit the TUI (a running comparison keeps going)"),
    ("1 2 3 4  Tab", "switch tab (in Setup, digits on a number option edit it instead)"),
    ("?", "this help"),
    ("Setup", ""),
    ("↑ ↓  (j k)", "move"),
    ("space / enter", "tick a model or benchmark, flip an on/off option, edit a value, press Run"),
    ("0-9 on a number", "start typing a new value"),
    ("← →", "decrease / increase the number under the cursor"),
    ("a", "on a model: force its group (auto → non-transformer → transformer)"),
    ("R", "reload the model list from Ollama"),
    ("r", "run (the comparison or the optimisation, depending on Mode)"),
    ("Mode line", "switch between Compare architectures and Optimise (bilevel, aflow, …)"),
    ("Seeds option", "several seeds, e.g. '42 43 44': each draws other test questions; results show mean ± std"),
    ("While editing", ""),
    ("enter", "save    Esc: cancel    ← → Home End: move    Backspace/Del: erase"),
    ("Status", ""),
    ("s", "stop the running job and its children (finished steps are kept)"),
    ("Results / Comparison", ""),
    ("↑ ↓ PgUp PgDn Home End", "scroll"),
    ("g", "Optimise mode: run aggregate_results.py now (paired tests)"),
]

GREEN, RED, YELLOW, CYAN, MAGENTA, HEADER = range(1, 7)


def group_color(group):
    return curses.color_pair({"non-transformer": CYAN, "transformer": MAGENTA}.get(group, YELLOW))


def status_color(status):
    return curses.color_pair({"done": GREEN, "cached": GREEN, "running": YELLOW, "invalid": RED,
                              "failed": RED, "stopped": RED}.get(status, 0))


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


def fetch_models():
    with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=5) as resp:
        tags = json.loads(resp.read())["models"]
    models = []
    for m in tags:
        caps = m.get("capabilities")
        if caps is not None and "completion" not in caps:
            continue  # embedding models
        arch = m.get("details", {}).get("family", "?")
        name = m["name"][:-len(":latest")] if m["name"].endswith(":latest") else m["name"]
        models.append({
            "name": name,
            "arch": arch,
            "group": ARCHITECTURES.get(arch, ("unknown",))[0],
            "size": m.get("details", {}).get("parameter_size", "?"),
            "quant": m.get("details", {}).get("quantization_level", "?"),
        })
    return sorted(models, key=lambda m: (GROUP_ORDER[m["group"]], m["name"]))


def fmt(value, spec=".1f", missing="–"):
    return missing if value is None else format(value, spec)


def bar(fraction, width):
    fraction = max(0.0, min(1.0, fraction))
    full = int(round(fraction * width))
    return "█" * full + "░" * (width - full)


def duration(seconds):
    if seconds is None:
        return "–"
    seconds = int(seconds)
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"


class App:
    def __init__(self, screen, output_dir, base_dir="runs"):
        self.screen = screen
        self.tab = 0
        self.cursor = 0
        self.scroll = [0] * len(TABS)
        self.message = ""
        self.models, self.model_error = [], None
        self.options = {key: default for key, _, default, _, _ in COMPARE_OPTIONS + OPTIMISE_OPTIONS}
        self.options["output_dir"] = output_dir
        self.options["base_dir"] = base_dir
        self.mode = "compare"
        self.methods = {"bilevel"}
        self.show_help = False
        self.selected_benchmarks = set(BENCHMARKS)
        self.selected_models = set()
        self.arch_override = {}
        self.refresh_models()
        self.load_previous_config()

    @property
    def out(self):
        """Folder of the current mode's run."""
        if self.mode == "compare":
            path = Path(self.options["output_dir"]).expanduser()
        else:
            base = self.options["base_dir"]
            # run_experiment.py redirects the default folder for smoke runs.
            path = Path("runs_smoke" if self.options["smoke"] and base == "runs" else base).expanduser()
        return path if path.is_absolute() else HERE / path

    def mode_options(self):
        return COMPARE_OPTIONS if self.mode == "compare" else OPTIMISE_OPTIONS

    # ---------- data ----------

    def refresh_models(self):
        try:
            self.models, self.model_error = fetch_models(), None
        except OSError as e:
            self.models, self.model_error = [], f"Cannot reach Ollama at {OLLAMA_URL}: {e}"

    def load_previous_config(self):
        names = {m["name"] for m in self.models}
        if self.mode == "compare":
            config = (read_json(self.out / "status.json") or {}).get("config")
            if not config:
                return
            for key in ("n_test", "speed_samples"):
                if key in config:
                    self.options[key] = config[key]
            seeds = config.get("seeds") or ([config["seed"]] if "seed" in config else None)
            if seeds:
                self.options["compare_seeds"] = " ".join(map(str, seeds))
            benchmarks = config.get("benchmarks")
        else:
            config = (read_json(self.out / "driver_state.json") or {}).get("args")
            if not config:
                return
            if config.get("methods"):
                self.methods = set(config["methods"])
            if config.get("seeds"):
                self.options["seeds"] = " ".join(map(str, config["seeds"]))
            for key in ("optimiser_model", "rounds", "fixed_rounds", "validation_rounds", "skip_internal_test",
                        "n_test", "max_error_rate", "inner", "inner_mipro_candidates",
                        "inner_mipro_steps", "inner_tg_steps", "inner_tune_k", "inner_select_k"):
                if config.get(key) is not None:
                    self.options[key] = config[key]
            benchmarks = config.get("train_benchmarks")
        self.selected_models = {m for m in config.get("models", []) if m in names}
        if benchmarks:
            self.selected_benchmarks = set(benchmarks) & set(BENCHMARKS)

    def compare_status(self):
        path = Path(self.options["output_dir"]).expanduser()
        status = read_json((path if path.is_absolute() else HERE / path) / "status.json")
        if status and status.get("state") == "running" and not pid_alive(status.get("pid")):
            status["state"] = "crashed"
        return status

    def optimise_state(self):
        mode, self.mode = self.mode, "optimise"
        try:
            return opt.driver(self.out, pid_alive)
        finally:
            self.mode = mode

    def status(self):
        return self.compare_status() if self.mode == "compare" else self.optimise_state()

    def running(self, mode=None):
        mode = mode or self.mode
        if mode == "compare":
            status = self.compare_status()
            return bool(status and status.get("state") == "running")
        state = self.optimise_state()
        return bool(state and state.get("state") in ("running", "preflight"))

    def group_of(self, model):
        """Architecture group of a model name or label, from the Ollama list and any 'a' override."""
        for m in self.models:
            if model in (m["name"], model_label(m["name"])):
                return self.arch_override.get(m["name"], m["group"])
        return "unknown"

    # ---------- setup items ----------

    def setup_items(self):
        items = [("mode", None)]
        items += [("model", m) for m in self.models]
        items += [("benchmark", b) for b in BENCHMARKS]
        if self.mode == "optimise":
            items += [("method", m) for m in opt.METHODS]
        items += [("option", o) for o in self.mode_options()]
        items.append(("run", None))
        return items

    def switch_mode(self):
        self.mode = "optimise" if self.mode == "compare" else "compare"
        self.load_previous_config()
        self.message = f"Mode: {MODES[self.mode]}. Status, Results and Comparison follow the mode."

    def activate(self, kind, value):
        if kind == "mode":
            self.switch_mode()
        elif kind == "method":
            self.methods ^= {value}
        elif kind == "model":
            self.selected_models ^= {value["name"]}
        elif kind == "benchmark":
            self.selected_benchmarks ^= {value}
        elif kind == "option":
            if value[3] is bool:
                self.options[value[0]] = not self.options[value[0]]
            elif isinstance(value[3], tuple):
                self.step_option(value, 1)
            else:
                self.edit_option(value, str(self.options[value[0]]))
        elif kind == "run":
            self.start_run()

    def edit_option(self, option, initial):
        key, label, _, typ, _ = option
        text = self.prompt(f"{label}: ", initial)
        if text is None:
            return
        try:
            value = typ(text)
        except ValueError:
            self.message = f"'{text}' is not a valid {typ.__name__}; kept {self.options[key]}."
            return
        if typ in (int, float) and value < 0:
            self.message = "Negative values are not allowed."
            return
        if typ is str and not value:
            return
        if key in ("seeds", "compare_seeds") and not all(part.isdigit() for part in value.split()):
            self.message = "Seeds must be whole numbers separated by spaces, e.g. '42 43 44'."
            return
        self.options[key] = value
        if key in ("output_dir", "base_dir"):
            self.load_previous_config()
            self.message = f"Results, Status and Comparison now read {self.out}"
        elif self.running():
            self.message = "Saved. It applies to the next run, not the one in progress."

    def step_option(self, option, direction):
        key, _, _, typ, step = option
        if isinstance(typ, tuple):
            self.options[key] = typ[(typ.index(self.options[key]) + direction) % len(typ)]
        elif typ in (int, float):
            value = max(0, self.options[key] + direction * step)
            self.options[key] = round(value, 4) if typ is float else value

    def cycle_arch(self, model):
        order = [None, "non-transformer", "transformer"]
        current = self.arch_override.get(model["name"])
        nxt = order[(order.index(current) + 1) % len(order)]
        if nxt is None:
            self.arch_override.pop(model["name"], None)
        else:
            self.arch_override[model["name"]] = nxt

    def start_run(self):
        for mode in ("compare", "optimise"):
            if self.running(mode):
                self.message = (f"A {mode} run is already in progress; both use Ollama, so wait for it "
                                "or stop it (Status tab, 's').")
                return
        models = [m["name"] for m in self.models if m["name"] in self.selected_models]
        benchmarks = [b for b in BENCHMARKS if b in self.selected_benchmarks]
        if not models or not benchmarks:
            self.message = "Select at least one model and one benchmark."
            return
        if self.mode == "compare":
            cmd = self.compare_command(models, benchmarks)
        else:
            if not self.methods:
                self.message = "Select at least one method to train."
                return
            cmd = self.optimise_command(models, benchmarks)
        self.launch(cmd, f"{len(models)} models × {len(benchmarks)} benchmarks")

    def compare_command(self, models, benchmarks):
        o = self.options
        cmd = [sys.executable, str(HERE / "compare_models.py"),
               "--models", *models, "--benchmarks", *benchmarks,
               "--n-test", str(o["n_test"]), "--seeds", *o["compare_seeds"].split(),
               "--speed-samples", str(o["speed_samples"]),
               "--max-new-tokens", str(o["max_new_tokens"]),
               "--concurrency", str(o["concurrency"]), "--max-error-rate", str(o["max_error_rate"]),
               "--output-dir", str(self.out)]
        for flag in ("skip_accuracy", "all_pairs", "force"):
            if o[flag]:
                cmd.append("--" + flag.replace("_", "-"))
        overrides = [f"{m}={g}" for m, g in self.arch_override.items() if m in models]
        if overrides:
            cmd += ["--arch", *overrides]
        return cmd

    def optimise_command(self, models, benchmarks):
        o = self.options
        cmd = [sys.executable, str(HERE / "run_experiment.py"),
               "--models", *models, "--train-benchmarks", *benchmarks,
               "--methods", *[m for m in opt.METHODS if m in self.methods],
               "--seeds", *o["seeds"].split(), "--rounds", str(o["rounds"]),
               "--validation_rounds", str(o["validation_rounds"]), "--n-test", str(o["n_test"]),
               "--max-error-rate", str(o["max_error_rate"]), "--base-dir", str(self.out),
               "--optimiser-model", o["optimiser_model"]]
        if "bilevel" in self.methods:
            cmd += ["--inner", o["inner"]]
            if not o["smoke"]:  # smoke uses its own tiny inner budget
                for key in ("mipro_candidates", "mipro_steps", "tg_steps", "tune_k", "select_k"):
                    cmd += [f"--inner-{key.replace('_', '-')}", str(o["inner_" + key])]
        for flag in ("smoke", "skip_preflight", "stop_on_error", "fixed_rounds", "skip_internal_test"):
            if o[flag]:
                cmd.append("--" + flag.replace("_", "-"))
        return cmd

    def launch(self, cmd, what):
        self.out.mkdir(parents=True, exist_ok=True)
        log = open(self.out / "run.log", "a")
        log.write(f"\n$ {' '.join(cmd)}\n")
        log.flush()
        # Own session = own process group, so 's' can stop the run and its children together.
        proc = subprocess.Popen(cmd, cwd=HERE, stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        # Wait until the new run owns its state file, or the process dies during startup.
        self.tab = 1
        for _ in range(300):
            status = self.status()
            if status and status.get("pid") == proc.pid:
                self.message = f"Started: {what}. Log: {self.out / 'run.log'}"
                return
            if proc.poll() is not None:
                self.message = f"The run exited during startup (code {proc.returncode}); see the log below."
                return
            time.sleep(0.1)
        self.message = "The run is still starting; Status will update when it is ready."

    def stop_run(self):
        status = self.status()
        if not self.running():
            self.message = "No run in progress."
            return
        if (self.prompt("Stop the running job? [y/N] ") or "").lower() != "y":
            return
        pid = status["pid"]
        try:
            # Runs started from the TUI lead their own process group (children included);
            # a run started from a shell does not, and killing its group would hit the shell.
            if os.getpgid(pid) == pid:
                os.killpg(pid, signal.SIGTERM)
            else:
                os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        self.message = "Stop signal sent. Finished cells are kept; running again resumes."

    # ---------- drawing ----------

    def put(self, y, x, text, attr=0):
        h, w = self.screen.getmaxyx()
        if 0 <= y < h and x < w - 1:
            try:
                self.screen.addnstr(y, x, text, w - 1 - x, attr)
            except curses.error:
                pass

    def put_line(self, y, segments):
        x = 0
        for text, attr in segments:
            self.put(y, x, text, attr)
            x += len(text)

    def prompt(self, text, initial=""):
        """One-line editor on the bottom row. Returns the text, or None if Esc was pressed."""
        buffer, pos = list(initial), len(initial)
        curses.curs_set(1)
        self.screen.timeout(-1)
        try:
            while True:
                h, w = self.screen.getmaxyx()
                self.screen.move(h - 1, 0)
                self.screen.clrtoeol()
                self.put(h - 1, 0, text, curses.A_BOLD)
                start = min(len(text), w - 2)
                self.put(h - 1, start, "".join(buffer), curses.color_pair(CYAN))
                self.put(h - 2, 0, " " * (w - 1))
                self.put(h - 2, 0, "enter save · Esc cancel", curses.A_DIM)
                self.screen.move(h - 1, min(start + pos, w - 2))
                key = self.screen.get_wch()
                if key in ("\n", "\r", curses.KEY_ENTER):
                    return "".join(buffer).strip()
                if key == "\x1b":
                    return None
                if key in (curses.KEY_BACKSPACE, "\x7f", "\b"):
                    if pos:
                        del buffer[pos - 1]
                        pos -= 1
                elif key == curses.KEY_DC:
                    if pos < len(buffer):
                        del buffer[pos]
                elif key == curses.KEY_LEFT:
                    pos = max(0, pos - 1)
                elif key == curses.KEY_RIGHT:
                    pos = min(len(buffer), pos + 1)
                elif key == curses.KEY_HOME:
                    pos = 0
                elif key == curses.KEY_END:
                    pos = len(buffer)
                elif key == "\x15":  # Ctrl-U clears the line
                    buffer, pos = [], 0
                elif isinstance(key, str) and key.isprintable():
                    buffer.insert(pos, key)
                    pos += 1
        finally:
            curses.curs_set(0)
            self.screen.timeout(1000)

    def draw_header(self):
        _, w = self.screen.getmaxyx()
        self.put(0, 0, " " * (w - 1), curses.color_pair(HEADER))
        x = 1
        for i, name in enumerate(TABS):
            label = f" {i + 1} {name} "
            attr = curses.color_pair(HEADER) | (curses.A_REVERSE | curses.A_BOLD if i == self.tab else 0)
            self.put(0, x, label, attr)
            x += len(label) + 1
        status = self.status()
        text = f" {'compare' if self.mode == 'compare' else 'optimise'} "
        if status:
            tasks = status.get("tasks", []) if self.mode == "compare" else opt.tasks(self.out, status)
            done = sum(t["status"] in FINISHED for t in tasks)
            text += f"· {status['state']} {done}/{len(tasks)} "
        self.put(0, max(x + 2, w - len(text) - 2), text, curses.color_pair(HEADER) | curses.A_BOLD)

    def draw_footer(self):
        h, _ = self.screen.getmaxyx()
        keys = {
            0: "space/enter select·edit  ←→ change value  r run  a group  R reload",
            1: "s stop run  ↑↓ scroll",
            2: "↑↓ PgUp PgDn scroll" + ("  g aggregate" if self.mode == "optimise" else ""),
            3: "↑↓ PgUp PgDn scroll" + ("  g aggregate" if self.mode == "optimise" else ""),
        }[self.tab]
        self.put(h - 2, 0, self.message, curses.color_pair(YELLOW))
        self.put(h - 1, 0, f"q quit  ? help  Tab/1-4 tabs  {keys}", curses.A_DIM)

    def draw_help(self):
        lines = [[("Keys", curses.A_BOLD | curses.A_UNDERLINE), ("   any key closes this help", curses.A_DIM)]]
        for keys, text in HELP:
            if not text:
                lines += [[], [(keys, curses.A_BOLD)]]
            else:
                lines.append([(f"  {keys:<24}", curses.color_pair(CYAN)), (text, 0)])
        lines += [[], [(f"Output folder: {self.out}", curses.A_DIM)],
                  [("Runs are separate processes: quitting never stops them. Reopen tui.py to follow one.",
                    curses.A_DIM)]]
        for row, segments in enumerate(lines):
            self.put_line(2 + row, segments)

    def draw_scrolled(self, lines):
        h, _ = self.screen.getmaxyx()
        view = h - 4
        top = self.scroll[self.tab] = max(0, min(self.scroll[self.tab], max(0, len(lines) - view)))
        for row, segments in enumerate(lines[top:top + view]):
            self.put_line(2 + row, segments)
        if len(lines) > view:
            self.put(1, 0, f"lines {top + 1}-{min(len(lines), top + view)} of {len(lines)}", curses.A_DIM)

    def draw_setup(self):
        h, _ = self.screen.getmaxyx()
        items = self.setup_items()
        self.cursor = max(0, min(self.cursor, len(items) - 1))
        lines, cursor_line = [], 0
        bold = curses.A_BOLD
        last_kind = None
        for index, (kind, value) in enumerate(items):
            if kind != last_kind:
                title = {"mode": "", "model": "Models (from Ollama)", "benchmark": "Benchmarks",
                         "method": "Methods to train (baseline is always evaluated)",
                         "option": "Options", "run": ""}[kind]
                if last_kind:
                    lines.append([])
                if title:
                    lines.append([(title, bold | curses.A_UNDERLINE)])
                if kind == "model" and self.model_error:
                    lines.append([("  " + self.model_error, curses.color_pair(RED))])
                last_kind = kind
            here = index == self.cursor
            pointer = ("▶ " if here else "  ", curses.color_pair(YELLOW) | bold)
            if here:
                cursor_line = len(lines)
            if kind == "mode":
                lines.append([pointer, ("Mode: ", bold), (MODES[self.mode], curses.color_pair(GREEN) | bold),
                              ("   space/enter to switch" if here else "", curses.A_DIM)])
            elif kind == "method":
                check = "[x]" if value in self.methods else "[ ]"
                lines.append([pointer, (f"{check} {value}", bold if here else 0)])
            elif kind == "model":
                group = self.arch_override.get(value["name"], value["group"])
                forced = "*" if value["name"] in self.arch_override else " "
                check = "[x]" if value["name"] in self.selected_models else "[ ]"
                lines.append([pointer, (f"{check} {value['name']:<34}", bold if here else 0),
                              (f"{value['size']:>8}  {value['quant']:<8} {value['arch']:<14}", 0),
                              (f"{group}{forced}", group_color(group))])
            elif kind == "benchmark":
                check = "[x]" if value in self.selected_benchmarks else "[ ]"
                lines.append([pointer, (f"{check} {value}", bold if here else 0)])
            elif kind == "option":
                key, label, _, typ, _ = value
                shown = ("[x]" if self.options[key] else "[ ]") if typ is bool else str(self.options[key])
                if isinstance(typ, tuple):
                    hint = f"  ← → ({' / '.join(typ)})" if here else ""
                else:
                    hint = {int: "  ← →", float: "  ← →", str: "  enter to edit"}.get(typ, "") if here else ""
                lines.append([pointer, (f"{label:<48} ", bold if here else 0), (shown, curses.color_pair(CYAN)),
                              (hint, curses.A_DIM)])
            else:
                lines.append([pointer, ("[ Run comparison ]" if self.mode == "compare" else "[ Run optimisation ]", curses.color_pair(GREEN) | bold |
                                        (curses.A_REVERSE if here else 0))])
        n_models, n_bench = len(self.selected_models), len(self.selected_benchmarks)
        lines.append([])
        if self.mode == "compare":
            n_seeds = len(self.options["compare_seeds"].split())
            lines.append([(f"{n_seeds} seeds × {n_models} models × {n_bench} benchmarks = "
                           f"{n_seeds * n_models * n_bench} accuracy cells"
                           f" + {n_models if self.options['speed_samples'] else 0} speed probes.  "
                           "* = group set by hand (a).", curses.A_DIM)])
        else:
            n_seeds = 1 if self.options["smoke"] else len(self.options["seeds"].split())
            n_train = n_seeds * n_models * n_bench * len(self.methods)
            lines.append([(f"{n_seeds} seeds × {n_models} models × {n_bench} benchmarks × {len(self.methods)} "
                           f"methods = {n_train} training runs, each followed by evaluation.", curses.A_DIM)])
            optimiser = self.options["optimiser_model"]
            if optimiser.startswith("anthropic/") or "claude" in optimiser:
                lines.append([(f"Optimiser {optimiser} is Claude: needs ANTHROPIC_API_KEY in .env and costs money.",
                               curses.color_pair(YELLOW))])
            elif optimiser in {m["name"] for m in self.models}:
                lines.append([(f"Optimiser {optimiser} runs locally in Ollama.", curses.color_pair(GREEN))])
            else:
                lines.append([(f"Optimiser {optimiser} is not in Ollama yet. The default is built with: "
                               f"ollama pull deepseek-coder-v2:16b && ollama create {DEFAULT_OPTIMISER_MODEL} "
                               f"-f {OPTIMISER_MODELFILE}", curses.color_pair(RED))])
            lines.append([(f"Results go to {self.out}", curses.A_DIM)])
        view = h - 4
        top = self.scroll[0]
        if cursor_line < top:
            top = cursor_line
        elif cursor_line >= top + view:
            top = cursor_line - view + 1
        self.scroll[0] = top
        for row, segments in enumerate(lines[top:top + view]):
            self.put_line(2 + row, segments)

    def draw_status(self):
        (self.draw_status_compare if self.mode == "compare" else self.draw_status_optimise)()

    def draw_results(self):
        (self.draw_results_compare if self.mode == "compare" else self.draw_results_optimise)()

    def draw_comparison(self):
        (self.draw_comparison_compare if self.mode == "compare" else self.draw_comparison_optimise)()

    def log_tail(self, n=15):
        try:
            return (self.out / "run.log").read_text(errors="ignore").splitlines()[-n:]
        except OSError:
            return []

    # ---------- optimise mode ----------

    def draw_status_optimise(self):
        state = self.status()
        if not state:
            lines = [[("No optimise run yet in this folder. Pick models and methods in Setup and start one.",
                       curses.A_DIM)]]
            self.draw_scrolled(lines + [[(line, curses.A_DIM)] for line in self.log_tail()])
            return
        _, w = self.screen.getmaxyx()
        bold = curses.A_BOLD
        tasks = opt.tasks(self.out, state)
        finished = [t for t in tasks if t["status"] in FINISHED]
        run_state = state.get("state") or "?"
        started = state.get("launched_at") or state.get("started_at")
        end = opt.since(state["ended_at"]) if state.get("ended_at") else 0
        elapsed = (opt.since(started) or 0) - (end or 0)
        lines = [[("State: ", bold), (run_state, status_color({"crashed": "failed", "preflight": "running"}.get(
                  run_state, run_state)) | bold),
                  (f"   pid {state.get('pid')}   started {started}   elapsed {duration(elapsed)}", 0)]]
        bar_width = max(10, min(50, w - 40))
        lines.append([("Overall  ", bold), (bar(len(finished) / len(tasks) if tasks else 0, bar_width),
                                            curses.color_pair(GREEN)),
                      (f" {len(finished)}/{len(tasks)} steps", 0)])
        for t in tasks:
            if t["status"] != "running":
                continue
            where = f"seed {t['seed']} {t['stage']} / {t['benchmark']} / {t['model']} / {t['item']}"
            if t["progress"]:
                done, total = t["progress"]
                spent = t["elapsed_s"] or 0
                eta = spent / done * (total - done) if done else None
                lines.append([("Current  ", bold), (bar(done / total, bar_width), curses.color_pair(YELLOW)),
                              (f" round {done}/{total}  ETA {duration(eta)}  {where}", 0)])
            else:
                lines.append([("Current  ", bold), (f"{where}  ({duration(t['elapsed_s'])})",
                                                    curses.color_pair(YELLOW))])
        if run_state == "preflight":
            lines.append([("Running preflight checks (Ollama models, optimiser, datasets)…", curses.color_pair(YELLOW))])
        if run_state == "crashed":
            lines.append([("The process is gone without finishing; see the log below. Re-run to resume "
                           "(finished steps are skipped).", curses.color_pair(RED))])
        lines.append([])
        lines.append([(f"{'seed':<6}{'stage':<7}{'benchmark':<11}{'model':<26}{'method':<10}{'status':<13}"
                       f"{'time':>8}  result", bold)])
        for t in tasks:
            elapsed_s = t["elapsed_s"]
            lines.append([(f"{t['seed']:<6}{t['stage']:<7}{t['benchmark']:<11}{t['model'][:25]:<26}"
                           f"{t['item']:<10}", 0),
                          (f"{t['status']:<13}", status_color(t["status"]) if t["status"] != "no artifact"
                           else curses.A_DIM),
                          (f"{duration(elapsed_s) if elapsed_s is not None else '':>8}  {t['summary']}", 0)])
        lines += [[], [("Log (tail of run.log)", bold | curses.A_UNDERLINE)]]
        lines += [[(line, curses.A_DIM)] for line in self.log_tail()]
        self.draw_scrolled(lines)

    def optimise_models(self, state):
        models = opt.plan(state)["models"]
        return sorted(models, key=lambda m: (GROUP_ORDER.get(self.group_of(m), 3), m))

    def draw_results_optimise(self):
        state = self.status()
        if not state:
            self.draw_scrolled([[("No optimise run yet in this folder.", curses.A_DIM)]])
            return
        bold = curses.A_BOLD
        p = opt.plan(state)
        scores, training = opt.scores(self.out, state), opt.training(self.out, state)
        artifacts = ["baseline"] + [m for m in opt.METHODS if m in p["methods"]]
        models = self.optimise_models(state)
        width = max([len(m) for m in models] + [5]) + 2
        lines = [[("Test accuracy", bold | curses.A_UNDERLINE),
                  ("  mean over finished seeds (± std when >1); best method per model in green", curses.A_DIM)]]
        lines.append([(f"{'model':<{width}}{'group':<17}{'method':<10}", bold)] +
                     [(f"{b:<22}", bold) for b in p["benchmarks"]])
        for model in models:
            label, group = model_label(model), self.group_of(model)
            best = {}
            for b in p["benchmarks"]:
                means = {a: opt.mean_std(scores.get((b, label, a), {}).get("scores"))[0] for a in artifacts}
                means = {a: v for a, v in means.items() if v is not None}
                best[b] = max(means, key=means.get) if len(means) > 1 else None
            for artifact in artifacts:
                row = [(f"{model if artifact == 'baseline' else '':<{width}}", 0),
                       (f"{group if artifact == 'baseline' else '':<17}", group_color(group)),
                       (f"{artifact:<10}", bold if artifact == "bilevel" else 0)]
                for b in p["benchmarks"]:
                    entry = scores.get((b, label, artifact), {})
                    mean, std = opt.mean_std(entry.get("scores"))
                    if mean is None:
                        text = f"INVALID ×{entry['invalid']}" if entry.get("invalid") else "–"
                        row.append((f"{text:<22}", curses.color_pair(RED) if entry.get("invalid") else curses.A_DIM))
                        continue
                    text = f"{mean:.3f}" + (f" ±{std:.3f}" if std is not None else "")
                    text += f"  (n={len(entry['scores'])})"
                    row.append((f"{text:<22}", curses.color_pair(GREEN) | bold if best[b] == artifact else 0))
                lines.append(row)
            lines.append([])

        lines.append([("Training", bold | curses.A_UNDERLINE),
                      ("  mean time per run · optimiser tokens (and API cost, if any) summed over seeds",
                       curses.A_DIM)])
        lines.append([(f"{'model':<{width}}{'method':<10}", bold)] + [(f"{b:<22}", bold) for b in p["benchmarks"]])
        total_cost, total_tokens = 0.0, 0
        for model in models:
            label = model_label(model)
            for method in [m for m in opt.METHODS if m in p["methods"]]:
                row = [(f"{model:<{width}}{method:<10}", 0)]
                for b in p["benchmarks"]:
                    entry = training.get((b, label, method))
                    if not entry:
                        row.append((f"{'–':<22}", curses.A_DIM))
                        continue
                    total_cost += entry["cost"]
                    total_tokens += entry["optimiser_tokens"]
                    mean_time = opt.mean_std(entry["elapsed"])[0]
                    text = f"{duration(mean_time)}  {opt.tokens(entry['optimiser_tokens'])} tok"
                    if entry["cost"]:
                        text += f"  ${entry['cost']:.2f}"
                    if entry["failed"]:
                        text += f"  {entry['failed']} failed"
                    row.append((f"{text:<22}", curses.color_pair(RED) if entry["failed"] else 0))
                lines.append(row)
        optimiser = p.get("optimiser_model") or "?"
        summary = f"Optimiser {optimiser}: {opt.tokens(total_tokens)} tokens so far"
        if total_cost:
            summary += f", API cost ${total_cost:.2f}"
        lines += [[], [(summary, bold)]]
        self.draw_scrolled(lines)

    def draw_comparison_optimise(self):
        state = self.status()
        if not state:
            self.draw_scrolled([[("No optimise run yet in this folder.", curses.A_DIM)]])
            return
        bold = curses.A_BOLD
        p = opt.plan(state)
        scores = opt.scores(self.out, state)
        methods = [m for m in opt.METHODS if m in p["methods"]]
        models = self.optimise_models(state)
        width = max([len(m) for m in models] + [5]) + 2

        def mean_of(b, label, artifact):
            return opt.mean_std(scores.get((b, label, artifact), {}).get("scores"))[0]

        lines = [[("Gain over baseline", bold | curses.A_UNDERLINE),
                  ("  method − baseline on the same test set, mean over seeds", curses.A_DIM)]]
        lines.append([(f"{'model':<{width}}{'group':<17}{'method':<10}", bold)] +
                     [(f"{b:<12}", bold) for b in p["benchmarks"]])
        gains = {}  # (method, benchmark, group) -> [gain per model]
        for model in models:
            label, group = model_label(model), self.group_of(model)
            for method in methods:
                row = [(f"{model:<{width}}", 0), (f"{group:<17}", group_color(group)), (f"{method:<10}", 0)]
                for b in p["benchmarks"]:
                    base, score = mean_of(b, label, "baseline"), mean_of(b, label, method)
                    if base is None or score is None:
                        row.append((f"{'–':<12}", curses.A_DIM))
                        continue
                    gain = score - base
                    gains.setdefault((method, b, group), []).append(gain)
                    color = curses.color_pair(GREEN) if gain > 0 else curses.color_pair(RED) if gain < 0 else 0
                    row.append((f"{gain:+.3f}".ljust(12), color))
                lines.append(row)

        groups = ["non-transformer", "transformer"]
        lines += [[], [("Does optimisation help one architecture more?", bold | curses.A_UNDERLINE),
                       ("  mean gain per group; NT − T > 0 means non-transformers gain more", curses.A_DIM)]]
        lines.append([(f"{'method':<10}{'benchmark':<11}", bold), (f"{'non-transformer':>17}", group_color(groups[0]) | bold),
                      (f"{'transformer':>14}", group_color(groups[1]) | bold), (f"{'NT − T':>10}", bold)])
        for method in methods:
            for b in p["benchmarks"]:
                nt = gains.get((method, b, groups[0]))
                t = gains.get((method, b, groups[1]))
                nt_mean = sum(nt) / len(nt) if nt else None
                t_mean = sum(t) / len(t) if t else None
                delta = nt_mean - t_mean if nt_mean is not None and t_mean is not None else None
                lines.append([(f"{method:<10}{b:<11}", 0),
                              (f"{fmt(nt_mean, '+.3f'):>17}", 0), (f"{fmt(t_mean, '+.3f'):>14}", 0),
                              (f"{fmt(delta, '+.3f'):>10}", bold)])

        lines += [[], [("Paired tests (aggregate_results.py)", bold | curses.A_UNDERLINE),
                       ("  per seed; diff = method − reference; * = Holm p<0.05", curses.A_DIM)]]
        final = opt.final_results(self.out)
        if not final:
            lines.append([("Not aggregated yet. It runs automatically at the end; press g to run it now.",
                           curses.color_pair(YELLOW))])
        else:
            newest = max((f.stat().st_mtime for f in self.out.glob("seed*/eval/eval_summary.json")), default=0)
            stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(final["_mtime"]))
            stale = "  — older than the latest eval results, press g to refresh" if newest > final["_mtime"] else ""
            lines.append([(f"Aggregated {stamp}{stale}", curses.color_pair(YELLOW) if stale else curses.A_DIM)])
            for c in final.get("paired_comparisons", []):
                lo, hi = c.get("diff_ci") or (None, None)
                significant = c.get("p_holm", 1) < 0.05
                verdict = ("no significant difference" if not significant else
                           f"{c['method'] if c['diff'] > 0 else c['reference']} better")
                group = self.group_of(c["model"])
                lines.append([(f"  seed {c['seed']} {c['benchmark']:<9}", 0), (f"{c['model']:<{width}}", group_color(group)),
                              (f"{c['method']:>8} vs {c['reference']:<9}"
                               f"{c['diff']:+.3f} [{fmt(lo, '+.3f')},{fmt(hi, '+.3f')}]  "
                               f"p={c.get('p_holm', 1):.4f}{'*' if significant else ' '}  ", 0),
                              (verdict, bold if significant else curses.A_DIM)])
        self.draw_scrolled(lines)

    @staticmethod
    def seed_agreement(c):
        n = len(c.get("per_seed_diff") or {})
        if n < 2:
            return []
        a, b = c["seeds_a_ahead"], c["seeds_b_ahead"]
        consistent = a == n or b == n
        return [(f"  A ahead in {a}/{n} seeds, B in {b}/{n}",
                 curses.color_pair(GREEN) if consistent else curses.color_pair(YELLOW))]

    def aggregate(self):
        if self.mode != "optimise":
            return
        result = subprocess.run([sys.executable, str(HERE / "aggregate_results.py"), "--base-dir", str(self.out)],
                                cwd=HERE, capture_output=True, text=True)
        output = (result.stdout + result.stderr).strip().splitlines()
        self.message = ("Aggregated. " if result.returncode == 0 else "Aggregation failed: ") + (output[-1] if output else "")

    # ---------- compare mode ----------

    def draw_status_compare(self):
        status = self.status()
        if not status:
            lines = [[("No run yet. Pick models in Setup and start one.", curses.A_DIM)]]
            try:
                tail = (self.out / "run.log").read_text(errors="ignore").splitlines()[-15:]
            except OSError:
                tail = []
            self.draw_scrolled(lines + [[(line, curses.A_DIM)] for line in tail])
            return
        _, w = self.screen.getmaxyx()
        bold = curses.A_BOLD
        tasks = status.get("tasks", [])
        finished = [t for t in tasks if t["status"] in FINISHED]
        state = status["state"]
        now = time.time()
        started = time.mktime(time.strptime(status["started_at"], "%Y-%m-%dT%H:%M:%S"))
        end = status.get("updated_at", now) if state != "running" else now
        lines = [[("State: ", bold), (state, status_color(state if state != "crashed" else "failed") | bold),
                  (f"   pid {status.get('pid')}   started {status['started_at']}   "
                   f"elapsed {duration(end - started)}", 0)]]
        bar_width = max(10, min(50, w - 40))
        fraction = len(finished) / len(tasks) if tasks else 0
        lines.append([("Overall  ", bold), (bar(fraction, bar_width), curses.color_pair(GREEN)),
                      (f" {len(finished)}/{len(tasks)} tasks", 0)])
        current = status.get("current")
        if current:
            where = f"{current['kind']} / {current.get('benchmark') or 'all'} / {current['model']}"
            progress = status.get("progress") or {}
            if progress.get("total"):
                done, total = progress["done"], progress["total"]
                spent = now - current.get("started", now)
                eta = spent / done * (total - done) if done else None
                lines.append([("Current  ", bold), (bar(done / total, bar_width), curses.color_pair(YELLOW)),
                              (f" {done}/{total}  ETA {duration(eta)}  {where}", 0)])
            else:
                lines.append([("Current  ", bold), (f"{where} (starting…)", curses.color_pair(YELLOW))])
        if state == "crashed":
            lines.append([("The process is gone without finishing; see the log below. "
                           "Re-run to resume.", curses.color_pair(RED))])
        if status.get("error"):
            for line in status["error"].splitlines()[:6]:
                lines.append([(line, curses.color_pair(RED))])
        lines.append([])
        lines.append([(f"{'task':<9}{'seed':<6}{'benchmark':<11}{'model':<30}{'status':<10}{'time':>8}  result", bold)])
        for t in tasks:
            elapsed = t.get("elapsed_s")
            if t["status"] == "running":
                elapsed = now - t.get("started", now)
            lines.append([(f"{t['kind']:<9}{str(t.get('seed') or '–'):<6}{(t.get('benchmark') or '–'):<11}"
                           f"{t['model'][:29]:<30}", 0),
                          (f"{t['status']:<10}", status_color(t["status"])),
                          (f"{duration(elapsed) if elapsed is not None else '':>8}  {t.get('summary', '')}", 0)])
        lines.append([])
        lines.append([("Log (tail of run.log)", bold | curses.A_UNDERLINE)])
        try:
            tail = (self.out / "run.log").read_text(errors="ignore").splitlines()[-15:]
        except OSError:
            tail = []
        lines += [[(line, curses.A_DIM)] for line in tail]
        self.draw_scrolled(lines)

    def ordered_models(self, data):
        infos = data.get("models", {})
        return sorted(infos, key=lambda m: (GROUP_ORDER.get(infos[m]["group"], 3), m))

    def draw_results_compare(self):
        data = read_json(self.out / "comparison.json")
        if not data:
            self.draw_scrolled([[("No results yet.", curses.A_DIM)]])
            return
        bold = curses.A_BOLD
        infos, accuracy, speed = data["models"], data.get("accuracy", {}), data.get("speed", {})
        models = self.ordered_models(data)
        benchmarks = [b for b in BENCHMARKS if b in accuracy]
        width = max([len(m) for m in models] + [5]) + 2
        lines = [[("Accuracy", bold | curses.A_UNDERLINE), ("  one seed: score [95% CI] · several: mean ± std across seeds; best per benchmark in green",
                                                  curses.A_DIM)]]
        lines.append([(f"{'model':<{width}}{'group':<17}", bold)] +
                     [(f"{b:<26}", bold) for b in benchmarks])
        best = {}
        for b in benchmarks:
            valid = {m: c["mean_score"] for m, c in accuracy[b].items() if c["status"] == "success"}
            best[b] = max(valid, key=valid.get) if valid else None
        for m in models:
            group = infos[m]["group"]
            row = [(f"{m:<{width}}", 0), (f"{group:<17}", group_color(group))]
            for b in benchmarks:
                cell = accuracy[b].get(m)
                if not cell:
                    row.append((f"{'–':<26}", curses.A_DIM))
                elif cell["status"] == "invalid":
                    row.append((f"{'INVALID ' + format(cell['error_rate'], '.0%') + ' err':<26}", curses.color_pair(RED)))
                else:
                    lo, hi = cell["ci"]
                    if cell.get("seed_std") is not None:
                        text = f"{cell['mean_score']:.3f} ±{cell['seed_std']:.3f} ({len(cell['valid_seeds'])} seeds)"
                    else:
                        text = f"{cell['mean_score']:.3f} [{fmt(lo, '.3f')},{fmt(hi, '.3f')}]"
                    if cell.get("invalid_seeds"):
                        text += " !"
                    attr = curses.color_pair(GREEN) | bold if best[b] == m else 0
                    row.append((f"{text:<26}", attr))
            lines.append(row)

        seeds = sorted({seed for b in benchmarks for c in accuracy[b].values() for seed in c.get("per_seed", {})},
                       key=int)
        if len(seeds) > 1:
            lines += [[], [("Per seed", bold | curses.A_UNDERLINE),
                           (f"  seeds {' / '.join(seeds)}; each seed is a different set of questions; "
                            "x = invalid (too many errors)", curses.A_DIM)]]
            lines.append([(f"{'model':<{width}}{'group':<17}", bold)] + [(f"{b:<26}", bold) for b in benchmarks])
            for m in models:
                group = infos[m]["group"]
                row = [(f"{m:<{width}}", 0), (f"{group:<17}", group_color(group))]
                for b in benchmarks:
                    per_seed = (accuracy[b].get(m) or {}).get("per_seed", {})
                    parts = []
                    for seed in seeds:
                        cell = per_seed.get(seed)
                        parts.append("–" if not cell else "x" if cell["status"] == "invalid"
                                     else f"{cell['mean_score']:.2f}")
                    row.append((f"{' / '.join(parts):<26}", 0))
                lines.append(row)
        if any(c.get("invalid_seeds") for b in benchmarks for c in accuracy[b].values()):
            lines += [[], [("! = some seeds were invalid and are left out of the mean", curses.color_pair(YELLOW))]]

        if speed:
            lines += [[], [("Speed", bold | curses.A_UNDERLINE),
                           ("  medians, sequential; tokenisers differ, so compare latency and chars/s", curses.A_DIM)]]
            lines.append([(f"{'model':<{width}}{'group':<17}{'latency s':>10}{'p90 s':>8}{'decode t/s':>11}"
                           f"{'prefill t/s':>12}{'chars/s':>9}{'out tok':>9}{'load s':>8}", bold)])
            fastest = min((s["latency_s"], m) for m, s in speed.items() if s.get("latency_s"))[1] \
                if any(s.get("latency_s") for s in speed.values()) else None
            for m in models:
                s = speed.get(m)
                if not s:
                    continue
                group = infos[m]["group"]
                lines.append([(f"{m:<{width}}", 0), (f"{group:<17}", group_color(group)),
                              (f"{fmt(s['latency_s'], '.2f'):>10}",
                               curses.color_pair(GREEN) | bold if m == fastest else 0),
                              (f"{fmt(s['latency_p90_s'], '.2f'):>8}{fmt(s['decode_tok_s']):>11}"
                               f"{fmt(s['prefill_tok_s']):>12}{fmt(s['output_chars_s']):>9}"
                               f"{fmt(s['output_tokens'], '.0f'):>9}{fmt(s['cold_load_s'], '.2f'):>8}", 0)])
            lines += [[], [("Memory", bold | curses.A_UNDERLINE),
                           ("  loaded size incl. KV cache / recurrent state", curses.A_DIM)]]
            lines.append([(f"{'model':<{width}}{'group':<17}{'total GB':>9}{'GPU GB':>8}{'ctx':>8}"
                           f"{'params':>9}{'quant':>9}", bold)])
            for m in models:
                s = speed.get(m)
                if not s:
                    continue
                group = infos[m]["group"]
                lines.append([(f"{m:<{width}}", 0), (f"{group:<17}", group_color(group)),
                              (f"{fmt(s['memory_gb'], '.2f'):>9}{fmt(s['vram_gb'], '.2f'):>8}"
                               f"{str(s.get('context_length') or '–'):>8}"
                               f"{str(infos[m].get('parameter_size') or '–'):>9}"
                               f"{str(infos[m].get('quantization') or '–'):>9}", 0)])
            quants = {infos[m].get("quantization") for m in models}
            if len(quants) > 1:
                lines += [[], [(f"! Quantisation differs between models ({', '.join(sorted(map(str, quants)))}); "
                                "it affects accuracy, speed and memory.", curses.color_pair(YELLOW))]]
            contexts = {s.get("context_length") for s in speed.values()}
            if len(contexts) > 1:
                lines += [[(f"! Context length differs ({', '.join(sorted(map(str, contexts)))}); memory includes "
                            "the cache for that context, so use a Modelfile with the same num_ctx.",
                            curses.color_pair(YELLOW))]]
        self.draw_scrolled(lines)

    def draw_comparison_compare(self):
        data = read_json(self.out / "comparison.json")
        if not data:
            self.draw_scrolled([[("No results yet.", curses.A_DIM)]])
            return
        bold = curses.A_BOLD
        infos, accuracy, speed = data["models"], data.get("accuracy", {}), data.get("speed", {})
        comparisons = data.get("comparisons", [])
        groups = ["non-transformer", "transformer"]

        lines = [[("Architecture scoreboard", bold | curses.A_UNDERLINE),
                  ("  mean over the models in each group; wins = significant paired differences (Holm p<0.05)",
                   curses.A_DIM)]]
        lines.append([(f"{'benchmark':<12}", bold)] + [(f"{g + ' mean':<22}", group_color(g) | bold) for g in groups]
                     + [(f"{'NT wins':>8}{'T wins':>8}{'no diff':>9}", bold)])
        for b in [b for b in BENCHMARKS if b in accuracy]:
            row = [(f"{b:<12}", 0)]
            for g in groups:
                scores = [c["mean_score"] for m, c in accuracy[b].items()
                          if c["status"] == "success" and infos[m]["group"] == g]
                row.append((f"{fmt(sum(scores) / len(scores) if scores else None, '.3f') + f'  (n={len(scores)})':<22}", 0))
            cross = [c for c in comparisons if c["benchmark"] == b and c["cross_architecture"]]
            nt = sum(c["p_holm"] < 0.05 and c["diff"] > 0 for c in cross)
            t = sum(c["p_holm"] < 0.05 and c["diff"] < 0 for c in cross)
            row.append((f"{nt:>8}{t:>8}{len(cross) - nt - t:>9}", 0))
            lines.append(row)

        if speed:
            lines += [[], [("Efficiency by group", bold | curses.A_UNDERLINE), ("  medians of the models' medians", curses.A_DIM)]]
            lines.append([(f"{'group':<17}{'latency s':>10}{'chars/s':>9}{'memory GB':>11}", bold)])
            for g in groups:
                rows = [s for m, s in speed.items() if infos[m]["group"] == g]

                def mid(key):
                    values = [s[key] for s in rows if s.get(key) is not None]
                    return statistics.median(values) if values else None

                lines.append([(f"{g:<17}", group_color(g)),
                              (f"{fmt(mid('latency_s'), '.2f'):>10}{fmt(mid('output_chars_s')):>9}"
                               f"{fmt(mid('memory_gb'), '.2f'):>11}", 0)])

        lines += [[], [("Head-to-head accuracy", bold | curses.A_UNDERLINE),
                       ("  same questions; diff = A − B; * = significant after Holm", curses.A_DIM)]]
        if not comparisons:
            lines.append([("No pairs yet (needs at least one finished model per group on a benchmark).", curses.A_DIM)])
        width = max([len(m) for m in infos] + [5]) + 1
        current = None
        for c in comparisons:
            if c["benchmark"] != current:
                current = c["benchmark"]
                lines.append([(current, bold)])
            lo, hi = c["diff_ci"]
            significant = c["p_holm"] < 0.05
            if not significant:
                verdict, attr = "no significant difference", curses.A_DIM
            else:
                winner = c["model_a"] if c["diff"] > 0 else c["model_b"]
                verdict, attr = f"{winner} better", group_color(infos[winner]["group"]) | bold
            lines.append([(f"  {c['model_a']:<{width}}", group_color(infos[c['model_a']]['group'])),
                          ("vs ", curses.A_DIM),
                          (f"{c['model_b']:<{width}}", group_color(infos[c['model_b']]['group'])),
                          (f"{c['score_a']:.3f} vs {c['score_b']:.3f}  diff {c['diff']:+.3f} "
                           f"[{fmt(lo, '+.3f')},{fmt(hi, '+.3f')}]  p={c['p_holm']:.4f}{'*' if significant else ' '}  ", 0),
                          (verdict, attr)] + self.seed_agreement(c))

        cross_pairs = sorted({(c["model_a"], c["model_b"]) for c in comparisons if c["cross_architecture"]})
        if speed and cross_pairs:
            lines += [[], [("Head-to-head efficiency", bold | curses.A_UNDERLINE),
                           ("  ratio A / B; latency and memory < 1 means A is cheaper", curses.A_DIM)]]
            for a, b in cross_pairs:
                sa, sb = speed.get(a), speed.get(b)
                if not sa or not sb:
                    continue

                def ratio(key):
                    return sa[key] / sb[key] if sa.get(key) and sb.get(key) else None

                lines.append([(f"  {a:<{width}}", group_color(infos[a]["group"])), ("vs ", curses.A_DIM),
                              (f"{b:<{width}}", group_color(infos[b]["group"])),
                              (f"latency ×{fmt(ratio('latency_s'), '.2f')}  chars/s ×{fmt(ratio('output_chars_s'), '.2f')}"
                               f"  memory ×{fmt(ratio('memory_gb'), '.2f')}", 0)])
        self.draw_scrolled(lines)

    # ---------- loop ----------

    def handle(self, key):
        h, _ = self.screen.getmaxyx()
        items = self.setup_items() if self.tab == 0 else []
        option = items[self.cursor][1] if items and items[self.cursor][0] == "option" else None
        numeric = option is not None and option[3] in (int, float)
        if self.show_help:
            self.show_help = False
        elif key == ord("?"):
            self.show_help = True
        elif numeric and (ord("0") <= key <= ord("9") or key == ord(".")):
            self.edit_option(option, chr(key))
        elif numeric and key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            self.step_option(option, -1 if key == curses.KEY_LEFT else 1)
        elif key in (ord("1"), ord("2"), ord("3"), ord("4")):
            self.tab = key - ord("1")
        elif key == ord("\t"):
            self.tab = (self.tab + 1) % len(TABS)
        elif key == curses.KEY_BTAB:
            self.tab = (self.tab - 1) % len(TABS)
        elif self.tab == 0:
            if key in (curses.KEY_UP, ord("k")):
                self.cursor = max(0, self.cursor - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                self.cursor = min(len(items) - 1, self.cursor + 1)
            elif key in (ord(" "), ord("\n"), curses.KEY_ENTER) and items:
                self.activate(*items[self.cursor])
            elif key == ord("a") and items and items[self.cursor][0] == "model":
                self.cycle_arch(items[self.cursor][1])
            elif key == ord("R"):
                self.refresh_models()
                self.message = self.model_error or f"{len(self.models)} models found."
            elif key == ord("r"):
                self.start_run()
        else:
            if key == ord("s") and self.tab == 1:
                self.stop_run()
            elif key == ord("g") and self.tab in (2, 3):
                self.aggregate()
            elif key in (curses.KEY_UP, ord("k")):
                self.scroll[self.tab] -= 1
            elif key in (curses.KEY_DOWN, ord("j")):
                self.scroll[self.tab] += 1
            elif key == curses.KEY_PPAGE:
                self.scroll[self.tab] -= h - 5
            elif key == curses.KEY_NPAGE:
                self.scroll[self.tab] += h - 5
            elif key == curses.KEY_HOME:
                self.scroll[self.tab] = 0
            elif key == curses.KEY_END:
                self.scroll[self.tab] = 10 ** 6

    def run(self):
        curses.curs_set(0)
        curses.use_default_colors()
        for pair, color in [(GREEN, curses.COLOR_GREEN), (RED, curses.COLOR_RED), (YELLOW, curses.COLOR_YELLOW),
                            (CYAN, curses.COLOR_CYAN), (MAGENTA, curses.COLOR_MAGENTA)]:
            curses.init_pair(pair, color, -1)
        curses.init_pair(HEADER, curses.COLOR_BLACK, curses.COLOR_CYAN)
        self.screen.timeout(1000)  # redraw every second so Status stays live
        if self.running("optimise") and not self.running("compare"):
            self.mode = "optimise"
            self.load_previous_config()
        if self.running():
            self.tab = 1
        while True:
            self.screen.erase()
            self.draw_header()
            if self.show_help:
                self.draw_help()
            else:
                [self.draw_setup, self.draw_status, self.draw_results, self.draw_comparison][self.tab]()
            self.draw_footer()
            self.screen.refresh()
            key = self.screen.getch()
            if key in (ord("q"), 27):  # 27 = Esc
                return
            if key != -1:
                self.message = ""
                self.handle(key)


def main():
    parser = argparse.ArgumentParser(description="Terminal UI for compare_models.py")
    parser.add_argument("--output-dir", default="compare-results", dest="output_dir",
                        help="Folder of the architecture comparison (Compare mode).")
    parser.add_argument("--base-dir", default="runs", dest="base_dir",
                        help="Folder of the train + evaluate runs (Optimise mode).")
    args = parser.parse_args()
    os.environ.setdefault("ESCDELAY", "25")  # make Esc react immediately
    try:
        curses.wrapper(lambda screen: App(screen, args.output_dir, args.base_dir).run())
    except KeyboardInterrupt:
        pass
    print("TUI closed. A running comparison keeps going; reopen with: python tui.py")


if __name__ == "__main__":
    main()
