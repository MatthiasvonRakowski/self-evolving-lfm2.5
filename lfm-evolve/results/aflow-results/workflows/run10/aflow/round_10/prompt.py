DECOMPOSE_PROMPT = """You are a math problem analyst. Read the following grade-school math problem and extract:
1. All given quantities and their units/labels
2. The relationships between quantities (e.g., rates, totals, differences)
3. Exactly what the problem is asking to find
4. The sequence of steps needed to arrive at the answer

Be concise and precise. Do not solve the problem yet, just structure it clearly.

Problem: """

SOLVE_MATH_PROMPT = """You are an expert math solver. Using the original problem and the extracted key facts provided, solve the problem step by step.

Follow these steps:
1. For each calculation step, write what each number represents (its label/unit) before computing.
2. Perform the arithmetic operation and record the result WITH its label (e.g., "12 apples × $3/apple = $36 total cost").
3. Map each calculation step explicitly to the solution plan from the key facts section.
4. After completing all steps, verify the final answer makes sense in context (check magnitude and units).
5. State the final numerical answer on its own line prefixed exactly with "#### ".

"""