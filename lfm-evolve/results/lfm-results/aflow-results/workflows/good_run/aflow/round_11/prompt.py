SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem with careful, systematic reasoning.

Follow these steps EXACTLY:
1. Read the problem carefully and list every known quantity with its unit/label.
2. Identify exactly what the question is asking for.
3. Plan the sequence of operations needed.
4. Execute each arithmetic operation one at a time, writing it explicitly:
   - Show the operation: e.g., "12 × 5 = 60"
   - Label the result: e.g., "Total apples = 60"
5. After completing all steps, re-read the original problem and confirm:
   - Every piece of information from the problem was used correctly.
   - The final answer directly answers what was asked.
   - The magnitude of the answer is reasonable given the problem context.
6. If you find any error during the confirmation, correct it immediately before writing the final answer.

Important rules:
- Never skip arithmetic steps.
- Always write numbers as digits, not words.
- Track units throughout (e.g., dollars, hours, apples).

After your full solution, write the final numerical answer on its own line prefixed exactly with "#### " (e.g., "#### 42").

Problem: """