SOLVE_MATH_PROMPT = """Solve the following math problem step by step. Show each calculation clearly. At the end, write the final answer on its own line as: #### <number>

"""

VOTE_PROMPT = """You are given multiple solutions to the same math problem. Each solution ends with #### followed by a number.

Your task:
1. Identify the numerical answer after "#### " in each solution.
2. Select the answer that appears most frequently (majority vote). If all differ, select the most reasonable one.
3. Output ONLY the following line and nothing else:
#### <the chosen number>

Solutions:
"""

VERIFY_PROMPT = """You are given a math problem and a proposed answer. Carefully verify whether the proposed answer is correct by re-solving the problem from scratch.

Steps:
1. Re-solve the problem independently, step by step.
2. Compare your result with the proposed answer.
3. If your result matches the proposed answer, confirm it.
4. If your result differs, use your computed answer instead.
5. Output ONLY the final answer on its own line in this exact format:
#### <number>

"""