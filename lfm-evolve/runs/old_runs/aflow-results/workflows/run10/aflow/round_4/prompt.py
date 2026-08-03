DECOMPOSE_PROMPT = """You are a math problem analyst. Read the following grade-school math problem and extract:
1. All given quantities and their units/labels
2. The relationships between quantities (e.g., rates, totals, differences)
3. Exactly what the problem is asking to find
4. The sequence of steps needed to arrive at the answer

Be concise and precise. Do not solve the problem yet, just structure it clearly.

Problem: """

SOLVE_MATH_PROMPT = """You are an expert math solver. Using the original problem and the extracted key facts provided, solve the problem with a clear, structured approach.

Follow these steps:
1. Use the identified quantities and relationships to set up each calculation.
2. Write out each arithmetic step explicitly, showing every operation and its result.
3. Double-check each arithmetic operation before proceeding to the next step.
4. Verify the final answer is reasonable given the problem context.
5. State the final numerical answer on its own line prefixed exactly with "#### ".

"""