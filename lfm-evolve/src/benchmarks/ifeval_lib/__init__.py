"""IFEval instruction checker, vendored from lm-evaluation-harness 0.4.12 (lm_eval/tasks/ifeval/),
itself taken from google-research/instruction_following_eval. Apache License 2.0; see the file headers.

Only the four pure-Python modules are copied (imports rewritten to be relative); nothing else of
lm-eval was used, and depending on it pulled in a CUDA build of torch and ~5 GB of NVIDIA libraries.
The checker needs `langdetect`, `immutabledict`, `nltk` (with the punkt_tab tokenizer) and `packaging`.
"""
