SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the grade-school math problem below using analogical reasoning:

Step 1 - Identify the problem type (e.g., rate, ratio, addition, subtraction, multiplication, division, multi-step).
Step 2 - Mentally recall a similar simpler problem of the same type and note how it is solved.
Step 3 - Apply the same solution pattern to the actual problem, computing each arithmetic operation carefully.
Step 4 - State the final numerical answer on its own line, prefixed exactly with "#### " (four hash symbols, a space, then the number only).

Important: The line with "#### " must contain only the number, no units or extra words.

Problem: """