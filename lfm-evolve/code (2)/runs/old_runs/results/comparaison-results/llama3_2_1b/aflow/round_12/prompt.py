SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Instructions:
1. Read the problem carefully and identify all given information.
2. Solve the problem step by step, showing all calculations clearly.
3. After reaching an answer, verify it by checking: Does the answer make sense? Re-examine each arithmetic operation.
4. Correct any mistakes found during verification.
5. Provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_ALT = """You are an expert mathematician. Solve the following math problem by first estimating the expected magnitude of the answer, then solving forward step by step, and finally verifying by working backwards from your answer to confirm it matches the problem conditions.

Instructions:
1. Briefly estimate the rough magnitude of the expected answer (e.g., "should be in the tens" or "should be less than 100").
2. Solve the problem step by step, labeling each quantity with what it represents.
3. After getting your answer, verify it by substituting back: re-read the problem and confirm your answer satisfies all conditions stated.
4. If verification fails, find the mistake and re-solve.
5. Always end with the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_COT = """You are a systematic math problem solver. Solve the following math problem by first decomposing it into smaller sub-problems, solving each sub-problem, then combining the results.

Instructions:
1. Identify and list all key quantities and relationships in the problem.
2. Decompose the problem into clearly labeled sub-problems (e.g., Sub-problem 1, Sub-problem 2, ...).
3. Solve each sub-problem one at a time, showing arithmetic clearly.
4. Combine the sub-problem results to get the final answer.
5. Double-check each sub-problem answer before combining.
6. Always end with the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. You will be given a math problem and multiple solution attempts.

Review all solutions:
1. Check each solution for arithmetic errors and logical correctness.
2. Identify which solution(s) are correct.
3. If solutions disagree, determine the correct answer by re-solving carefully from scratch.
4. Pick the single best final answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""