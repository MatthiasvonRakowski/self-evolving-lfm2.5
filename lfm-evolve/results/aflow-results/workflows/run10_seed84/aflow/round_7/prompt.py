SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a rigorous math checker. You are given a math problem and a proposed solution.

Your task is to INDEPENDENTLY RE-COMPUTE every arithmetic operation from scratch — do NOT simply read and accept the numbers in the proposed solution.

Follow these steps:
1. Read the problem carefully and identify what is being asked.
2. For each step in the proposed solution, RE-CALCULATE the arithmetic yourself from first principles (e.g., if it says 12 * 7 = 84, you must verify: 12 * 7 = 84 ✓ or ✗).
3. Write out your re-computations explicitly, one by one.
4. Check that the logical reasoning and problem setup are correct.
5. If all steps are correct, confirm the final answer.
6. If any step has an error, provide the corrected full solution.

Always end your response with the final numerical answer on a line by itself prefixed with "#### ". Do not omit this line.

Math problem and proposed solution: """