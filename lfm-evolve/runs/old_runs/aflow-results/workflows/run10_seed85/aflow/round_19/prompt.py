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
1. FIRST, independently solve the problem yourself from scratch, step by step, without being influenced by Solutions A or B. Write out your full working and conclude with your own answer.
2. Compare your independent answer with Solution A and Solution B.
3. If all three agree, confirm that answer.
4. If there is any disagreement (especially if the NOTE above flags a DISAGREE), carefully re-examine all reasoning chains step by step, checking every arithmetic operation. Trust the solution whose step-by-step logic is most rigorous and free of arithmetic errors. Use your own independent calculation as the primary tiebreaker.
5. Always end your response with the single correct final numerical answer on its own line prefixed with "#### ".

Do not skip steps. Always end with a line in the format:
#### <number>

"""