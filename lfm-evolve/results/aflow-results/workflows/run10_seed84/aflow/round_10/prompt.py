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
1. Extract the final numerical answer from Solution A and Solution B.
2. If both solutions agree on the final answer, verify the answer by quickly re-checking the key arithmetic steps, then confirm the answer.
3. If the solutions disagree, DO NOT simply pick one — instead, solve the problem yourself completely from scratch, showing all steps independently. Then identify which solution (if any) matches your independent result.
4. Always end with the final numerical answer on its own line prefixed with "#### ".

Important: When in doubt, re-derive the answer yourself rather than trusting either solution blindly.

Math problem and two solutions: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You are given a math problem and a proposed solution.

Review the proposed solution step by step:
1. Check each calculation for arithmetic errors.
2. Verify the logic and reasoning are correct.
3. If the solution is correct, restate it with the final answer on its own line prefixed with "#### ".
4. If the solution has errors, provide the corrected solution with the final answer on its own line prefixed with "#### ".

Always end your response with the final numerical answer on a line by itself prefixed with "#### ".

Math problem and proposed solution: """