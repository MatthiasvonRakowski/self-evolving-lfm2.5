SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem using this structured template:

UNDERSTAND: (restate what the problem is asking for in one sentence)
LABEL: (assign a variable name and unit to every distinct quantity in the problem, e.g. total_apples=10 apples)
PLAN: (describe the steps/operations needed)
EXECUTE: (carry out each step showing arithmetic explicitly, referencing your labeled variables)
CHECK: (verify: does each arithmetic result make real-world sense? re-examine what the question asked and confirm your final value answers exactly that)
ANSWER: (single number)

After completing the template, output the final numerical answer on its own line prefixed with "#### ".

Problem: """