prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the given problem and its previous solution.
Check each calculation step carefully for arithmetic errors or logical mistakes.
If the solution is correct, restate the final answer. If there are errors, provide the corrected solution.
Show your verification steps clearly, then provide the final numerical answer on its own line prefixed with "#### ".

"""