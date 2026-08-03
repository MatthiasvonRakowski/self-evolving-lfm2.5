SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You will solve the problem independently first, then compare with the previous solution.

Step 1: Re-solve the problem completely from scratch, showing all steps.

Step 2: Check for these common error types:
- Arithmetic errors: recompute every addition, subtraction, multiplication, and division explicitly.
- Problem setup errors: ensure the question is interpreted correctly and all relevant quantities are identified.
- Logic/ordering errors: confirm operations are applied in the correct sequence.
- Off-by-one or unit errors: check counts, rates, and any unit conversions.

Step 3: Compare your answer with the previous solution. If both agree, confirm the answer. If they disagree, carefully re-examine each step to find the error and determine the correct answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

Problem and previous solution to review: """