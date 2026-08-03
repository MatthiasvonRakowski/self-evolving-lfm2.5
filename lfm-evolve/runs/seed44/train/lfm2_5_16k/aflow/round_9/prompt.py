SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_ALT = """You are a math expert. Solve the following grade-school math problem using a careful, methodical approach.

Break the problem into smaller parts, compute each part clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a math verification expert. You are given a math problem and two independent solutions (Solution A and Solution B).

Step 1: Read the problem carefully.
Step 2: Check Solution A's reasoning and final answer for correctness.
Step 3: Check Solution B's reasoning and final answer for correctness.
Step 4: If both solutions agree on the final answer, output that answer.
Step 5: If they disagree, solve the problem independently from scratch, identify which solution (if either) is correct, and output the correct answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""