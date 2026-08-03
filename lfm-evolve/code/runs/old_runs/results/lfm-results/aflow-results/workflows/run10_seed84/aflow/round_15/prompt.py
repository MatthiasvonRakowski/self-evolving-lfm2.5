SOLVE_MATH_PROMPT_A = """You are a careful math solver. Solve the following grade-school math problem step by step, showing all arithmetic clearly.

Work through the problem methodically, then state the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_B = """You are a precise math solver. Solve the following grade-school math problem by identifying what is given, what is asked, and computing each step carefully.

After your reasoning, provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

AGGREGATE_PROMPT = """You are given a math problem and two independent solutions. Your task is to determine the correct final answer.

1. Compare the final answers from both solutions (look for lines starting with "#### ").
2. If both solutions agree on the final answer, use that answer.
3. If they disagree, carefully re-examine both solution paths, identify any arithmetic errors, and determine the correct answer.
4. Output your final numerical answer on its own line prefixed with "#### ".

"""