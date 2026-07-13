prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. Review the proposed solution to the math problem below.
Check each calculation step carefully for arithmetic errors or logical mistakes.
If the solution is correct, restate it clearly.
If there are errors, provide the corrected solution with clear step-by-step reasoning.
Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""