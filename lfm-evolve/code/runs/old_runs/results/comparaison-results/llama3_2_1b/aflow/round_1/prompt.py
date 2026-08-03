prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You are given a math problem and a proposed solution.

Review the proposed solution step by step:
1. Check each calculation for arithmetic errors.
2. Check that the reasoning logic is correct.
3. If the solution is correct, restate it clearly with the final answer on its own line prefixed with "#### ".
4. If there are errors, provide the corrected solution with the correct final answer on its own line prefixed with "#### ".

Always end your response with the final numerical answer on a line by itself prefixed with "#### ".

"""