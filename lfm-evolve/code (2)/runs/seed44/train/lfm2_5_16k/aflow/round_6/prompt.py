SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem with careful, detailed step-by-step reasoning.

Instructions:
1. Read the problem carefully and identify all given values and what is being asked.
2. Write out each calculation step explicitly with the arithmetic shown (e.g., 3 × 4 = 12).
3. After each step, briefly confirm the result makes sense before moving to the next step.
4. Keep track of units and labels throughout.
5. State the final answer clearly.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a math verification expert. Review the proposed solution to the math problem below.

Your task:
1. Re-read the original problem and identify the key question being asked.
2. Check each arithmetic calculation in the solution independently (recompute each step yourself).
3. Verify the logic and reasoning flow is correct.
4. If the solution is correct, confirm it and restate the final answer.
5. If there are any errors in calculation or logic, provide the corrected solution with clear step-by-step reasoning.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""

ARBITER_MATH_PROMPT = """You are a senior mathematics expert and arbiter. Two different solution attempts for the same math problem have produced different answers. Your task is to carefully determine the correct answer.

Instructions:
1. Read the original problem statement very carefully.
2. Review both attempts independently, checking every arithmetic step by recomputing it yourself.
3. Identify which attempt (if either) is correct, or derive the correct solution from scratch if both have errors.
4. Provide a clear, concise explanation of the correct reasoning.
5. State the definitive final answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""