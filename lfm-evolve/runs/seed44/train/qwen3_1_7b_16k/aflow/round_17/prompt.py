CLASSIFY_PROBLEM_PROMPT = """You are a math expert. Read the following grade-school math problem and identify its category.

Choose the most fitting category from: [arithmetic, rate/speed, percentages, fractions, geometry, ratios/proportions, multi-step word problem, money/economics, time, other].

Also briefly state the key mathematical operation or formula that will be needed to solve it.

Respond in this format:
Category: <category>
Key operation: <operation or formula>

Problem: """

SOLVE_WITH_STRATEGY_PROMPT = """You are a helpful math tutor. A math problem and its identified category are provided below. Use the category as a hint to apply the most appropriate solving strategy.

Before solving, extract and list all key numbers and quantities mentioned in the problem to avoid misreading.

Then solve the problem step by step, carefully performing each arithmetic operation. At each step, write out the calculation explicitly (e.g., 3 × 4 = 12) and verify the result before proceeding to the next step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

"""