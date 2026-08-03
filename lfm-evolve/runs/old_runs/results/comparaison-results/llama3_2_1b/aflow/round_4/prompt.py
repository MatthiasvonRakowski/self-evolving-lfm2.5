SOLVE_MATH_PROMPT = """You are an expert math problem solver. Solve the following grade-school math problem carefully.

Follow these steps:
1. Read the problem carefully and identify all given information and what is being asked.
2. Break down the problem into small, manageable steps.
3. For each step, perform the arithmetic carefully and double-check each calculation.
4. Verify your intermediate results make sense in the context of the problem.
5. State your final answer clearly.

Important rules:
- Show every calculation explicitly (e.g., 3 × 4 = 12, not just "12")
- Double-check each arithmetic operation before moving to the next step
- Ensure units and quantities are tracked throughout
- The final answer must be a single number

After your step-by-step solution, write the final numerical answer on its own line in this exact format:
#### <number>

Problem: """