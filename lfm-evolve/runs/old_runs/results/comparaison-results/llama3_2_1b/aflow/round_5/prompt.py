EXTRACT_PROMPT = """You are a math problem analyst. Read the following grade-school math problem and extract:
1. All given numerical quantities and what they represent
2. The relationships or operations between quantities
3. What the question is asking to find

Be concise and structured. Problem: """

SOLVE_MATH_PROMPT = """You are a helpful math tutor. Using the problem and the extracted key quantities and relationships provided, solve the math problem step by step.

Show your reasoning clearly using the extracted information, then provide the final numerical answer on its own line prefixed with "#### ".

"""