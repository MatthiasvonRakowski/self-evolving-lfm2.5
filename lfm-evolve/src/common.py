import contextlib
import importlib.metadata
import json
import os
import sys
import threading
import time

# tqdm reads its TQDM_* defaults when it is imported, so this has to run before litellm/evoagentx
# pull it in. Progress bars redraw many times a second by default, which floods the log files.
os.environ.setdefault("TQDM_MININTERVAL", "10")

import dotenv
import litellm
from litellm.litellm_core_utils.logging_worker import GLOBAL_LOGGING_WORKER, LoggingWorker
from loguru import logger
from loguru._recattrs import RecordLevel
from evoagentx.models import LiteLLMConfig, LiteLLM
from evoagentx.optimizers import AFlowOptimizer

from src.naming import (  # noqa: F401  (re-exported for existing imports)
    DEFAULT_EXECUTOR_MODEL, DEFAULT_OPTIMISER_MODEL, LITELLM_PROVIDERS, OPTIMISER_MODELFILE,
    model_label, ollama_name, resolve_model_id,
)

# ---------------------------------------------------------------------------------------------
# Third-party internals this module patches, and private EvoAgentX methods src/aflow_base.py and
# src/BilevelOptimiser.py override. All of it was written against these exact versions; anything
# else fails loudly here instead of silently doing nothing (or crashing hours into a run).

PINNED_VERSIONS = {"litellm": "1.86.2", "dspy": "2.6.27"}
EVOAGENTX_COMMIT = "f542ce4e0151166549975b4e15d7c7e4ca312af3"
_PATCHED_ATTRIBUTES = [
    (LiteLLM, "init_model"),
    (LiteLLM, "_update_cost"),
    (LoggingWorker, "ensure_initialized_and_enqueue"),
    (AFlowOptimizer, "_evaluate_and_save_optimization_results"),
    (AFlowOptimizer, "_run_test"),
    (AFlowOptimizer, "_load_best_round"),
    (AFlowOptimizer, "test"),
]

def _installed_evoagentx_commit():
    try:
        text = importlib.metadata.distribution("evoagentx").read_text("direct_url.json")
        return json.loads(text or "{}").get("vcs_info", {}).get("commit_id")
    except Exception:
        return None

def check_pinned_internals():
    if os.environ.get("LFM_SKIP_VERSION_CHECK"):
        return
    problems = []
    for dist, wanted in PINNED_VERSIONS.items():
        installed = importlib.metadata.version(dist)
        if installed != wanted:
            problems.append(f"{dist} {installed} is installed; the patches were written for {wanted}")
    commit = _installed_evoagentx_commit()
    if commit and commit != EVOAGENTX_COMMIT:
        problems.append(f"evoagentx is at commit {commit[:12]}; expected {EVOAGENTX_COMMIT[:12]}")
    for owner, name in _PATCHED_ATTRIBUTES:
        if not hasattr(owner, name):
            problems.append(f"{owner.__name__}.{name} no longer exists")
    if problems:
        raise RuntimeError(
            "src/common.py patches litellm, DSPy and EvoAgentX internals, and the installed versions "
            "differ from the ones they were written for:\n  - " + "\n  - ".join(problems) +
            "\nInstall the pinned versions (pyproject.toml, `uv sync`) or review the patches, then "
            "set LFM_SKIP_VERSION_CHECK=1 to run anyway."
        )

check_pinned_internals()

# ---------------------------------------------------------------------------------------------
# LLM usage accounting (one jsonl record per call; summarised into run_summary.json).
#
# Recorded from EvoAgentX's LiteLLM._update_cost, which both of its generate paths (sync and async)
# call inline with the token counts and litellm's price for the model. The litellm success callbacks
# used before were unreliable here: a function registered in both callback lists is skipped by the
# sync path, and the async path runs on litellm's logging worker, whose tasks die whenever EvoAgentX
# closes the event loop it creates for a single WorkFlow.execute() call (TextGrad steps, MIPRO).
# On 2026-10-13 that lost every MIPRO call and every TextGrad optimiser call.

