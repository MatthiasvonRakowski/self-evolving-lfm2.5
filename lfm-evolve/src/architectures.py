"""Architecture groups for compare_models.py and tui.py. Kept free of heavy imports."""

# Ollama's `general.architecture` value -> (group, description).
ARCHITECTURES = {
    "lfm2": ("non-transformer", "gated short-conv + attention hybrid"),
    "lfm2moe": ("non-transformer", "gated short-conv + attention hybrid (MoE)"),
    "granitehybrid": ("non-transformer", "Mamba-2 + attention hybrid"),
    "falcon_h1": ("non-transformer", "Mamba-2 + attention hybrid"),
    "falcon-h1": ("non-transformer", "Mamba-2 + attention hybrid"),
    "nemotron_h": ("non-transformer", "Mamba-2 + attention hybrid"),
    "jamba": ("non-transformer", "Mamba + attention hybrid"),
    "qwen3next": ("non-transformer", "gated DeltaNet + attention hybrid"),
    "mamba": ("non-transformer", "Mamba SSM"),
    "mamba2": ("non-transformer", "Mamba-2 SSM"),
    "rwkv6": ("non-transformer", "RWKV-6 recurrent"),
    "rwkv7": ("non-transformer", "RWKV-7 recurrent"),
    "llama": ("transformer", "decoder-only transformer"),
    "qwen2": ("transformer", "decoder-only transformer"),
    "qwen3": ("transformer", "decoder-only transformer"),
    "qwen3moe": ("transformer", "decoder-only transformer (MoE)"),
    "gemma": ("transformer", "decoder-only transformer"),
    "gemma2": ("transformer", "decoder-only transformer"),
    "gemma3": ("transformer", "decoder-only transformer"),
    "gemma3n": ("transformer", "decoder-only transformer"),
    "phi3": ("transformer", "decoder-only transformer"),
    "mistral": ("transformer", "decoder-only transformer"),
    "granite": ("transformer", "decoder-only transformer"),
    "olmo": ("transformer", "decoder-only transformer"),
    "olmo2": ("transformer", "decoder-only transformer"),
    "smollm3": ("transformer", "decoder-only transformer"),
    "exaone": ("transformer", "decoder-only transformer"),
    "stablelm": ("transformer", "decoder-only transformer"),
    "gptoss": ("transformer", "decoder-only transformer (MoE)"),
}

GROUP_ORDER = {"non-transformer": 0, "transformer": 1, "unknown": 2}
