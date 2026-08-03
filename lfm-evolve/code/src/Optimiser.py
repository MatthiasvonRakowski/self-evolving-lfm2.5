from pathlib import Path

class Optimiser:
    def __init__(self, seed: int, rounds: int, output_dir: Path, executor_config, optimiser_config):
        self.seed = seed
        self.rounds = rounds
        self.output_dir = output_dir
        self.executor_config = executor_config
        self.optimiser_config = optimiser_config

    def run(self):
        raise NotImplementedError("Subclasses should implement this method.")
