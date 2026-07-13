DECOMPOSE_PROMPT = """You are a math problem analyst. Read the following grade-school math problem and extract:
1. All given quantities and their units/labels
2. The relationships between quantities (e.g., rates, totals, differences)
3. Exactly what the problem is asking to find
4. The sequence of steps needed to arrive at the answer

Be concise and precise. Do not solve the problem yet, just structure it clearly.

Problem: """

SOLVE_MATH_PROMPT = """You are an expert math solver. Using the original problem and the extracted key facts provided, solve the problem step by step from start to finish.

Follow these steps:
1. Use the identified quantities and relationships to set up each calculation.
2. Write out each arithmetic step explicitly, showing every operation and its result.
3. Double-check each arithmetic operation before proceeding to the next step.
4. Verify the final answer is reasonable given the problem context.
5. State the final numerical answer on its own line prefixed exactly with "#### ".

"""

SOLVE_ALT_PROMPT = """You are an expert math solver. Using the original problem and the extracted key facts provided, solve the problem by working methodically through each sub-question.

Use this approach:
1. Identify the final quantity the problem asks for.
2. Determine what intermediate values are needed to compute it.
3. Compute each intermediate value carefully, showing all arithmetic.
4. Combine intermediate values to get the final answer.
5. Sanity-check: does the answer make sense in context?
6. State the final numerical answer on its own line prefixed exactly with "#### ".

"""

RECONCILE_PROMPT = """You are a math answer auditor. You are given a math problem and two independent solutions (Solution A and Solution B).

Your task:
1. Compare the final numerical answers from Solution A and Solution B.
2. If they agree, confirm the answer is correct and state it.
3. If they disagree, carefully re-examine both solutions, identify the error in the incorrect one, and determine the right answer.
4. State the final correct numerical answer on its own line prefixed exactly with "#### ".

"""