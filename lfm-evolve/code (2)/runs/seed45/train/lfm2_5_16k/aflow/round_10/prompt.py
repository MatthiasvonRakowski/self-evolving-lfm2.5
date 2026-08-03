SOLVE_MATH_PROMPT = """You are a careful math tutor. Solve the following grade-school math problem step by step.

Think carefully about each arithmetic operation. Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_ALT = """You are a precise math solver. Solve the following grade-school math problem using a different approach or strategy than typical.

Break the problem into smaller parts, verify each computation, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_THIRD = """You are an expert math solver. Solve the following grade-school math problem independently.

Read the problem carefully, identify all quantities and relationships, then compute step by step. Double-check your arithmetic before concluding. Provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. Review the following problem and three candidate solutions.

Check each arithmetic step carefully in all solutions. Determine which solution (if any) is correct.
If at least one solution is correct, respond with "CORRECT" on the first line, then state which answer is right and why.
If all are incorrect, respond with "INCORRECT" on the first line, then explain the mistakes found in each.

"""

REVISE_MATH_PROMPT = """You are a meticulous math tutor. Previous solutions had errors or disagreements. Using the review feedback provided, solve the problem again carefully from scratch, step by step.

Show all reasoning clearly. Double-check every single arithmetic operation before writing it down. After verifying your answer is correct, you MUST write the final numerical answer on its own line using EXACTLY this format: #### <number>

Do NOT omit the #### prefix. Example of correct final line format: #### 42

"""