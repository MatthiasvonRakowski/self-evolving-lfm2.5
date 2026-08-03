prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the proposed solution to the math problem below.

Steps:
1. Re-read the problem carefully.
2. Check each calculation step in the proposed solution.
3. If you find any errors, redo the solution correctly.
4. If the solution is correct, confirm it.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""