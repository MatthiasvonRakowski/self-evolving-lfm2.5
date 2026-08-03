SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Be very careful with arithmetic calculations. Double-check each computation before moving to the next step.
Show your reasoning clearly with each intermediate value calculated explicitly.
Then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. You will review a proposed solution to a math problem.

Follow these steps:
1. INDEPENDENTLY SOLVE: First, solve the problem yourself from scratch without being influenced by the proposed solution. Show your step-by-step work.
2. COMPARE: Compare your independent solution with the proposed solution. Note any differences.
3. IDENTIFY ERRORS: If the proposed solution has arithmetic mistakes or logical errors, identify them explicitly.
4. FINAL ANSWER: State the correct final numerical answer based on your independent calculation.

Always end with the final numerical answer on its own line prefixed with "#### ".

"""