SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

EXTRACT_ANSWER_PROMPT = """You are a math answer extractor. Given the problem and its solution below, carefully verify the arithmetic and extract the correct final numerical answer.

Output ONLY the following format (nothing else):
#### <number>

Where <number> is the final integer or decimal answer to the problem. Do not include units, explanations, or any other text.

"""