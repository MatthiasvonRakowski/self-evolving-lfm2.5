prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the proposed solution to the math problem below.

Check each calculation step carefully. If the solution is correct, restate it with the final answer on its own line prefixed with "#### ". If there are any errors, provide the corrected step-by-step solution and give the correct final numerical answer on its own line prefixed with "#### ".

Important: Always end your response with the final answer on a line by itself in the format: #### <number>

"""