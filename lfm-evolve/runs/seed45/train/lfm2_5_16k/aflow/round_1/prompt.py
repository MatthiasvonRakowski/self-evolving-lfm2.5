SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the following problem and solution.

Check each arithmetic step carefully. If the solution is correct, respond with "CORRECT" on the first line.
If there are any errors, respond with "INCORRECT" on the first line, then explain the mistakes found.

"""

REVISE_MATH_PROMPT = """You are a helpful math tutor. A previous solution had errors. Using the review feedback, solve the problem again carefully step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

"""