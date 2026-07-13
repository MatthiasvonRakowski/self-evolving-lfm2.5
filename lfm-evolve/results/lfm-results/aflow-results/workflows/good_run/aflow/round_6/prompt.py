SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

EXTRACT_ANSWER_PROMPT = """You are given a math problem and its solution. Your task is to repeat the full solution steps, then on the very last line write the final numerical answer prefixed exactly with "#### " (four hash symbols, a space, then the number only, no units, no extra text).

If the solution already contains a line starting with "#### ", preserve that answer. Output the complete solution followed by the correctly formatted answer line.

"""