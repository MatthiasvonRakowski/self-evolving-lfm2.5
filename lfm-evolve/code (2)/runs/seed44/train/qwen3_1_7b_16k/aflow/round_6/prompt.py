SOLVE_MATH_PROMPT_A = """You are an expert math tutor. Solve the following grade-school math problem by carefully reading the problem, identifying the key quantities and relationships, then computing step by step.

Show your reasoning clearly at each step. End with the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_B = """You are a precise math calculator. Solve the following grade-school math problem by working through the arithmetic carefully, computing each operation one at a time with exact numbers.

Show each arithmetic operation explicitly. End with the final numerical answer on its own line prefixed with "#### ".

Problem: """

SELECT_BEST_PROMPT = """You are a math answer evaluator. You are given a math problem and two independent solutions. 

Your task:
1. Check the arithmetic in each solution carefully.
2. Identify which solution has correct calculations.
3. If both agree, use that answer. If they disagree, determine which is correct by recomputing.
4. Output the correct final answer on its own line prefixed with "#### ".

Only output your brief reasoning and the final answer line. Do not skip the "#### " prefix.

"""