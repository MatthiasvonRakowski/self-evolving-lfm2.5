SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem with careful, systematic reasoning.

Follow these steps:
1. Identify the key quantities and what is being asked.
2. Write out each arithmetic operation explicitly (e.g., "3 × 4 = 12").
3. After each calculation, verify the result before using it in the next step.
4. Combine results to reach the final answer.

Be precise with every number. Double-check each multiplication, division, addition, and subtraction.

After your full solution, write the final numerical answer on its own line prefixed exactly with "#### " (e.g., "#### 42").

Problem: """