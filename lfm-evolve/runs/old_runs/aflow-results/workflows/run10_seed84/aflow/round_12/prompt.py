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

SYNTHESIZE_MATH_PROMPT = """You are a rigorous math expert. You are given a math problem and three independent solutions (Solution A, Solution B, and Solution C).

Your task:
1. FIRST, independently solve the problem yourself from scratch, step by step, without being influenced by the provided solutions. Write out your own complete solution.
2. Compare your own answer with the answers from Solutions A, B, and C.
3. If your answer matches the majority of the provided solutions, that answer is very likely correct — present the clearest solution.
4. If your answer differs from all provided solutions, carefully re-examine each solution and your own work to identify arithmetic or logic errors, then determine the correct answer.
5. If the three provided solutions all disagree with each other, use your own independent solution as the primary reference.
6. Always end with the final numerical answer on its own line prefixed with "#### ".

Math problem and three solutions: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You are given a math problem and a proposed solution.

Review the proposed solution step by step:
1. Check each calculation for arithmetic errors.
2. Verify the logic and reasoning are correct.
3. If the solution is correct, restate it with the final answer on its own line prefixed with "#### ".
4. If the solution has errors, provide the corrected solution with the final answer on its own line prefixed with "#### ".

Always end your response with the final numerical answer on a line by itself prefixed with "#### ".

Math problem and proposed solution: """