SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You will be given a math problem and a proposed solution.

Your task:
1. Re-read the problem carefully, identifying all quantities and what is being asked.
2. Check EACH arithmetic operation in the proposed solution one by one (addition, subtraction, multiplication, division). Explicitly recompute each calculation.
3. Check the logical flow: does each step follow from the previous? Are all problem constraints respected?
4. If the solution is correct, restate it clearly with the final answer on its own line prefixed with "#### ".
5. If you find any error (even a small arithmetic mistake), redo the ENTIRE solution correctly from scratch, step by step, and put the correct final numerical answer on its own line prefixed with "#### ".

Do not skip steps. Always end with a line in the format:
#### <number>

"""

SOLVE_MATH_ALT_PROMPT = """You are an independent math solver. Solve the following grade-school math problem using a different approach or method than typical solutions.

Work through it carefully step by step. Provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

RECONCILE_PROMPT = """You are a math expert reconciling two independently derived solutions to the same problem.

Your task:
1. FIRST, independently solve the problem yourself from scratch, step by step, without being influenced by Solutions A or B. Write out your full working and conclude with your own answer (call it Solution C).
2. Extract the final answers from Solution A, Solution B, and your Solution C.
3. MAJORITY VOTING: If at least two of the three answers agree, that is the candidate answer.
   - If all three agree, that answer is almost certainly correct. Confirm it.
   - If two agree and one disagrees, carefully re-examine the dissenting solution for arithmetic errors. If you find an error in the dissenting one, go with the majority answer.
   - If all three disagree (no majority), re-examine all three solutions step by step, recomputing every arithmetic operation explicitly. Identify which solution has the most rigorous, error-free logic and use that answer.
4. When the NOTE above flags a DISAGREE between Solutions A and B, pay extra attention: re-verify every arithmetic step in both solutions before finalizing.
5. Always end your response with the single correct final numerical answer on its own line prefixed with "#### ".

Do not skip steps. Always end with a line in the format:
#### <number>

"""