SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the grade-school math problem below with rigorous step-by-step reasoning and self-verification.

Follow this exact process:

**PHASE 1 - EXTRACT:**
List every number and quantity mentioned in the problem and what each represents.

**PHASE 2 - SOLVE:**
Work through the solution in clear numbered steps.
For each step: write the arithmetic expression, compute it explicitly (e.g., "3 × 4 = 12"), and state what the result represents.

**PHASE 3 - VERIFY:**
Re-trace the key arithmetic chain in one compact summary (e.g., "10 + 5 - 3 = 12"). Confirm this matches your answer.

**PHASE 4 - ANSWER:**
Write the final answer on its own line in this exact format: #### <number>
- The number must be a plain integer or decimal (no units, no commas, no extra text).
- Only one #### line is allowed.

Problem: """