prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the provided problem and its solution step by step.
Check each calculation for correctness. If the solution is correct, restate it with the same final answer format.
If there is any error, provide the corrected full solution.
Always end with the final numerical answer on its own line prefixed with "#### ".

"""