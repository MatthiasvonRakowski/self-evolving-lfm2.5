prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the provided problem and its initial solution.
Check each calculation step for errors. If the solution is correct, restate it with the same format.
If you find any errors, provide the corrected full solution with clear step-by-step reasoning.
Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""