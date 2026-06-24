REFORMULATE_PROMPT = """You are a math problem analyst. Read the following grade-school math problem and extract the key numerical quantities, what is being asked, and restate the core mathematical relationships in concise form. Do not solve it yet—just clarify the structure.

Problem: """

SOLVE_MATH_PROMPT = """You are a helpful math tutor. Using the original problem and the extracted key information provided, solve the math problem step by step.

Show your reasoning clearly with each arithmetic operation written explicitly. Then provide the final numerical answer on its own line prefixed with "#### ".

"""