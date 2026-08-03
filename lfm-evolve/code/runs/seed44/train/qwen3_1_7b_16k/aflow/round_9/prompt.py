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
2. INDEPENDENTLY solve the problem from scratch using your own reasoning, without being influenced by the proposed solution
3. Compare your independent answer with the proposed answer
4. If they differ, carefully recheck both approaches and determine the correct answer
5. If they agree, confirm the answer

Show your independent calculation steps clearly, then output your verified final numerical answer on its own line prefixed with "#### ".

Problem and proposed solution to check: """