litellm.turn_off_message_logging = True
litellm.success_callback = []
litellm.failure_callback = []
litellm._async_success_callback = []
litellm._async_failure_callback = []

try:
    from litellm_enterprise.enterprise_callbacks.callback_controls import EnterpriseCallbackControls
    EnterpriseCallbackControls.is_callback_disabled_dynamically = staticmethod(lambda *a, **k: False)
except Exception:
    pass

_usage_lock = threading.Lock()

_ANTHROPIC_FALLBACK_PRICE_PER_TOKEN = {
    "input": 3.0 / 1_000_000,
    "output": 15.0 / 1_000_000,
}

def is_anthropic_model(model) -> bool:
    name = str(model or "").lower()
    return name.startswith("anthropic/") or "claude" in name

def usage_model_name(model) -> str:
    """Model name as stored in the usage records: the Ollama name for local models."""
    name = str(model or "unknown")
    for prefix in ("ollama_chat/", "ollama/"):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name

def record_usage(model, prompt_tokens, completion_tokens, cost_usd=0.0):
    """Append one record to the file named by LLM_USAGE_LOG (main.py points it at usage/<method>.jsonl)."""
    log_path = os.environ.get("LLM_USAGE_LOG")
    if not log_path:
        return
    prompt_tokens = int(prompt_tokens or 0)
    completion_tokens = int(completion_tokens or 0)
    if not cost_usd and is_anthropic_model(model):
        cost_usd = (prompt_tokens * _ANTHROPIC_FALLBACK_PRICE_PER_TOKEN["input"]
                    + completion_tokens * _ANTHROPIC_FALLBACK_PRICE_PER_TOKEN["output"])
    record = {
        "ts": time.time(),
        "model": usage_model_name(model),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": float(cost_usd or 0.0),
    }
    with _usage_lock:
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")

_orig_update_cost = LiteLLM._update_cost

def _update_cost_and_record(self, cost):
    _orig_update_cost(self, cost)
    try:
        record_usage(self.config.model, cost.input_tokens, cost.output_tokens,
                     cost.input_cost + cost.output_cost)
    except Exception:
        pass  # accounting must never fail a call

LiteLLM._update_cost = _update_cost_and_record

def summarize_usage(jsonl_path):
    summary = {
        "anthropic": {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0},
        "local": {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0},
        # Executor and a local optimiser are both "local"; this keeps them apart.
        "by_model": {},
    }
    if not jsonl_path or not os.path.exists(jsonl_path):
        return summary
    try:
        with open(jsonl_path) as f:
            lines = f.readlines()
    except Exception:
        return summary
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except Exception:
            continue
        provider = "anthropic" if is_anthropic_model(record.get("model", "")) else "local"
        bucket = summary[provider]
        bucket["calls"] += 1
        bucket["prompt_tokens"] += record.get("prompt_tokens", 0) or 0
        bucket["completion_tokens"] += record.get("completion_tokens", 0) or 0
        bucket["cost_usd"] += record.get("cost_usd", 0.0) or 0.0
        per_model = summary["by_model"].setdefault(
            record.get("model", "unknown"), {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0})
        per_model["calls"] += 1
        per_model["prompt_tokens"] += record.get("prompt_tokens", 0) or 0
        per_model["completion_tokens"] += record.get("completion_tokens", 0) or 0
    return summary

# ---------------------------------------------------------------------------------------------
# Patches of litellm / DSPy behaviour (see check_pinned_internals for the versions).

dotenv.load_dotenv()
os.environ["ANTHROPIC_API_BASE"] = "https://api.anthropic.com"

_orig_init_model = LiteLLM.init_model

# EvoAgentX sets litellm's *global* api_base to the local model's URL, which would send Claude calls
# to Ollama. Per-call api_base is still passed for local models, so the global one can go.
def _init_model_no_global_base(self):
    _orig_init_model(self)
    litellm.api_base = None

LiteLLM.init_model = _init_model_no_global_base

