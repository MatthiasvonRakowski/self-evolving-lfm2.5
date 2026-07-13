SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem step by step.

Phase 1 - UNDERSTAND:
- Identify all given quantities and what the question asks for.
- List every variable or unknown explicitly.

Phase 2 - PLAN:
- Write out the sequence of operations needed (addition, subtraction, multiplication, division).
- Express each step as a simple equation before computing it.

Phase 3 - COMPUTE:
- Execute each equation one at a time.
- After each calculation, write the result and its unit/label.
- Double-check every multi-digit addition or multiplication by doing it a second way (e.g., re-add column by column, or verify multiplication via repeated addition for small numbers).

Phase 4 - VERIFY:
- Re-read the original problem.
- Confirm the final answer is in the correct units and answers exactly what was asked.
- Check that the answer is reasonable (order of magnitude, sign, real-world logic).

Phase 5 - ANSWER:
- State the final numerical answer on its own line, prefixed EXACTLY with "#### " (four hash symbols followed by a space).
- Do NOT include units or extra words after the number on that line.

Problem: """