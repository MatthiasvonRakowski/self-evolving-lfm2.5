SOLVE_MATH_PROMPT = """You are a precise math solver. Solve the grade-school math problem below using a state-transition approach:

1. INITIAL STATE: Write down all starting quantities mentioned in the problem.
2. TRANSITIONS: For each event or action in the problem, write what changes and compute the new value (e.g., "After [event]: quantity goes from X to Y because X ± Z = Y").
3. FINAL STATE: State the final values of all relevant quantities.
4. ANSWER: Extract the numerical answer to the question asked.

After working through the states, write the final numerical answer on its own line prefixed exactly with "#### " (e.g., #### 42).

Problem: """