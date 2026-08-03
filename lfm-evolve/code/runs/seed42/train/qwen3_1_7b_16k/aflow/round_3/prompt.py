SOLVE_MATH_PROMPT = """You are an expert math problem solver. Solve the following grade-school math problem with careful, detailed reasoning.

Follow these steps exactly:
1. UNDERSTAND: State clearly what the question is asking for.
2. FACTS: List all the key numbers and information given.
3. SOLVE: Work through the solution step by step, writing out every arithmetic operation explicitly (e.g., 3 × 4 = 12).
4. CHECK: Verify your final number makes sense in the context of the problem.
5. ANSWER: Write the final numerical answer on its own line, prefixed with "#### ".

Important: The answer after "#### " must be a single number only (no units, no extra words).

Problem: """