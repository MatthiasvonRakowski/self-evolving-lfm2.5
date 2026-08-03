SOLVE_MATH_PROMPT = """You are an expert math problem solver. Solve the following grade-school math problem with careful, detailed reasoning.

Follow these steps exactly:
1. UNDERSTAND: State clearly what the question is asking for.
2. FACTS: List all the key numbers and information given.
3. SOLVE: Work through the solution step by step, writing out every arithmetic operation explicitly (e.g., 3 × 4 = 12).
4. CHECK: Verify your final number makes sense in the context of the problem.
5. ANSWER: Write the final numerical answer on its own line, prefixed with "#### ".

Important: The answer after "#### " must be a single number only (no units, no extra words).

Problem: """

REVIEW_MATH_PROMPT = """You are a meticulous math checker. You will be given a math problem and a proposed solution.

Follow these steps exactly:
1. INDEPENDENT SOLVE: Before looking at the proposed solution, solve the problem entirely on your own from scratch. Write out every arithmetic step explicitly (e.g., 5 × 6 = 30). Arrive at your own independent answer.
2. COMPARE: Compare your independent answer with the proposed solution's final answer. Note any discrepancies.
3. DIAGNOSE: If answers differ, carefully identify which solution has the error by re-examining the key arithmetic steps of both solutions. If answers match, do a final sanity check.
4. FINAL ANSWER: Output the correct verified answer on its own line, prefixed with "#### ".

Important rules:
- The answer after "#### " must be a single number only (no units, no extra words).
- Your INDEPENDENT SOLVE must be genuinely independent — do not follow the proposed solution's method unless it is clearly correct.
- Always output a "#### " line at the end.

"""