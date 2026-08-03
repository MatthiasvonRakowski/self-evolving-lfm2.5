SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem with extreme care and precision.

Follow these steps strictly:
1. READ: Identify all given quantities and what is being asked.
2. DEFINE VARIABLES: Assign a variable name to each unknown (e.g., let x = total apples).
3. SET UP EQUATIONS: Write symbolic equations using your defined variables BEFORE substituting any numbers.
4. SUBSTITUTE & COMPUTE: Replace variables with numbers and calculate step by step. For each arithmetic operation:
   a. Write the expression (e.g., 5 × 3 = ?)
   b. Compute the result.
   c. Re-verify: recheck every addition/subtraction of multi-digit numbers by re-adding column by column.
5. LABEL RESULTS: Clearly label every intermediate result (e.g., "Cost per apple = $0.50").
6. ANSWER CHECK: Re-read the original question. Confirm your answer directly addresses what was asked.
7. SANITY CHECK: Does the magnitude and sign make real-world sense?
8. State the final numerical answer on its own line, prefixed EXACTLY with "#### " (four hash symbols followed by a space). Do not include units on the answer line.

Important: Separating equation setup (Step 3) from computation (Step 4) is critical — do NOT mix conceptual reasoning with arithmetic. Verify ALL multi-digit arithmetic before proceeding to the next step.

Problem: """