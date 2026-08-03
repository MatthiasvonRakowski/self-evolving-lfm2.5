prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_ALT_PROMPT = """You are an expert mathematician. Carefully read and solve the following math problem using a systematic approach.

Break the problem into smaller parts, compute each part carefully, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. You are given a math problem and two independent solutions (Solution A and Solution B).

Your tasks:
1. Check each solution's arithmetic and logic steps for correctness.
2. If both solutions agree on the final answer, confirm that answer.
3. If they disagree, identify which solution is correct by re-deriving the answer from scratch.
4. Provide a brief corrected step-by-step reasoning if needed.

Always end with the final numerical answer on its own line prefixed with "#### ".

"""