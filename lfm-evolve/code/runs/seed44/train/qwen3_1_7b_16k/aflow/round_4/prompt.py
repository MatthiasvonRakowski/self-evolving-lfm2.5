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

VERIFY_PROMPT = """You are a careful arithmetic verifier. You are given a math problem and a proposed solution. Your task is to:
1. Re-read the problem carefully
2. Check every arithmetic step in the proposed solution
3. Verify the final answer is correct
4. If the answer is wrong, recompute and provide the correct answer
5. If the answer is correct, confirm it

Output your verified final numerical answer on its own line prefixed with "#### ".

Problem and proposed solution: """