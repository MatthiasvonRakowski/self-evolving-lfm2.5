SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem using the structured template below. Fill in each section completely.

UNDERSTAND: [Restate what the problem is asking. Identify all given numbers and what needs to be found.]

PLAN: [Describe the sequence of operations needed to solve the problem.]

EXECUTE: [Carry out each step explicitly, showing every arithmetic operation and its result. Label each intermediate result with its meaning and units.]

CHECK: [For every arithmetic operation performed in EXECUTE, recompute it independently from scratch to confirm it is correct. Then verify the final answer addresses exactly what the problem asked for (not a sub-quantity).]

ANSWER: [State the final numerical answer in one sentence.]

#### [Final numerical answer as a single number, nothing else]

Problem: """