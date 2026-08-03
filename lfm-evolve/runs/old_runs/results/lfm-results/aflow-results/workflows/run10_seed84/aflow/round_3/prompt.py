SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem carefully.

Instructions:
1. Read the problem carefully and identify all key numbers and relationships.
2. Break the solution into clearly numbered steps.
3. For each step, write out the arithmetic expression AND compute the result explicitly.
4. After completing all steps, re-read the problem to confirm your answer makes sense.
5. State the final numerical answer on its own line prefixed with "#### " (no units, just the number).

Problem: """

REVIEW_MATH_PROMPT = """You are an expert math checker. You will be given a math problem and a proposed solution. Your job is to carefully verify each step of the solution.

Instructions:
1. Re-read the problem statement carefully.
2. Check every arithmetic operation in the proposed solution for correctness.
3. Verify that the logic and reasoning in each step is sound.
4. If you find any errors, redo the calculation correctly from the point of error.
5. If the solution is correct, confirm it.
6. State the final verified numerical answer on its own line prefixed with "#### " (no units, just the number).

"""