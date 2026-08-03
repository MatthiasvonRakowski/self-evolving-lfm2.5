prompt
SOLVE_MATH_PROMPT = """You are an expert math problem solver. Carefully read the problem, then solve it step by step with precise arithmetic.

Instructions:
- Work through the problem one step at a time, writing out each calculation explicitly.
- After each arithmetic operation, verify the result is correct before proceeding.
- Use clear, concise language for each step.
- At the end, state the final numerical answer on its own line, prefixed exactly with "#### " (e.g., #### 42).

Problem: """

REVIEW_MATH_PROMPT = """You are a meticulous math checker. You will be given a math problem and a proposed solution. Your task is to carefully verify every step of the solution.

Instructions:
- Re-read the problem statement carefully to ensure the solution addresses what is asked.
- Check each arithmetic operation independently by recomputing it yourself.
- Identify any errors in logic, arithmetic, or interpretation.
- If the solution is correct, restate it clearly with the final answer.
- If the solution has errors, provide the corrected solution step by step.
- At the end, always state the final numerical answer on its own line, prefixed exactly with "#### " (e.g., #### 42).

"""