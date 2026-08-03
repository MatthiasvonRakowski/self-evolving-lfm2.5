prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You are given a math problem and a proposed solution.

Review each step of the solution carefully for arithmetic and logical errors.
If the solution is correct, restate the key steps briefly and confirm the answer.
If the solution contains errors, rework the problem from scratch showing correct step-by-step reasoning.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""