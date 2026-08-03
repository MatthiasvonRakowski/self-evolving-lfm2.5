SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. You will be given a math problem and an initial solution attempt.

Review the solution step by step:
1. Check each calculation for arithmetic errors.
2. Verify the logic and reasoning is correct.
3. If you find errors, redo the solution correctly.
4. If the solution is correct, confirm it.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""