prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. You will be given a math problem and a proposed solution.

Review the solution step by step for any arithmetic or logic errors. If the solution is correct, restate it. If there are errors, provide the corrected solution.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""