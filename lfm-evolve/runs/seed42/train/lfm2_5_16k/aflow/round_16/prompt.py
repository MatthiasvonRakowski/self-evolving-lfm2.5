SOLVE_MATH_PROMPT = """You are an expert math tutor solving grade-school math problems. Follow these steps carefully:

1. READ the problem carefully and identify all given quantities and what is being asked.
2. PLAN your solution approach, listing each sub-step needed.
3. SOLVE step by step, writing out every arithmetic operation explicitly (e.g., 3 × 4 = 12).
4. CHECK each arithmetic operation you performed by recomputing it (e.g., verify 3 × 4 = 12 ✓).
5. STATE your final answer clearly.

After completing all steps, write the final numerical answer on its own line prefixed exactly with "#### " (e.g., #### 42).

Problem: """

SOLVE_MATH_PROMPT2 = """You are an expert mathematician solving grade-school math problems using a reverse/analytical approach. Follow these steps:

1. IDENTIFY what the final answer represents and what quantity you need to find.
2. WORK BACKWARDS or set up equations: express the unknown in terms of given quantities.
3. SUBSTITUTE known values and compute each arithmetic step explicitly (e.g., 5 + 3 = 8).
4. DOUBLE-CHECK every calculation by redoing it (e.g., 5 + 3 = 8 ✓).
5. STATE the final answer clearly.

After completing all steps, write the final numerical answer on its own line prefixed exactly with "#### " (e.g., #### 42).

Problem: """

RECONCILE_PROMPT = """You are given a math problem and two independent solutions (Solution A and Solution B). Your task:

1. Extract the final numerical answer from Solution A (look for #### number).
2. Extract the final numerical answer from Solution B (look for #### number).
3. If both answers AGREE: confirm that answer is correct and state it.
4. If they DISAGREE: carefully re-examine both solutions, identify which solution contains an arithmetic error, and determine the correct answer by recomputing the critical steps.
5. Output the correct final answer.

Write the final numerical answer on its own line prefixed exactly with "#### " (e.g., #### 42).

"""