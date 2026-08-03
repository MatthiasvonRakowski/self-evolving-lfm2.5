SOLVE_MATH_PROMPT = """You are a precise math solver. Solve the given grade-school math problem using the following structured approach:

STEP 1 - MAP THE PROBLEM:
  Given: [list each piece of information with its unit, e.g. "5 apples", "3 boxes"]
  Find: [what the question asks for, with expected unit]

STEP 2 - SOLVE WITH UNIT TRACKING:
  Work through the solution step by step. After every arithmetic operation, write the unit next to the result.
  Example: 5 apples × 3 boxes = 15 apples

STEP 3 - FINAL ANSWER:
  State the final numerical answer. Then write it on its own line prefixed exactly with "#### ".

Problem: """