# litellm hands every async completion's success handler to a background "logging worker" that is
# bound to the event loop of the first call. EvoAgentX's WorkFlow.execute() creates and closes a loop
# per call, so those handler tasks are destroyed with their loop: hundreds of "Task was destroyed but
# it is pending!" / "Event loop is closed" tracebacks per TextGrad arm (runs_smoke_v3, 2026-10-13).
# The harness registers no litellm callbacks (usage is recorded above), so the handler has nothing
# to do: close the coroutine instead of scheduling it.
def _drop_async_logging(async_coroutine):
    async_coroutine.close()

GLOBAL_LOGGING_WORKER.ensure_initialized_and_enqueue = _drop_async_logging

# DSPy retries with JSONAdapter when a reply misses its [[ ## field ## ]] markers (local models
# often answer in a ```json block instead). JSONAdapter starts with lm.model.split("/"), but
# EvoAgentX's MiproLMWrapper keeps an LLM object in .model, so the retry crashed and MIPRO died.
# Without a model name there is no structured-output probe to do: use JSON formatting/parsing directly.
from dspy.adapters.chat_adapter import ChatAdapter
from dspy.adapters.json_adapter import JSONAdapter

_orig_json_adapter_call = JSONAdapter.__call__

def _json_adapter_call(self, lm, lm_kwargs, signature, demos, inputs):
    if not isinstance(getattr(lm, "model", None), str):
        return ChatAdapter.__call__(self, lm, lm_kwargs, signature, demos, inputs)
    return _orig_json_adapter_call(self, lm, lm_kwargs, signature, demos, inputs)

JSONAdapter.__call__ = _json_adapter_call

# ---------------------------------------------------------------------------------------------
# Logging. EvoAgentX routes everything through the global loguru logger, and two habits of its shape
# the code below:
#   * it binds its console sink to the sys.stdout *object* -- at import, and again every time
#     suppress_logger_info() exits -- so after tee_to_file swaps sys.stdout the sink must be rebound,
#     or a method's loguru lines bypass its own log file;
#   * suppress_logger_info() calls logger.remove() with no arguments, so any sink or filter added
#     here is gone after the first validation pass. The one hook that survives is the core patcher.

_CONSOLE_LOG_LEVEL = os.environ.get("LFM_LOG_LEVEL", "INFO").upper()

def _demote_cost_spam(record):
    # evoagentx logs "Total cost ... | Current tokens ..." at INFO after every single LLM call:
    # thousands of lines per run that bury everything else. The numbers are in the usage jsonl.
    if record["function"] == "update_cost" and record["name"].startswith("evoagentx.models"):
        record["level"] = RecordLevel("DEBUG", 10, record["level"].icon)

logger.configure(patcher=_demote_cost_spam)

def bind_console_logger(stream):
    logger.remove()
    logger.add(stream, level=_CONSOLE_LOG_LEVEL)

bind_console_logger(sys.stdout)

class _Tee:
    """Mirror a console stream into a log file.

    Loguru sinks can keep a reference to a tee after its file is closed (suppress_logger_info
    rebinding), so writes to a closed member are skipped instead of raising.
    """

    def __init__(self, console, file):
        self.console = console
        self.file = file

    def write(self, data):
        if not self.console.closed:
            self.console.write(data)
            self.console.flush()
        if not self.file.closed:
            # tqdm redraws its bar with "\r"; in a file that is one endless line, so each redraw
            # becomes a line of its own.
            self.file.write(data.replace("\r", "\n"))
            self.file.flush()

    def flush(self):
        for stream in (self.console, self.file):
            if not stream.closed:
                stream.flush()

    def isatty(self):
        return False

    @property
    def encoding(self):
        return getattr(self.console, "encoding", "utf-8")

    @property
    def closed(self):
        return False

@contextlib.contextmanager
def tee_to_file(log_path):
    """Send stdout, stderr and loguru output to `log_path` as well as the console."""
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    f = open(log_path, "a", buffering=1, encoding="utf-8", errors="replace")
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = _Tee(old_out, f), _Tee(old_err, f)
    bind_console_logger(sys.stdout)
    try:
        yield
    finally:
        sys.stdout, sys.stderr = old_out, old_err
        bind_console_logger(old_out)
        f.close()

