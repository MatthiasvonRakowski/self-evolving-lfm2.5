"""Shared infrastructure for main.py, evaluate.py and the bilevel optimiser.

Importing this module has side effects (applied once): .env loading, litellm
logging silencers, and the LiteLLM.init_model api_base-nulling monkeypatch.
"""

import contextlib
import os
import sys

import dotenv
import litellm
from evoagentx.models import LiteLLMConfig, LiteLLM

litellm.turn_off_message_logging = True
litellm.success_callback = []
litellm.failure_callback = []
litellm._async_success_callback = []
litellm._async_failure_callback = []

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
