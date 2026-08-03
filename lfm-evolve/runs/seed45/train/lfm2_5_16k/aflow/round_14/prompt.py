SOLVE_MATH_PROMPT = """You are a careful math tutor. Solve the following grade-school math problem step by step.

Think carefully about each arithmetic operation. Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_ALT = """You are a precise math solver. Solve the following grade-school math problem using a different approach or strategy than typical.

Break the problem into smaller parts, verify each computation, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the following problem and two candidate solutions.

Check each arithmetic step carefully in both solutions. Determine which solution (if any) is correct.
If at least one solution is correct, respond with "CORRECT" on the first line, then on the second line write exactly "PREFER A" if Solution A is correct, or "PREFER B" if Solution B is correct (prefer B only if A is wrong but B is right).
If both are incorrect, respond with "INCORRECT" on the first line, then explain the mistakes found in each.

"""

REVISE_MATH_PROMPT = """You are a helpful math tutor. Previous solutions had errors or disagreed. Using the review feedback, solve the problem again carefully step by step from scratch.

Show your reasoning clearly, verify each arithmetic step, then provide the final numerical answer on its own line prefixed with "#### ".

"""