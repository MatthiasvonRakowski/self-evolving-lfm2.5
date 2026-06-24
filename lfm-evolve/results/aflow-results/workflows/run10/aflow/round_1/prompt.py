SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem with extreme care and precision.

Follow these steps strictly:
1. Read the problem carefully and identify ALL key quantities, units, and what is being asked.
2. Break the problem into small sub-steps. For each sub-step:
   a. Write the operation you will perform.
   b. Compute the result.
   c. Immediately verify the arithmetic (e.g., re-add, re-multiply) before moving on.
3. Label every intermediate result clearly (e.g., "Total apples = 5 + 3 = 8").
4. After completing all steps, re-read the original question and confirm your final answer addresses it.
5. Check reasonableness: does the magnitude and sign of the answer make real-world sense?
6. State the final numerical answer on its own line, prefixed EXACTLY with "#### " (four hash symbols followed by a space).

Important: Do NOT skip verification of any arithmetic step. Common errors happen in addition/subtraction of multi-digit numbers—recheck these carefully.

Problem: """