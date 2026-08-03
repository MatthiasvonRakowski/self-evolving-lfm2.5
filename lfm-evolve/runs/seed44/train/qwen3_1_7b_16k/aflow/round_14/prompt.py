CLASSIFY_PROBLEM_PROMPT = """You are a math expert. Read the following grade-school math problem and identify its category.

Choose the most fitting category from: [arithmetic, rate/speed, percentages, fractions, geometry, ratios/proportions, multi-step word problem, money/economics, time, other].

Also briefly state the key mathematical operation or formula that will be needed to solve it.

Respond in this format:
Category: <category>
Key operation: <operation or formula>

Problem: """

SOLVE_WITH_STRATEGY_PROMPT = """You are a helpful math tutor. A math problem and its identified category are provided below. Use the category as a hint to apply the most appropriate solving strategy.

Solve the problem step by step, carefully performing each arithmetic operation. At each step, write out the calculation explicitly and double-check the arithmetic before moving on.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

"""

VERIFY_SOLUTION_PROMPT = """You are a careful math checker. You are given a math problem and a proposed solution. Your task is to:

1. Re-read the problem carefully and identify what is being asked.
2. Check each arithmetic step in the proposed solution for correctness.
3. If you find any errors, recompute from the point of error and provide the corrected solution.
4. If the solution is correct, confirm it and restate the final answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""