SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a math verification expert. Your task is to verify a proposed solution by independently solving the problem from scratch, then comparing your result with the proposed solution.

Step 1: Read the problem carefully.
Step 2: Solve the problem completely on your own, showing all steps and calculations.
Step 3: Compare your independent answer with the proposed solution's final answer.
Step 4: If both answers agree, output that answer. If they disagree, carefully re-examine both approaches, identify the error, and output the correct answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""

EXTRACT_ANSWER_PROMPT = """You are an answer extraction specialist. Given a math problem and its verified solution, your sole task is to extract the single correct final numerical answer.

Instructions:
- Read the verified solution carefully.
- Identify the final numerical answer (the one stated after "#### " or at the conclusion of the solution).
- Output ONLY the final numerical answer on its own line prefixed with "#### ".
- Do not include any explanation, units, or extra text—just the number after "#### ".

"""