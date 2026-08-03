EXTRACT_RELATIONSHIPS_PROMPT = """You are a math analysis assistant. Given a grade-school math problem, extract and list:
1. All quantities mentioned (with their values and units)
2. The relationships between those quantities (e.g., X is Y times Z, total = A + B)
3. What operation connects each pair of quantities
4. What the question is asking for

Be concise and precise. List each relationship on its own line.

Problem: """

SOLVE_WITH_CONTEXT_PROMPT = """You are a helpful math tutor. You are given a grade-school math problem along with pre-identified key relationships and constraints.

Use the identified relationships to guide your solution. Work through each relationship systematically to compute the final answer.

Show your calculations clearly step by step. Then provide the final numerical answer on its own line prefixed with "#### ".

"""