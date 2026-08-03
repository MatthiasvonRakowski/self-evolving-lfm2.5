SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_DIRECT_PROMPT = """You are a precise math calculator. Solve the following math problem by carefully computing each arithmetic operation one at a time.

Write out every calculation explicitly, double-check your arithmetic, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

ENSEMBLE_PROMPT = """You are given a math problem and two independent solutions. Your task is to determine the correct final answer.

1. Check if both solutions agree on the final answer.
2. If they agree, use that answer.
3. If they disagree, carefully re-examine the problem and both solutions, then determine the correct answer.

Output only the final verified answer on a line prefixed with "#### " (e.g., #### 42).

"""