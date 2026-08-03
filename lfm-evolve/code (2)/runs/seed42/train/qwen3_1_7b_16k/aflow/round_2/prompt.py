SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem with careful, detailed step-by-step reasoning.

Instructions:
1. Read the problem carefully and identify all given information and what is being asked.
2. Break the problem into clear, logical steps.
3. For each step, explicitly state the operation and compute the result carefully.
4. After completing all steps, verify your arithmetic by re-checking each calculation.
5. State the final answer clearly.

Format your response as:
- Numbered steps showing your full reasoning
- A verification line confirming key calculations are correct
- The final answer on its own line prefixed with "#### " (e.g., "#### 42")

Problem: """