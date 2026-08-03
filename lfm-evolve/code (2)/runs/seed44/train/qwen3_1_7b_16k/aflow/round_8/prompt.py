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

ALT_SOLVE_PROMPT = """You are a precise math solver. Using the extracted key information provided, solve the grade-school math problem using a different approach or order of operations than typical.

Follow these steps:
- Re-read the problem from scratch
- Break the problem into smaller sub-problems
- Solve each sub-problem independently
- Combine results carefully

Provide the final numerical answer on its own line prefixed with "#### ".

Problem and context: """

VERIFY_PROMPT = """You are a careful arithmetic verifier. You are given a math problem and two independently computed solutions (Solution A and Solution B).

Your task is to:
1. Re-read the problem carefully and identify all given quantities
2. Check the arithmetic in Solution A step by step, noting any errors
3. Check the arithmetic in Solution B step by step, noting any errors
4. If both solutions agree and both are arithmetically correct, confirm that answer
5. If they disagree or either contains an error, independently re-solve the problem from scratch:
   - List each step explicitly (e.g., "Step 1: 5 x 3 = 15")
   - Verify each arithmetic operation before proceeding
   - Arrive at the correct final answer
6. You MUST output the final verified numerical answer on its own line prefixed with "#### " (e.g., "#### 42")

Always end your response with a line in the format: #### <number>

Problem and solutions: """