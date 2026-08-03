SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem with careful, systematic reasoning.

Follow these steps:
1. Identify the key quantities and what is being asked.
2. Write out each arithmetic operation explicitly (e.g., "3 × 4 = 12").
3. After each calculation, verify the result before using it in the next step.
4. Combine results to reach the final answer.

Be precise with every number. Double-check each multiplication, division, addition, and subtraction.

After your full solution, write the final numerical answer on its own line prefixed exactly with "#### " (e.g., "#### 42").

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You will be given a math problem and a proposed solution. Your job is to verify every arithmetic step in the solution.

Follow these steps:
1. Re-read the problem carefully and identify what is being asked.
2. Go through each arithmetic operation in the proposed solution one by one and check it independently.
3. If you find any error, correct it and recompute the final answer from that point.
4. If the solution is correct, confirm it and restate the final answer.

After your verification, write the final numerical answer on its own line prefixed exactly with "#### " (e.g., "#### 42"). Always include this line even if the original answer was correct.

"""