SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem using this structured approach:

1. **Identify**: List the key quantities and what is being asked.
2. **Plan**: Describe the operations needed to reach the answer.
3. **Solve**: Perform each calculation step by step, showing all arithmetic clearly.
4. **Answer**: State the final numerical answer.

After completing all steps, write the final answer on its own line in this exact format:
#### <number>

Only output a plain integer or decimal for the final answer after ####. Do not include units or extra text after ####.

Problem: """