prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the previous solution to the math problem below. 
Check each step for arithmetic or logical errors.
If the solution is correct, restate it with the final answer on its own line prefixed with "#### ".
If there are errors, provide the corrected solution step by step, with the final answer on its own line prefixed with "#### ".

Problem and previous solution: """