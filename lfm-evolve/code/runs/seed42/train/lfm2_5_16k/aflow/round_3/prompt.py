prompt
SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_ALT_PROMPT = """You are a math expert. Solve the following grade-school math problem using a different approach or method than typical solutions.

Break the problem into smaller parts, verify each part, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. Review the problem and two independent solutions provided.

Compare both solutions carefully. Check each calculation step. Identify which solution is correct, or if both agree, confirm the answer. If both solutions differ, carefully re-derive the answer from scratch.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

Problem and solutions: """