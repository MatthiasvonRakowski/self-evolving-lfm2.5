"""Shared infrastructure for main.py, evaluate.py and the bilevel optimiser.

Importing this module has side effects (applied once): .env loading, litellm
logging silencers, and the LiteLLM.init_model api_base-nulling monkeypatch.
"""

import contextlib
import json
import os
import sys
import threading
import time

import dotenv
import litellm
from evoagentx.models import LiteLLMConfig, LiteLLM

litellm.turn_off_message_logging = True
litellm.success_callback = []
litellm.failure_callback = []
litellm._async_success_callback = []
litellm._async_failure_callback = []

# ---------------------------------------------------------------------------
# DURABLE FIX for a broken litellm_enterprise import chain that silently
# kills ALL success callbacks (not just ours).
#
# litellm's should_run_callback() calls EnterpriseCallbackControls.
# is_callback_disabled_dynamically() unconditionally for every callback, on
# every call. That method does an unguarded `from ...custom_logger_registry
# import CustomLoggerRegistry`, which transitively imports a Focus/S3 logger
# requiring `boto3` -- not installed here, and unrelated to anything this
# repo uses. The ImportError propagates out of should_run_callback and is
# swallowed by litellm as a "non-blocking" logging error, so every
# registered success callback (ours included) silently never runs. We
# neutralize just that dynamic-disable check (a proxy/enterprise feature
# this repo doesn't use), verified against a live Ollama call.
# ---------------------------------------------------------------------------
try:
    from litellm_enterprise.enterprise_callbacks.callback_controls import EnterpriseCallbackControls
    EnterpriseCallbackControls.is_callback_disabled_dynamically = staticmethod(lambda *a, **k: False)
except Exception:
    pass
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# LLM usage/cost tracking.
#
# Every litellm.completion/acompletion call (both the local Ollama executor
# and the Claude optimiser) runs through this callback. It's a no-op unless
# the LLM_USAGE_LOG env var is set (main.py sets it per-cell), and it must
# never raise -- a broken logger must not break a multi-day optimisation run.
# ---------------------------------------------------------------------------
_usage_lock = threading.Lock()

# Hardcoded fallback pricing for when litellm's price map doesn't know the
# model (e.g. a Claude model id newer than the installed litellm version).
# Token counts from response_obj.usage remain ground truth regardless.
_ANTHROPIC_FALLBACK_PRICE_PER_TOKEN = {
    "input": 3.0 / 1_000_000,
    "output": 15.0 / 1_000_000,
}


def _usage_callback(kwargs, response_obj, start_time, end_time):
    try:
        log_path = os.environ.get("LLM_USAGE_LOG")
        if not log_path:
            return
        model = kwargs.get("model", "unknown")
        usage = getattr(response_obj, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0

        cost_usd = kwargs.get("response_cost")
        if not cost_usd and model.startswith("anthropic/"):
            cost_usd = (
                prompt_tokens * _ANTHROPIC_FALLBACK_PRICE_PER_TOKEN["input"]
                + completion_tokens * _ANTHROPIC_FALLBACK_PRICE_PER_TOKEN["output"]
            )
        cost_usd = cost_usd or 0.0

        record = {
            "ts": time.time(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
        }
        with _usage_lock:
            os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
            with open(log_path, "a") as f:
                f.write(json.dumps(record) + "\n")
    except Exception:
        pass


litellm.success_callback.append(_usage_callback)
litellm._async_success_callback.append(_usage_callback)


def summarize_usage(jsonl_path):
    """Sum calls/tokens/cost from a usage jsonl, split by provider ('anthropic'
    vs 'local'). Tolerant of a missing file or a corrupt trailing line (e.g.
    a crash mid-write)."""
    summary = {
        "anthropic": {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0},
        "local": {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0},
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
        provider = "anthropic" if str(record.get("model", "")).startswith("anthropic/") else "local"
        bucket = summary[provider]
        bucket["calls"] += 1
        bucket["prompt_tokens"] += record.get("prompt_tokens", 0) or 0
        bucket["completion_tokens"] += record.get("completion_tokens", 0) or 0
        bucket["cost_usd"] += record.get("cost_usd", 0.0) or 0.0
    return summary

# Load env once, up front, so ANTHROPIC_API_KEY is available everywhere below.
dotenv.load_dotenv()
os.environ["ANTHROPIC_API_BASE"] = "https://api.anthropic.com"  # extra safety; harmless

# Default local executor model (your custom 16k-context LFM2.5 Modelfile build).
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
    summary keys). e.g. 'qwen3:1.7b' -> 'qwen3_1_7b'."""
    raw = model or DEFAULT_EXECUTOR_MODEL
    short = raw.split("/")[-1]
    return short.replace(":", "_").replace("/", "_").replace(".", "_").replace("-", "_")


def claude_config():
    """Cloud optimiser model (Claude Sonnet 4.6)."""
    return LiteLLMConfig(
        model="anthropic/claude-sonnet-4-6",
        anthropic_key=os.environ["ANTHROPIC_API_KEY"],
    )


def hf_load_dataset(*args, timeouts=(30, 60, 120), **kwargs):
    """datasets.load_dataset with HF Hub timeouts bumped and retried.

    The Hub's metadata/etag HEAD requests (e.g. README.md) default to a 10s
    timeout, which read-times-out on slow/unstable connections well before
    the actual data transfer would. huggingface_hub reads
    HF_HUB_ETAG_TIMEOUT/HF_HUB_DOWNLOAD_TIMEOUT dynamically at call time (not
    baked into function defaults), so patching them at runtime works
    regardless of import order.
    """
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
