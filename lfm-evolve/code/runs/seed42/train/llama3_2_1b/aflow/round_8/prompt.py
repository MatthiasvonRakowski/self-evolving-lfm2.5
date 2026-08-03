SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SELECT_BEST_PROMPT = """You are a math expert. Two solutions to a math problem are provided. Carefully evaluate both solutions, identify which one has correct arithmetic and reasoning, and output the better solution exactly as-is (including its #### answer line). If both are correct, pick Solution 1. Only output the chosen solution text with no additional commentary.

Solutions: """