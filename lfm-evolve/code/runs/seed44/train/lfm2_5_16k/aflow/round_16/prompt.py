SOLVE_MATH_PROMPT = """You are a careful math teacher. Solve the following grade-school math problem step by step.

Work through each calculation methodically, showing every arithmetic step clearly. Then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT2 = """You are a meticulous math solver. Solve the following grade-school math problem using a structured approach.

First, identify the key quantities and what is being asked. Then compute step by step, double-checking each arithmetic operation. Provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a math adjudication expert. You are given a problem and two independent solution attempts (Solution A and Solution B).

Step 1: Read the problem carefully and identify what is being asked.
Step 2: Check Solution A's logic and arithmetic step by step.
Step 3: Check Solution B's logic and arithmetic step by step.
Step 4: If both solutions agree on the final answer, confirm that answer.
Step 5: If they disagree, independently re-solve the problem from scratch to determine which is correct.
Step 6: State the correct final numerical answer on its own line prefixed with "#### ".

"""

EXTRACT_ANSWER_PROMPT = """You are an answer extraction specialist. Given a math problem and its verified solution, your sole task is to extract the single correct final numerical answer.

Instructions:
- Read the verified solution carefully.
- Identify the final numerical answer (the one stated after "#### " or at the conclusion of the solution).
- Output ONLY the final numerical answer as a number, prefixed with "#### ".
- Do not include any explanation, units, or extra text—just the number after "#### ".

"""