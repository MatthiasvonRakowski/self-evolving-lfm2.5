SOLVE_MATH_PROMPT = """You are a careful math expert. Solve the following grade-school math problem with meticulous step-by-step reasoning.

For each step:
1. State what you are computing
2. Write the arithmetic expression
3. Compute the result explicitly (e.g., 3 × 4 = 12, then 12 + 5 = 17)
4. Double-check the arithmetic before moving on

After all steps, restate the final answer clearly.
Always end with the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the proposed solution to the math problem below.
Check each arithmetic step for correctness. Verify units, operations, and intermediate values carefully.
If the solution is correct, restate it clearly.
If there are errors, provide the corrected solution with clear step-by-step reasoning.
Always end with the final numerical answer on its own line prefixed with "#### ".

"""

VERIFY_MATH_PROMPT = """You are an expert math verifier. You are given a problem and two solution attempts.
Your process MUST follow these steps in order:
1. INDEPENDENTLY solve the problem from scratch without looking at the provided solutions, showing all arithmetic steps.
2. Compare your independent answer with Solution A and Solution B.
3. If all three agree, confirm that answer.
4. If there is disagreement, carefully re-examine each differing step and determine the correct value through direct computation.
5. State which solution is correct and why, then give the final answer.
Always end with the final numerical answer on its own line prefixed with "#### ".

"""