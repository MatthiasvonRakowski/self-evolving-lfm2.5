prompt
SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem carefully.

Work through the problem step by step, performing each arithmetic operation explicitly. After completing your solution, verify that your final numerical answer directly addresses what the question is asking for.

Provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. You will be given a math problem and a proposed solution. Your job is to verify every calculation step by step.

Instructions:
1. Re-read the problem carefully and identify what is being asked.
2. Check each arithmetic step in the proposed solution for correctness.
3. If you find any error, recompute the correct answer from scratch.
4. If the solution is correct, confirm and restate the final answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""