SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_ALT_PROMPT = """You are an expert mathematician. Solve the following math problem using a careful, methodical approach.

Break the problem into smaller parts, compute each part, then combine for the final answer.
Always end with the final numerical answer on its own line prefixed with "#### ".

Problem: """

SYNTHESIZE_MATH_PROMPT = """You are a careful math checker and judge. You are given a math problem and two independent solutions (Solution A and Solution B).

Your task:
1. Check both solutions for correctness by verifying each calculation step.
2. If both solutions agree on the final answer, confirm that answer.
3. If they disagree, determine which solution is correct by carefully re-working the problem from scratch.
4. Provide a clear, concise step-by-step explanation of the correct solution.
5. Always end with the final numerical answer on its own line prefixed with "#### ".

"""