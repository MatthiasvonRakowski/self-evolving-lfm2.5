SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem using the worked example scaffolding method:

STEP 1 - CREATE A PARALLEL MINI-PROBLEM: Invent a simpler version of this same problem type using small, easy numbers (e.g., 2, 3, 5). Write it out and solve it completely showing each arithmetic operation.

STEP 2 - EXTRACT THE SOLUTION TEMPLATE: Identify the exact sequence of arithmetic operations used in your mini-problem (e.g., multiply → subtract → divide).

STEP 3 - APPLY TEMPLATE TO REAL PROBLEM: Follow that exact same sequence of operations using the actual numbers from the real problem. Perform each arithmetic operation explicitly.

STEP 4 - STATE THE FINAL ANSWER on its own line prefixed with "#### " followed by just the number.

Problem: """