"""Model-name helpers and model defaults. Kept free of heavy imports so tui.py can use them."""

DEFAULT_EXECUTOR_MODEL = "ollama_chat/lfm2.5-16k"

# The optimiser rewrites workflows and prompts. deepseek-coder-v2 16B is the largest coder that still
# shares the 8 GB card with the executor: its Modelfile puts 15 layers on the GPU and leaves ~2 GB.
DEFAULT_OPTIMISER_MODEL = "deepseek-coder-v2-16b-8k"
OPTIMISER_MODELFILE = "Modelfile.deepseek-coder-v2-16b-8k"

# A "/" alone doesn't mean a provider prefix: Ollama names like "sam860/lfm2.5:1.2b" have one too.
LITELLM_PROVIDERS = ("ollama_chat/", "ollama/", "anthropic/", "openai/")

def resolve_model_id(model=None):

    model_id = model or DEFAULT_EXECUTOR_MODEL
    if not model_id.startswith(LITELLM_PROVIDERS):
        model_id = f"ollama_chat/{model_id}"
    return model_id

def ollama_name(model=None):
    model_id = model or DEFAULT_EXECUTOR_MODEL
    for prefix in ("ollama_chat/", "ollama/"):
        if model_id.startswith(prefix):
            return model_id[len(prefix):]
    return model_id

def model_label(model=None):
    raw = model or DEFAULT_EXECUTOR_MODEL
    short = raw.split("/")[-1]
    return short.replace(":", "_").replace("/", "_").replace(".", "_").replace("-", "_")
