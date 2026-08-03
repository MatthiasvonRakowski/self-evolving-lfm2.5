CLASSIFY_PROBLEM_PROMPT = """You are a math expert. Read the following grade-school math problem and identify its category and key numerical data.

Choose the most fitting category from: [arithmetic, rate/speed, percentages, fractions, geometry, ratios/proportions, multi-step word problem, money/economics, time, other].

Also briefly state the key mathematical operation or formula that will be needed to solve it.

Then, carefully list every numerical value mentioned in the problem with its meaning (e.g., "5 apples", "3 hours", "$12.50").

Respond in this format:
Category: <category>
Key operation: <operation or formula>
Key numbers: <list each number and what it represents, separated by semicolons>

Problem: """

SOLVE_WITH_STRATEGY_PROMPT = """You are a helpful math tutor. A math problem and its identified category and key numbers are provided below. Use the category and the listed key numbers as a hint to apply the most appropriate solving strategy.

Solve the problem step by step, carefully performing each arithmetic operation. At each step, write out the calculation explicitly and double-check the arithmetic before moving on.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

"""