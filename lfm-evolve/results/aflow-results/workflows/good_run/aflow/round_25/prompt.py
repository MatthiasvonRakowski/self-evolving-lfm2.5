SOLVE_MATH_PROMPT = """Solve the following math problem step by step. Show each calculation clearly. At the end, write the final answer on its own line as: #### <number>

"""

SOLVE_MATH_PROMPT_ALT = """Solve the following math problem by first estimating the answer, then computing carefully step by step, and finally verifying your answer by substituting back or checking with a different method. At the end, write the final answer on its own line as: #### <number>

"""

VOTE_PROMPT = """You are given multiple solutions to the same math problem. Each solution ends with #### followed by a number.

Your task:
1. Identify the numerical answer after "#### " in each solution.
2. Select the answer that appears most frequently (majority vote). If all differ, select the most reasonable one based on the problem context and calculations shown.
3. Output ONLY the following line and nothing else:
#### <the chosen number>

Solutions:
"""