# ---------------------------------------------------------------------------------------------
# Model configurations.

OLLAMA_API_BASE = "http://localhost:11434"

# A 1-2B executor answers in seconds. These bounds only catch runaway generations (small models do
# loop until the context is full) and a server that has been pushed onto the CPU, so that such calls
# end as recorded errors instead of hanging. litellm's default timeout is 600 s; Ollama's default
# num_predict is unlimited. The longest IFEval request asks for 1200 words (~1700 tokens).
EXECUTOR_TIMEOUT_S = int(os.environ.get("LFM_EXECUTOR_TIMEOUT", 1800))
EXECUTOR_MAX_TOKENS = int(os.environ.get("LFM_EXECUTOR_MAX_TOKENS", 4096))

def executor_config(model=None):
    return LiteLLMConfig(
        model=resolve_model_id(model),
        is_local=True,
        api_base=OLLAMA_API_BASE,
        timeout=EXECUTOR_TIMEOUT_S,
        max_tokens=EXECUTOR_MAX_TOKENS,
    )

def claude_config(model="anthropic/claude-sonnet-4-6"):
    return LiteLLMConfig(
        model=model,
        anthropic_key=os.environ["ANTHROPIC_API_KEY"],
    )

# The optimiser rewrites workflows and prompts. It runs locally by default; build it with
# `ollama create <DEFAULT_OPTIMISER_MODEL> -f <OPTIMISER_MODELFILE>` (Ollama's default context would
# silently truncate the optimiser prompts, which carry the workflow code and failed examples).
def optimiser_config(model=None):
    model = model or DEFAULT_OPTIMISER_MODEL
    if is_anthropic_model(model):
        return claude_config(model if model.startswith("anthropic/") else f"anthropic/{model}")
    return LiteLLMConfig(
        model=resolve_model_id(model),
        is_local=True,
        api_base=OLLAMA_API_BASE,
        # A local 16B writing a whole workflow can take minutes; litellm's default is 600 s.
        timeout=1800,
        # Qwen3 thinks by default, which made each call ~15x slower in testing. LiteLLM maps
        # this to Ollama's think=false; models without a thinking mode ignore it.
        reasoning_effort="none",
    )

PROBLEM_PLACEHOLDERS = ("{{problem}}", "{problem}")

class PromptPlaceholderError(ValueError):
    pass

def fill_prompt_template(template: str, problem: str) -> str:
    if not isinstance(template, str):
        raise PromptPlaceholderError(f"prompt template is {type(template).__name__}, not str")
    for placeholder in PROBLEM_PLACEHOLDERS:
        if placeholder in template:
            return template.replace(placeholder, problem)
    raise PromptPlaceholderError(
        "prompt template contains no {problem} or {{problem}} placeholder, so the "
        "problem text would never reach the model. Template starts: "
        f"{template[:120]!r}"
    )

def hf_load_dataset(*args, timeouts=(30, 60, 120), **kwargs):
    import huggingface_hub.constants as hf_constants
    from datasets import load_dataset

    last_err = None
    for i, timeout_s in enumerate(timeouts):
        hf_constants.HF_HUB_ETAG_TIMEOUT = timeout_s
        hf_constants.HF_HUB_DOWNLOAD_TIMEOUT = timeout_s
        try:
            return load_dataset(*args, **kwargs)
        except Exception as e:
            last_err = e
            print(f"[hf_load_dataset] attempt {i + 1}/{len(timeouts)} "
                  f"(timeout={timeout_s}s) failed: {e}")
    raise RuntimeError(
        f"Failed to load HuggingFace dataset {args!r} after {len(timeouts)} "
        f"attempts with increasing timeouts {timeouts}. This usually means "
        f"the network to huggingface.co is slow, blocked, or proxied. Check "
        f"connectivity, or pre-populate the cache/jsonl file manually."
    ) from last_err
