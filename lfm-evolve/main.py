from src.AFlowOptimiser import AFlowOptimiser
from src.TextGradOptimiser import TextGradOptimiser
from src.MiproOptimiser import MiproOptimiser

import os
import argparse
import dotenv

import litellm
from evoagentx.models import LiteLLMConfig, LiteLLM

# Load env once, up front, so ANTHROPIC_API_KEY is available everywhere below.
dotenv.load_dotenv()
os.environ["ANTHROPIC_API_BASE"] = "https://api.anthropic.com"  # extra safety; harmless

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


def lfm_config():
    return LiteLLMConfig(
        model="ollama_chat/lfm2.5-16k",
        is_local=True,
        api_base="http://localhost:11434",
    )

def claude_config():
    """Cloud optimiser model (Claude Sonnet 4.6)."""
    return LiteLLMConfig(
        model="anthropic/claude-sonnet-4-6",
        anthropic_key=os.environ["ANTHROPIC_API_KEY"],
    )


def main():
    argparser = argparse.ArgumentParser(description="Run optimisers on benchmarks.")
    argparser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")
    argparser.add_argument("--rounds", type=int, default=None, help="Number of optimization rounds to run.")
    argparser.add_argument("--output_dir", type=str, default="output", help="Directory to save optimization results.")
    argparser.add_argument("--graph_path", type=str, default="src/aflow_workflow", help="Path to the graph file.")
    argparser.add_argument(
        "--method", nargs="+",
        choices=["aflow", "textgrad", "mipro"],
        default=["aflow"],
        help="Optimiser(s) to run. Can specify multiple.",
    )
    args = argparser.parse_args()

    METHODS = {
        "aflow": lambda args: AFlowOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(args.output_dir, "aflow"),
            executor_config=lfm_config(),
            optimiser_config=claude_config(),
            graph_path=args.graph_path,
        ),
        "textgrad": lambda args: TextGradOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(args.output_dir, "textgrad"),
            executor_config=lfm_config(),
            optimiser_config=lfm_config(),
        ),
        "mipro": lambda args: MiproOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=os.path.join(args.output_dir, "mipro"),
            executor_config=lfm_config(),
            optimiser_config=claude_config(),
        ),
    }

    for method in args.method:
        print(f"\n=== Running {method} ===")
        opt = METHODS[method](args)
        opt.run()


if __name__ == "__main__":
    main()
