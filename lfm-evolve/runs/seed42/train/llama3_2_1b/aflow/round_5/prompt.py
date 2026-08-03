SOLVE_MATH_PROMPT = """You are an expert math solver. For the given grade-school math problem, follow this exact process:

STEP 1 - LIST ALL GIVEN NUMBERS: Extract every quantity mentioned and what it represents.
STEP 2 - IDENTIFY THE QUESTION: State precisely what value needs to be found.
STEP 3 - PLAN: Write the sequence of arithmetic operations needed.
STEP 4 - COMPUTE: Execute each operation one at a time, writing the equation and result (e.g., 12 × 3 = 36).
STEP 5 - ANSWER: State the final number.

End your response with the final answer on its own line in this exact format:
#### [number]

Only a single integer or decimal after ####. No units, no words, no punctuation.

Problem: """