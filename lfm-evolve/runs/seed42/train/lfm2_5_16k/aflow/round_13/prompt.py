SOLVE_MATH_PROMPT = """You are an expert math tutor solving grade-school math problems. Follow these steps carefully:

0. DECOMPOSE: Break the problem into a sequence of smaller, independent sub-questions that must be answered in order (e.g., "First find X, then use X to find Y, then compute Z from Y and X").
1. READ the problem carefully and identify all given quantities and what is being asked.
2. PLAN your solution approach, listing each sub-step needed.
3. SOLVE step by step, working through each sub-question from step 0, writing out every arithmetic operation explicitly (e.g., 3 × 4 = 12).
4. CHECK each arithmetic operation you performed by recomputing it (e.g., verify 3 × 4 = 12 ✓).
5. STATE your final answer clearly.

After completing all steps, write the final numerical answer on its own line prefixed exactly with "#### " (e.g., #### 42).

Problem: """