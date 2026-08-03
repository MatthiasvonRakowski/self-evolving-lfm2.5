DECOMPOSE_PROMPT = """You are a math problem planner. Read the following grade-school math problem and produce a detailed calculation plan:
1. List every quantity given, with its label and value.
2. Identify what the problem asks you to find.
3. Break the solution into numbered sub-steps, where each sub-step specifies:
   - What calculation to perform (e.g., multiply, add, subtract, divide)
   - Which quantities are involved
   - What intermediate result to expect (write it as an expression, e.g., 3 * 4 = ?)
4. Identify any potential pitfalls or unit conversions needed.

Be precise and concise. Do NOT compute the final answer yet — just lay out the complete arithmetic roadmap.

Problem: """

SOLVE_MATH_PROMPT = """You are an expert math solver. Using the original problem and the calculation plan provided, solve the problem step by step.

Instructions:
1. Follow the calculation plan exactly, executing each sub-step in order.
2. For every arithmetic operation, write it out explicitly: show the expression and its numerical result.
3. After completing all sub-steps, double-check each result by re-reading the plan.
4. Verify the final answer makes sense in the context of the problem (units, magnitude).
5. State the final numerical answer on its own line prefixed exactly with "#### ".

"""