SOLVE_MATH_PROMPT = """You are an expert math problem solver. Study the example below, then solve the new problem using the same approach.

EXAMPLE:
Problem: Janet has 3 apples. She buys 5 more apples at the store, then gives 2 apples to her friend. How many apples does Janet have now?

Step 1: Identify what is being asked.
→ Final number of apples Janet has.

Step 2: List the key facts and numbers.
→ Starts with: 3 apples
→ Buys more: +5 apples
→ Gives away: -2 apples

Step 3: Solve with explicit arithmetic.
→ After buying: 3 + 5 = 8 apples
→ After giving away: 8 - 2 = 6 apples

Step 4: Verify the answer makes sense.
→ She started with 3, gained 5, lost 2. Net change = +3. So 3 + 3 = 6. ✓

Step 5: State the final answer.
#### 6

---
Now solve the following problem using the same step-by-step format. End with the final numerical answer on its own line prefixed with "#### ".

Problem: """