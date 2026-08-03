SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. You are given a math problem and a proposed solution.

Review the proposed solution step by step:
1. Check each arithmetic calculation for correctness.
2. Verify the logic and reasoning are sound.
3. If you find any errors, redo the solution correctly from scratch.
4. If the solution is correct, confirm and restate it.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""