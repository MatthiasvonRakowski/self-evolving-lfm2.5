SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the proposed solution to the math problem below.
Check each arithmetic step for correctness. Verify units, operations, and intermediate values carefully.
If the solution is correct, restate it clearly.
If there are errors, provide the corrected solution with clear step-by-step reasoning.
Always end with the final numerical answer on its own line prefixed with "#### ".

"""

VERIFY_MATH_PROMPT = """You are an expert math verifier. You are given a problem and two solution attempts.
Compare both solutions carefully:
1. Identify which solution has correct arithmetic at every step.
2. If both agree on the final answer, confirm that answer.
3. If they disagree, determine which is correct by re-computing key steps independently.
4. Provide a concise final solution with the correct reasoning.
Always end with the final numerical answer on its own line prefixed with "#### ".

"""