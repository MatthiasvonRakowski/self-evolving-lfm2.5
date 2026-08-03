SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You are given a math problem and a previously attempted solution.

Your task:
1. Carefully re-read the problem and check the previous solution step by step.
2. Identify any arithmetic or logical errors.
3. If the solution is correct, restate it with the same step-by-step reasoning.
4. If there are errors, provide the corrected full solution with clear steps.
5. End your response with the final numerical answer on its own line prefixed with "#### ".

"""

ALT_SOLVE_PROMPT = """You are an expert mathematician. Solve the following grade-school math problem using a different approach or method than typical step-by-step arithmetic. Think carefully and independently.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

RECONCILE_PROMPT = """You are a math judge. You are given a math problem and two independent solutions (Solution A and Solution B).

Your task:
1. Extract the final numerical answer from Solution A (look for the line starting with "#### ").
2. Extract the final numerical answer from Solution B (look for the line starting with "#### ").
3. If both answers agree, confirm that answer as correct and output a brief explanation followed by the final answer.
4. If they disagree, carefully re-examine both solutions step by step, identify which one is correct, and explain why.
5. End your response with the final numerical answer on its own line prefixed with "#### ".

"""