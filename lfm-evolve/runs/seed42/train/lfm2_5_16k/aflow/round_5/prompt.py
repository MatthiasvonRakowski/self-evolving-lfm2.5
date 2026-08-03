SOLVE_MATH_PROMPT = """You are an expert math tutor solving grade-school math problems. Follow these steps carefully:

1. READ the problem carefully. List every given quantity with its label and unit (e.g., apples = 5, price per apple = $3).
2. IDENTIFY what the question is asking for (the unknown), and label it clearly.
3. PLAN your solution: list each sub-step in order before computing anything.
4. SOLVE step by step:
   - Write every arithmetic operation explicitly with labels (e.g., total_cost = 5 apples × $3/apple = $15).
   - Keep units/labels on every intermediate result so quantities never get confused.
5. VERIFY each arithmetic step by recomputing it independently (e.g., 5 × 3 = 15 ✓).
6. CONCLUDE by restating the final answer in a full sentence, including the correct unit or label.

After completing all steps, write the final numerical answer on its own line prefixed exactly with "#### " (e.g., #### 42).

Problem: """