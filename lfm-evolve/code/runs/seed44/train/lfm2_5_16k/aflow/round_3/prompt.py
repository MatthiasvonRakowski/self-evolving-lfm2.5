SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a math verification expert. Review the proposed solution to the math problem below.
Check each calculation step carefully. If the solution is correct, restate it with the final answer.
If there are any errors, provide the corrected solution with clear step-by-step reasoning.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""

ARBITRATE_MATH_PROMPT = """You are an expert math arbitrator. Two different solutions to a math problem are provided below, and they disagree on the final answer.

Carefully evaluate both Solution A and Solution B step by step. Identify which solution contains correct reasoning and which contains an error. Then provide your own clean, correct solution with detailed reasoning.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""