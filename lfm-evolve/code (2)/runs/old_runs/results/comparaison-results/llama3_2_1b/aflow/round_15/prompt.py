SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_ALT = """You are an expert mathematician solving a word problem. Use this structured decomposition approach:

Step 1 - LIST all given quantities and values mentioned in the problem.
Step 2 - STATE clearly what the problem is asking you to find.
Step 3 - IDENTIFY the relationships and operations needed between the quantities.
Step 4 - CALCULATE step by step using those relationships.
Step 5 - STATE the final answer.

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