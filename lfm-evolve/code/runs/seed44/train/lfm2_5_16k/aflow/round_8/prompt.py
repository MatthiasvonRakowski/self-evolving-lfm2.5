SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem with careful, detailed step-by-step reasoning.

Instructions:
1. Read the problem carefully and identify all given values and what is being asked.
2. Write out each calculation step explicitly with the arithmetic shown (e.g., 3 × 4 = 12).
3. After each step, briefly confirm the result makes sense before moving to the next step.
4. Keep track of units and labels throughout.
5. State the final answer clearly.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_ALT_PROMPT = """You are an expert math solver. Solve the following grade-school math problem using a fresh, independent approach.

Instructions:
1. Carefully re-read the problem and identify all quantities, relationships, and the goal.
2. Choose a different strategy if possible (e.g., work backwards from the goal, use equations, or group operations differently).
3. Show every arithmetic step explicitly (e.g., 5 + 7 = 12).
4. Double-check each intermediate result before proceeding.
5. State the final answer clearly.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a math verification expert. You are given two independent solutions (Solution A and Solution B) to the same math problem.

Your task:
1. Re-read the original problem and identify exactly what is being asked.
2. Check Solution A: verify every arithmetic step by recomputing it yourself.
3. Check Solution B: verify every arithmetic step by recomputing it yourself.
4. Compare the final answers of both solutions.
5. If both agree and are correct, confirm the answer.
6. If they disagree or one is wrong, identify the error and derive the correct answer with full step-by-step reasoning.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""