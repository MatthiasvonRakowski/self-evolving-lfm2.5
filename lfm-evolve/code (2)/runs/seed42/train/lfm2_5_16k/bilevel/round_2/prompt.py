prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the proposed solution to the math problem below.

Check each calculation step for errors. If the solution is correct, restate it. If there are mistakes, provide the corrected full solution.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""