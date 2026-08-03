SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_ALT = """You are an expert mathematician. Carefully solve the following grade-school math problem using a structured approach.

Break the problem into smaller parts, solve each part, then combine to get the final answer. Always double-check arithmetic.

Provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. Review the problem and the candidate solution provided.

Check each calculation step carefully. If the solution is correct, restate it concisely. If there are any errors, provide the corrected solution.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

Problem and candidate solution: """