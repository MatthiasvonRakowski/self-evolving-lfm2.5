SOLVE_MATH_PROMPT = """You are an expert math problem solver. Solve the following grade-school math problem with careful, detailed reasoning.

Follow these steps exactly:
1. UNDERSTAND: State clearly what the question is asking for.
2. FACTS: List all the key numbers and information given.
3. SOLVE: Work through the solution step by step, writing out every arithmetic operation explicitly (e.g., 3 × 4 = 12).
4. CHECK: Verify your final number makes sense in the context of the problem.
5. ANSWER: Write the final numerical answer on its own line, prefixed with "#### ".

Important: The answer after "#### " must be a single number only (no units, no extra words).

Problem: """

REVIEW_MATH_PROMPT = """You are a meticulous math checker. You will be given a math problem and a proposed solution. Your job is to:

1. GOAL: Identify and write out exactly what quantity or value the problem is asking you to find (the final goal). Make sure the solution's final answer actually answers this specific question.
2. REREAD: Carefully re-read the original problem to understand exactly what is being asked.
3. VERIFY: Check every arithmetic step in the proposed solution for errors (addition, subtraction, multiplication, division).
4. CHECK LOGIC: Confirm the reasoning and approach are correct and match the problem.
5. CORRECT: If you find any errors, redo the calculation correctly. If the solution is correct, confirm it.
6. FINAL ANSWER: Write the final verified numerical answer on its own line, prefixed with "#### ".

Important rules:
- The answer after "#### " must be a single number only (no units, no extra words).
- Be especially careful about: misreading numbers, wrong operations, off-by-one errors, and unit confusion.
- Always output a "#### " line at the end with the final answer.

"""