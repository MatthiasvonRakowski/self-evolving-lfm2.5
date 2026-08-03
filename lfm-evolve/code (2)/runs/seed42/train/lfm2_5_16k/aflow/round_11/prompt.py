SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You will solve the problem independently first, then compare with the previous solution.

Step 1: Re-solve the problem completely from scratch, showing all steps.
Step 2: Compare your answer with the previous solution. Identify any discrepancies.
Step 3: If both solutions agree, confirm the answer. If they disagree, carefully re-examine each step to find the error and determine the correct answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

Problem and previous solution to review: """