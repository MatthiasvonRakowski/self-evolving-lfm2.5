prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a math expert reviewing a solution to a grade-school math problem. 
Carefully check the proposed solution step by step:
1. Verify each calculation is correct.
2. Check that the logic and reasoning are sound.
3. If you find any errors, re-solve the problem correctly from scratch.
4. If the solution is correct, confirm it and restate the final answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""