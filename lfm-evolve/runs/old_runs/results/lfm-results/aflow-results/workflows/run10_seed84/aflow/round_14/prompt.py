SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Break the problem into small steps, perform each arithmetic calculation carefully, and show your reasoning clearly.
Then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_ALT_PROMPT = """You are a math expert. Solve the following grade-school math problem by first identifying the key quantities and setting up equations or expressions.

Work through the problem systematically, double-checking each arithmetic step.
Then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SYNTHESIZE_MATH_PROMPT = """You are a careful math reviewer. You are given a math problem and two independent solutions (Solution A and Solution B).

Your task:
1. ALWAYS solve the problem completely from scratch on your own, showing every arithmetic step explicitly. Do not skip any computation.
2. After completing your independent solution, extract the final numerical answer from Solution A and Solution B.
3. Compare your independently derived answer with Solution A and Solution B.
4. If your answer matches one or both solutions, confirm the answer with high confidence.
5. If your answer disagrees with both solutions, re-check your own work carefully, then finalize the answer you are most confident in.
6. Always end with the final numerical answer on its own line prefixed with "#### ".

Important: Your own independent derivation is the primary source of truth. The two provided solutions are only secondary references to cross-check against.

Math problem and two solutions: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You are given a math problem and a proposed solution.

Review the proposed solution step by step:
1. Check each calculation for arithmetic errors.
2. Verify the logic and reasoning are correct.
3. If the solution is correct, restate it with the final answer on its own line prefixed with "#### ".
4. If the solution has errors, provide the corrected solution with the final answer on its own line prefixed with "#### ".

Always end your response with the final numerical answer on a line by itself prefixed with "#### ".

Math problem and proposed solution: """