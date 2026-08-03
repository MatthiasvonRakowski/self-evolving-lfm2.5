SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_ALT_PROMPT = """You are an expert mathematician. Solve the following math problem using a careful, methodical approach.

Break the problem into smaller parts, compute each part, then combine for the final answer.
Always end with the final numerical answer on its own line prefixed with "#### ".

Problem: """

SYNTHESIZE_MATH_PROMPT = """You are a rigorous math verifier. You are given a math problem and two independent solutions (Solution A and Solution B).

Your task:
1. Independently re-solve the problem from scratch with your own step-by-step calculation — do not simply copy from Solution A or B.
2. For every arithmetic operation in your solution, explicitly write out the computation (e.g., "3 × 4 = 12").
3. After completing your independent solution, compare your answer with Solution A and Solution B.
4. If your answer matches one or both solutions, confirm that answer.
5. If your answer differs from both, carefully recheck your own work and theirs to determine the correct answer.
6. Always end with the final numerical answer on its own line prefixed with "#### ".

"""