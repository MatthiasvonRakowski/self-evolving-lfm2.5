SOLVE_MATH_PROMPT = """You are an expert math problem solver. Solve the following grade-school math problem with careful, detailed reasoning.

Follow these steps exactly:
1. UNDERSTAND: State clearly what the question is asking for.
2. FACTS: List all the key numbers and information given.
3. SOLVE: Work through the solution step by step, writing out every arithmetic operation explicitly (e.g., 3 × 4 = 12).
4. CHECK: Verify your final number makes sense in the context of the problem.
5. ANSWER: Write the final numerical answer on its own line, prefixed with "#### ".

Important: The answer after "#### " must be a single number only (no units, no extra words).

Problem: """

SOLVE_MATH_PROMPT_ALT = """You are a careful math tutor solving a grade-school problem. Work through it methodically from scratch.

Follow these steps exactly:
1. GOAL: Identify exactly what quantity the problem asks you to find.
2. GIVENS: Extract every number and fact stated in the problem.
3. PLAN: Describe the sequence of operations needed before calculating.
4. CALCULATE: Execute each operation step by step, writing every arithmetic operation explicitly (e.g., 5 + 7 = 12).
5. ANSWER: Write the final numerical answer on its own line, prefixed with "#### ".

Important: The answer after "#### " must be a single number only (no units, no extra words).

Problem: """

REVIEW_MATH_PROMPT = """You are a meticulous math checker. You will be given a math problem and two independently produced solutions. Your job is to determine the correct answer.

1. REREAD: Carefully re-read the original problem to understand exactly what is being asked.
2. COMPARE: Check whether Solution A and Solution B agree on the final answer.
3. VERIFY: For each solution, check every arithmetic step for errors (addition, subtraction, multiplication, division).
4. JUDGE: If both solutions agree, confirm the answer. If they disagree, carefully identify which solution has an error and determine the correct answer by redoing the key calculations yourself.
5. FINAL ANSWER: Write the final verified numerical answer on its own line, prefixed with "#### ".

Important rules:
- The answer after "#### " must be a single number only (no units, no extra words).
- Be especially careful about: misreading numbers, wrong operations, off-by-one errors, and unit confusion.
- Always output a "#### " line at the end with the final answer.

"""