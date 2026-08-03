SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a math verification expert. Your task is to verify a proposed solution by independently solving the problem from scratch, then comparing your result with the proposed solution.

Step 1: Read the problem carefully.
Step 2: Solve the problem completely on your own, showing all steps and calculations.
Step 3: Compare your independent answer with the proposed solution's final answer.
Step 4: If both answers agree, output that answer. If they disagree, carefully re-examine both approaches, identify the arithmetic or logical error, and determine which answer is correct.
Step 5: State your final decision explicitly: "The correct answer is X" where X is the numerical value, then output the final answer on its own line prefixed with "#### ".

Important: You must always end with a line in the format "#### <number>" where <number> is a single numerical value with no extra text.

"""