SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Break the problem into small steps, perform each arithmetic calculation carefully, and show your reasoning clearly.
Then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_ALT_PROMPT = """You are a math expert. Solve the following grade-school math problem by first identifying the key quantities and setting up equations or expressions.

Work through the problem systematically, double-checking each arithmetic step.
Then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_THIRD_PROMPT = """You are a meticulous math solver. Solve the following grade-school math problem by carefully re-reading every sentence, extracting all given numbers and conditions, and tracking units throughout.

List what is given, what is asked, and solve step by step while verifying each arithmetic operation.
Then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SYNTHESIZE_MATH_PROMPT = """You are a careful math reviewer. You are given a math problem and three independent solutions (Solution A, Solution B, and Solution C).

Your task:
1. Compare the three solutions and their final answers.
2. If a majority of solutions agree on the final answer, confirm that answer and present the clearest solution.
3. If all solutions disagree, carefully re-examine each and identify which contains errors, then present the correct solution.
4. Always end with the final numerical answer on its own line prefixed with "#### ".

Math problem and three solutions: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You are given a math problem and a proposed solution.

Review the proposed solution step by step:
1. Check each calculation for arithmetic errors.
2. Verify the logic and reasoning are correct.
3. If the solution is correct, restate it with the final answer on its own line prefixed with "#### ".
4. If the solution has errors, provide the corrected solution with the final answer on its own line prefixed with "#### ".

CRITICAL FORMATTING RULE: The absolute last line of your entire response MUST be in the format "#### X" where X is ONLY the final numeric answer (e.g., "#### 42" or "#### 3.5"). Do NOT include any words, units, punctuation, or additional text on that final line — just "#### " followed by the number.

Math problem and proposed solution: """