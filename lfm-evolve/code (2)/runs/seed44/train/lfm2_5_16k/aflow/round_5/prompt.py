SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a math verification expert. Your task is to verify the solution to a math problem using a two-step process:

Step 1 - Independent Solution: First, solve the problem COMPLETELY ON YOUR OWN from scratch, without being influenced by the proposed solution. Show all your work step by step.

Step 2 - Comparison: Compare your independent solution with the proposed solution. Identify any discrepancies or errors in the proposed solution.

Step 3 - Final Answer: Based on your independent work and the comparison, state the correct final answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""

ARBITRATE_MATH_PROMPT = """You are an expert math arbitrator. Two different solutions to a math problem are provided below, and they disagree on the final answer.

Carefully evaluate both Solution A and Solution B step by step. Identify which solution contains correct reasoning and which contains an error. Then provide your own clean, correct solution with detailed reasoning.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""