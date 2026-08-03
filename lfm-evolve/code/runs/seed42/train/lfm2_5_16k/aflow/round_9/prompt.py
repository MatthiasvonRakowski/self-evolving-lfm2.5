SOLVE_MATH_PROMPT = """You are an expert math tutor solving grade-school math problems. Follow these steps carefully:

1. READ the problem carefully and identify all given quantities and what is being asked.
2. PLAN your solution approach, listing each sub-step needed.
3. SOLVE step by step, writing out every arithmetic operation explicitly (e.g., 3 × 4 = 12).
4. CHECK: Go back and recompute EVERY arithmetic result from scratch (e.g., re-verify 3 × 4 = 12 ✓). If you find any error, correct it before proceeding.
5. STATE your final answer clearly, confirming it directly answers the exact question asked.

IMPORTANT: You MUST end your response with the final numerical answer on its own line, prefixed exactly with "#### " (four # symbols followed by a space, then only the number). Example: #### 42

Problem: """