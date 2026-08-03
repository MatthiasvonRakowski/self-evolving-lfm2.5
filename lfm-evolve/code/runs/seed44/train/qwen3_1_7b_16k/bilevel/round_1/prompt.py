prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the proposed solution to the math problem below.

Steps:
1. Re-read the problem carefully.
2. Check each step of the proposed solution for correctness.
3. If the solution is correct, restate it with the final answer on its own line prefixed with "#### ".
4. If you find any error, provide the corrected solution step by step, and end with the correct final answer on its own line prefixed with "#### ".

Only output the verified or corrected solution. Always end with a line in the format: #### <number>

"""