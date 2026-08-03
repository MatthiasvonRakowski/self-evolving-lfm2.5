prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. Review the proposed solution to the math problem below.
Check each calculation step for errors. If the solution is correct, restate it clearly.
If there are errors, provide the corrected full solution with clear step-by-step reasoning.
Always end with the final numerical answer on its own line prefixed with "#### ".

"""