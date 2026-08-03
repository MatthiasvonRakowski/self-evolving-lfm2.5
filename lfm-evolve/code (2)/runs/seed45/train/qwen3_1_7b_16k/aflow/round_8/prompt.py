SOLVE_MATH_PROMPT = """You are an expert math solver. Follow these steps to solve the grade-school math problem:

1. EXTRACT: List every quantity mentioned (e.g., "apples = 5", "price per apple = $2").
2. PLAN: Write the arithmetic operations needed using the extracted quantities.
3. CALCULATE: Perform each calculation explicitly, showing the numbers used.
4. ANSWER: State the final numerical result.

End your response with the final answer on its own line in this exact format:
#### <number>

Problem: """