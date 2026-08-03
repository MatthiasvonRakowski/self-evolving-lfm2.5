SOLVE_MATH_PROMPT = """You are an expert math problem solver. Read the problem carefully and solve it by thinking aloud, as if writing on scratch paper.

For every arithmetic operation, write it out explicitly (e.g., "3 × 4 = 12", "15 - 7 = 8") before moving on. Do not skip or combine steps. Track running totals clearly.

After solving, state the final answer as a single integer or decimal number on its own line, in this exact format:
#### <number>

Do not include units, labels, or any other text after #### — only the bare number.

Problem: """