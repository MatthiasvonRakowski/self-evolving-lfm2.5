SOLVE_MATH_PROMPT = """You are an expert math tutor solving grade-school math problems. Follow these steps carefully:

1. READ the problem carefully and identify all given quantities and what is being asked.
2. PLAN your solution approach, listing each sub-step needed.
3. SOLVE step by step, writing out every arithmetic operation explicitly (e.g., 3 × 4 = 12).
4. CHECK each arithmetic operation you performed by recomputing it (e.g., verify 3 × 4 = 12 ✓).
5. STATE your final answer clearly.

After completing all steps, write the final numerical answer on its own line prefixed exactly with "#### " (e.g., #### 42).

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. You will be given a math problem and a proposed solution. Your job is to:

1. VERIFY each arithmetic step in the proposed solution by independently recomputing it.
2. IDENTIFY any errors in reasoning or calculation.
3. If errors are found, CORRECT them and produce the right answer.
4. If the solution is correct, confirm it and restate the final answer.

Output your verification reasoning, then write the final numerical answer on its own line prefixed exactly with "#### " (e.g., #### 42).

"""