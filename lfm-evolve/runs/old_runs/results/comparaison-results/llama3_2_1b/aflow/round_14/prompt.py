SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_ALT = """You are an expert mathematician. Carefully solve the following math problem using a clear, structured approach.

Break the problem into smaller parts, solve each part, then combine for the final answer.
Always end with the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_ALT2 = """You are a precise math solver. Solve the following math problem by carefully tracking all quantities and units throughout your work.

First, identify all given values and what is being asked. Then set up equations or operations needed. Solve methodically, checking each calculation. Finally, verify your answer makes logical sense in context.
Always end with the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. You will be given a math problem and multiple solution attempts.

Review all solutions:
1. Check each solution for arithmetic errors and logical correctness.
2. Identify which solution(s) are correct.
3. If solutions disagree, determine the correct answer by re-solving carefully.
4. Provide the best final answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""