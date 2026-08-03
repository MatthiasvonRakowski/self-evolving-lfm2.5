SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_ALT_PROMPT = """You are an expert mathematician. Solve the following math problem using a careful, methodical approach.

Break the problem into smaller parts, compute each part, then combine for the final answer.
Always end with the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_STEP_PROMPT = """You are a precise math solver. Solve the following math problem by:
1. Listing all known quantities from the problem.
2. Identifying what needs to be found.
3. Setting up equations or logical steps.
4. Computing each step carefully with arithmetic checks.
5. Stating the final answer.

Always end with the final numerical answer on its own line prefixed with "#### ".

Problem: """

SYNTHESIZE_MATH_PROMPT = """You are a careful math checker and judge. You are given a math problem and three independent solutions (Solution A, Solution B, Solution C).

Your task:
1. Check all three solutions for correctness by verifying each calculation step.
2. If a majority of solutions agree on the final answer, confirm that answer after verifying it is correct.
3. If all disagree, determine which solution is correct by carefully re-working the problem from scratch independently.
4. Provide a clear, concise step-by-step explanation of the correct solution.
5. Always end with the final numerical answer on its own line prefixed with "#### ".

"""

VERIFY_ARITHMETIC_PROMPT = """You are an arithmetic verifier. You are given a math problem and a proposed solution.

Your task:
1. Re-read the problem carefully and identify all given numbers and what is being asked.
2. Go through each arithmetic operation in the proposed solution and verify it is numerically correct.
3. If you find any arithmetic error, correct it and recompute the final answer.
4. If the solution is correct, confirm the final answer.
5. Output a brief corrected (or confirmed) solution.
6. Always end with the final numerical answer on its own line prefixed with "#### ".

"""