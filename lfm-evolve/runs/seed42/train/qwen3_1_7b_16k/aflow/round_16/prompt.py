SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem using the structured template below. Fill in every section carefully.

UNDERSTAND:
- QUESTION ASKED: (copy the exact thing the problem is asking you to find, including units)
- QUANTITIES: (list every number/quantity in the problem as: name = value unit)

PLAN:
- (describe in 1-3 sentences the operations you will use and why)

EXECUTE:
- (show every arithmetic step explicitly, one operation per line, labeling intermediate results with name and unit)

CHECK:
- (verify each arithmetic step from EXECUTE is correct; confirm the final result answers the QUESTION ASKED)

ANSWER:
- (one sentence: "The answer is [number] [unit].")
- Final answer: #### [number only]

Problem: """