DECOMPOSE_PROMPT = """You are a mathematical analyst. For the given grade-school math problem, extract and list:
1. GIVEN: All numerical values and quantities mentioned
2. RELATIONSHIPS: How these quantities relate to each other (operations needed)
3. GOAL: What exactly needs to be calculated

Be concise and precise. Only list facts, no calculations yet.

Problem: """

SOLVE_WITH_CONTEXT_PROMPT = """You are a helpful math tutor. Using the extracted key information provided, solve the grade-school math problem with careful arithmetic.

Follow these steps:
- Use the identified quantities and relationships
- Perform each arithmetic operation explicitly
- Double-check each multiplication and addition

Provide the final numerical answer on its own line prefixed with "#### ".

Problem and context: """

ALT_SOLVE_PROMPT = """You are a systematic math solver. Using the extracted key information provided, solve the grade-school math problem by defining variables and setting up explicit equations.

Follow these steps:
- Assign a variable or label to each unknown quantity (e.g., let X = total apples)
- Write out equations that represent the relationships in the problem
- Solve the equations step by step, showing every arithmetic operation
- Verify your equation setup matches the original problem before finalizing

This equation-based method must be meaningfully different from simple sequential arithmetic.

Provide the final numerical answer on its own line prefixed with "#### ".

Problem and context: """

VERIFY_PROMPT = """You are a careful arithmetic verifier. You are given a math problem and two independently computed solutions (Solution A and Solution B).

Your task is to:
1. Re-read the problem carefully
2. Check the arithmetic in both Solution A and Solution B
3. If both solutions agree, confirm that answer
4. If they disagree, recompute from scratch to determine the correct answer
5. Output only the verified correct final numerical answer

Output your verified final numerical answer on its own line prefixed with "#### ".

Problem and solutions: """

EXTRACT_PROMPT = """You are a precise answer extractor. Given a math problem and its verified solution, extract the single final numerical answer.

Rules:
- Output ONLY the final number (integer or decimal), nothing else on that line
- Always prefix your answer line with "#### "
- Do not include units, explanations, or extra text on the answer line
- Example correct format: #### 42

Problem and verified solution: """