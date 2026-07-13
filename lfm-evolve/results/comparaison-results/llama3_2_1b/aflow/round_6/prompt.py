SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Instructions:
1. Read the problem carefully and identify all given information.
2. Solve the problem step by step, showing all calculations clearly.
3. After reaching an answer, verify it by checking: Does the answer make sense? Re-examine each arithmetic operation.
4. Correct any mistakes found during verification.
5. Provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_ALT = """You are an expert mathematician. Carefully solve the following math problem using a clear, structured approach.

Instructions:
1. Break the problem into smaller parts and identify what needs to be calculated.
2. Solve each part systematically, writing out every arithmetic step explicitly.
3. Combine the results for the final answer.
4. Double-check your arithmetic by re-calculating key steps.
5. Always end with the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. You will be given a math problem and multiple solution attempts.

Review all solutions:
1. Check each solution for arithmetic errors and logical correctness.
2. Identify which solution(s) are correct.
3. If solutions disagree, determine the correct answer by re-solving carefully from scratch.
4. Pick the single best final answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""