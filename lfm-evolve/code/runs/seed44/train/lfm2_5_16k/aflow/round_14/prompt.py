SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem with careful, detailed step-by-step reasoning.

Instructions:
1. Read the problem carefully and identify all given values and what is being asked.
2. Before solving, briefly estimate what a reasonable answer range would be (e.g., "The answer should be between X and Y because...").
3. Write out each calculation step explicitly with the arithmetic shown (e.g., 3 × 4 = 12).
4. After each step, briefly confirm the result makes sense before moving to the next step.
5. Keep track of units and labels throughout.
6. State the final answer clearly and confirm it falls within your estimated range.

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