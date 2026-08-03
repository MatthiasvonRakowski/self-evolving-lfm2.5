SOLVE_MATH_PROMPT_A = """You are a precise arithmetic solver. Solve the math problem by carefully computing each numerical operation one at a time.

For each step, write out the arithmetic expression and its result explicitly.
At the end, write the final answer on its own line prefixed exactly with "#### ".

Problem: """

SOLVE_MATH_PROMPT_B = """You are a logical math reasoner. Read the math problem carefully, understand the real-world scenario, then solve it by tracking what each number represents throughout the solution.

Work through the problem from start to finish, then write the final answer on its own line prefixed exactly with "#### ".

Problem: """

SYNTHESIZE_PROMPT = """You are a math answer judge. You are given a math problem and two independent solutions. 

Your task:
1. Check which solution has correct arithmetic and logical reasoning.
2. If both agree on the final answer, confirm that answer.
3. If they disagree, determine which solution is correct by re-checking the key calculations.
4. Output the final correct answer on its own line prefixed exactly with "#### ".

Only output the reasoning and the final answer line. """