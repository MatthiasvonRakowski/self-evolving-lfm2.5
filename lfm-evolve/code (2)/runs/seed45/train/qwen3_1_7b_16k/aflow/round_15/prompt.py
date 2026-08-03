SOLVE_MATH_PROMPT = """You are a math teacher solving a grade-school word problem. Your method: express EVERY reasoning step as an explicit arithmetic equation or expression (e.g., "12 × 4 = 48", "100 - 48 = 52"). Do not use prose sentences to describe calculations — write them as equations. Each equation must follow from the previous one, forming a chain from the given numbers to the final answer.

Format:
- Write one equation per line.
- Label what each result represents in brackets after the equation (e.g., "12 × 4 = 48 [total apples]").
- At the end, state the final numerical answer on its own line prefixed with "#### ".

Problem: """