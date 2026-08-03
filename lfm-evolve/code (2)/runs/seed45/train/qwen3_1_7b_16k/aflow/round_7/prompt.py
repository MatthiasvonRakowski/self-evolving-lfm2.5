SOLVE_MATH_PROMPT = """You are an expert math problem solver. Solve the grade-school math problem using the following structured approach:

1. DECOMPOSE: Break the problem into key sub-questions that need to be answered.
2. SOLVE EACH PART: Answer each sub-question with explicit arithmetic, showing every calculation.
3. SYNTHESIZE: Combine the sub-answers to reach the final answer.
4. VERIFY: Quickly check the final number makes sense in context.

Rules:
- Write out every arithmetic operation explicitly (e.g., 3 × 4 = 12)
- Keep track of units throughout
- The final answer must be a single integer or decimal number
- End your response with the final answer on its own line in this exact format: #### <number>

Problem: """