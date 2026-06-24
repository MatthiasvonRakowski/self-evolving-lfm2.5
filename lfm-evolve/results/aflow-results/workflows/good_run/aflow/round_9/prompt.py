SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You will be given a math problem and a proposed solution.

Your task:
1. Re-read the problem carefully.
2. Check each step of the proposed solution for arithmetic or logical errors.
3. If the solution is correct, restate it clearly with the final answer on its own line prefixed with "#### ".
4. If you find any error, redo the solution correctly step by step, and put the correct final numerical answer on its own line prefixed with "#### ".

Do not skip steps. Always end with a line in the format:
#### <number>

"""

SOLVE_MATH_ALT_PROMPT = """You are an independent math solver. Solve the following grade-school math problem using a different approach or method than typical solutions.

Work through it carefully step by step. Provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

RECONCILE_PROMPT = """You are a math expert reconciling two independently derived solutions to the same problem.

Your task:
1. Read both Solution A and Solution B carefully.
2. Extract the final answer from each solution (the number after "####").
3. If both solutions agree on the final answer, confirm it and state that answer.
4. If they disagree, do NOT simply pick one. Instead:
   a. Set aside both solutions temporarily.
   b. Re-solve the original problem completely from scratch, step by step, as if seeing it for the first time.
   c. Use your fresh solution to determine the correct answer.
   d. Explain which of Solution A or B (if either) matches your fresh derivation and why the other was wrong.
5. Always end your response with the correct final numerical answer on its own line prefixed with "#### ".

Do not skip steps. Always end with a line in the format:
#### <number>

"""