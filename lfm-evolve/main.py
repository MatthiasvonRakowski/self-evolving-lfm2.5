from src.AFlowOptimiser import AFlowOptimiser
from src.TextGradOptimiser import TextGradOptimiser
from evoagentx.models import LiteLLMConfig
import os
import argparse

def lfm_config():
    return LiteLLMConfig(
        model="ollama_chat/sam860/lfm2.5:1.2b",
        is_local=True,
        api_base="http://localhost:11434",
    )

def claude_config():
    return LiteLLMConfig(
        model="anthropic/claude-3-5-sonnet-20240620",
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
        choices=["aflow", "textgrad"],
        default=["aflow"],
        help="Optimiser(s) to run. Can specify multiple.",
    )
    args = argparser.parse_args()


    METHODS = {
        "aflow": lambda args: AFlowOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=args.output_dir + "aflow",
            executor_config=lfm_config(),
            optimiser_config=lfm_config(),
            graph_path=args.graph_path,
        ),
        "textgrad": lambda args: TextGradOptimiser(
            seed=args.seed,
            rounds=args.rounds,
            output_dir=args.output_dir + "textgrad",
            executor_config=lfm_config(),
            optimiser_config=lfm_config(),
        ),
    }

    for method in args.method:
        print(f"\n=== Running {method} ===")
        opt = METHODS[method](args)
        opt.run()


if __name__ == "__main__":
    main()