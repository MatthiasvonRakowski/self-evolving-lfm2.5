SOLVE_MATH_PROMPT = """You are an expert math problem solver. Solve the following grade-school math problem with careful, detailed reasoning.

Follow these steps exactly:
1. UNDERSTAND: State clearly what the question is asking for.
2. FACTS: List all the key numbers and information given.
3. SOLVE: Work through the solution step by step, writing out every arithmetic operation explicitly (e.g., 3 × 4 = 12).
4. RECOMPUTE: Re-calculate each arithmetic result from step 3 independently (e.g., restate "3 × 4 = 12" and confirm). If any result differs, use the recomputed value.
5. ALTERNATIVE: Solve the problem using a completely different method or order of operations as a cross-check (e.g., if you multiplied first, now try adding first; if you worked forward, now work backward from a plausible answer). Confirm both methods give the same result.
6. CHECK: Verify your final number makes sense in the context of the problem (e.g., is it a reasonable magnitude? correct sign?).
7. ANSWER: Write the final numerical answer on its own line, prefixed with "#### ".

Important: The answer after "#### " must be a single number only (no units, no extra words).

Problem: """

REVIEW_MATH_PROMPT = """You are a meticulous math checker. You will be given a math problem and a proposed solution. Your job is to:

1. REREAD: Carefully re-read the original problem to understand exactly what is being asked.
2. VERIFY: Check every arithmetic step in the proposed solution for errors (addition, subtraction, multiplication, division).
3. CHECK LOGIC: Confirm the reasoning and approach are correct and match the problem.
4. CORRECT: If you find any errors, redo the calculation correctly. If the solution is correct, confirm it.
5. FINAL ANSWER: Write the final verified numerical answer on its own line, prefixed with "#### ".

Important rules:
- The answer after "#### " must be a single number only (no units, no extra words).
- Be especially careful about: misreading numbers, wrong operations, off-by-one errors, and unit confusion.
- Always output a "#### " line at the end with the final answer.

"""

RECONCILE_MATH_PROMPT = """You are a senior math arbiter. You will be given a math problem and two independent solution attempts. Your job is to:

1. COMPARE: Extract the final numerical answer from Attempt 1 and Attempt 2 (look for "#### " lines).
2. AGREE: If both answers match, confirm that answer is correct.
3. DISAGREE: If answers differ, carefully re-solve the problem from scratch independently, showing all arithmetic steps explicitly.
4. VERIFY: Double-check your final arithmetic by recomputing each operation.
5. DECIDE: Choose the correct answer based on your independent verification.
6. OUTPUT: Write the final answer on its own line, prefixed with "#### ".

Important rules:
- The answer after "#### " must be a single number only (no units, no extra words).
- Do not blindly trust either attempt — verify independently when they disagree.
- Always output a "#### " line at the end.

"""